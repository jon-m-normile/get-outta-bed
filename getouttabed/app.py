import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from . import APP_ID, APP_NAME, VERSION, audio, model, paths, recurrence, scheduler  # noqa: E402
from .log import log  # noqa: E402
from .model import AUDIO_EXTENSIONS, Alarm, Recording  # noqa: E402


class App(Gtk.Application):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.settings = None
        self.ringing = None
        self.preview = None
        self.volume = audio.SystemVolume()
        self._inhibit_cookie = 0
        self._inhibit_proc = None
        self._started = False

    # --- lifecycle -------------------------------------------------------

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = model.load(paths.settings_file())
        self.preview = audio.Preview()
        display = Gdk.Display.get_default()
        css = Gtk.CssProvider()
        css.load_from_path(str(paths.CSS_FILE))
        Gtk.StyleContext.add_provider_for_display(display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.IconTheme.get_for_display(display).add_search_path(str(paths.ASSETS_DIR))
        Gtk.Window.set_default_icon_name(APP_ID)

        for name, cb in (("quit", lambda *a: self.quit()), ("about", self._about)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", cb)
            self.add_action(action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        self.hold()
        self._inhibit_suspend()
        GLib.timeout_add_seconds(scheduler.CHECK_SECONDS, self._check)
        log(f"{APP_NAME} {VERSION} started")

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        if "--quit" in args:
            self.quit()
            return 0
        first = not self._started
        self._started = True
        if first:
            self._check()
        if not (first and "--background" in args):
            self.activate()
        return 0

    def do_activate(self):
        if self.window is None:
            from .ui.main_window import MainWindow
            self.window = MainWindow(self)
        self.window.present()

    def do_shutdown(self):
        if self.ringing:
            self.ringing.stop_audio()
        if self.preview:
            self.preview.stop()
        if self._inhibit_proc:
            self._inhibit_proc.terminate()
        log(f"{APP_NAME} quit")
        Gtk.Application.do_shutdown(self)

    def _inhibit_suspend(self):
        self._inhibit_cookie = self.inhibit(None, Gtk.ApplicationInhibitFlags.SUSPEND,
                                            "Get Outta Bed! is waiting to ring alarms")
        if self._inhibit_cookie:
            log("suspend inhibited via session manager")
            return
        if shutil.which("systemd-inhibit"):
            self._inhibit_proc = subprocess.Popen(
                ["systemd-inhibit", "--what=sleep", "--mode=block", f"--who={APP_NAME}",
                 "--why=Waiting to ring alarms", "sleep", "infinity"])
            log("suspend inhibited via systemd-inhibit")
        else:
            log("ERROR could not inhibit suspend")

    def _about(self, *_):
        dlg = Gtk.AboutDialog(transient_for=self.window, modal=True, program_name=APP_NAME,
                              version=VERSION, logo_icon_name=APP_ID,
                              comments="An alarm clock that keeps going until you solve a puzzle.",
                              license_type=Gtk.License.MIT_X11)
        dlg.present()

    # --- settings --------------------------------------------------------

    @property
    def tz(self):
        return recurrence.local_tz()

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def save(self):
        try:
            model.save(self.settings, paths.settings_file())
        except OSError as e:
            log(f"ERROR saving settings: {e}")
        self.emit("changed")

    def save_alarm(self, alarm: Alarm):
        now = self.now()
        if alarm.rrule is None and alarm.next_occurrence(now, self.tz) is None:
            alarm.start_date = recurrence.default_start_date(alarm.hour, alarm.minute,
                                                             now.astimezone(self.tz)).isoformat()
        alarm.enabled, alarm.ended = True, False
        alarm.arm(now)
        existing = self.settings.alarm(alarm.id)
        if existing:
            self.settings.alarms[self.settings.alarms.index(existing)] = alarm
        else:
            self.settings.alarms.append(alarm)
        self.save()

    def delete_alarm(self, alarm: Alarm):
        self.settings.alarms = [a for a in self.settings.alarms if a.id != alarm.id]
        self.save()

    def set_enabled(self, alarm: Alarm, on: bool):
        if alarm.enabled == on:
            return
        alarm.enabled = on
        if on:
            now = self.now()
            alarm.ended = False
            if alarm.next_occurrence(now, self.tz) is None:
                alarm.start_date = recurrence.default_start_date(alarm.hour, alarm.minute,
                                                                 now.astimezone(self.tz)).isoformat()
            alarm.arm(now)
        self.save()

    def recording_path(self, rec: Recording) -> Path:
        return paths.recordings_dir() / rec.filename

    def playlist_files(self, alarm: Alarm):
        recs = [self.settings.recording(rid) for rid in alarm.recordings]
        return [self.recording_path(r) for r in recs if r and self.recording_path(r).exists()]

    def import_files(self, files):
        """Copy audio files into the library. Returns a list of error messages."""
        errors = []
        for f in files:
            src = Path(f.get_path()) if hasattr(f, "get_path") else Path(f)
            ext = src.suffix.lower()
            if ext not in AUDIO_EXTENSIONS:
                errors.append(f"“{src.name}” isn't a supported audio file.")
                continue
            duration = audio.probe_duration(src)
            if duration is None:
                errors.append(f"“{src.name}” couldn't be read as audio.")
                continue
            rid = model.new_id()
            try:
                shutil.copyfile(src, paths.recordings_dir() / f"{rid}{ext}")
            except OSError as e:
                errors.append(f"“{src.name}” couldn't be copied: {e.strerror}")
                continue
            self.settings.recordings.append(Recording(rid, src.stem, f"{rid}{ext}", duration))
            log(f"imported recording {src.name}")
        self.save()
        return errors

    def delete_recording(self, rec: Recording):
        if self.preview.playing == self.recording_path(rec):
            self.preview.stop()
        try:
            self.recording_path(rec).unlink()
        except OSError:
            pass
        self.settings.remove_recording(rec.id)
        self.save()

    def test_volume(self, path: Path, max_volume: int):
        """Plays `path` at max_volume for TEST_SECONDS, then restores the system volume."""
        self.preview.stop()
        snapshot = self.volume.get()
        self.volume.set_mute(False)
        self.volume.set_volume(max_volume)

        def restore():
            if snapshot:
                self.volume.set_volume(snapshot[0])
                self.volume.set_mute(snapshot[1])

        self.preview.play(path, audio.TEST_SECONDS, restore)

    # --- ringing ---------------------------------------------------------

    def _check(self):
        try:
            now = self.now()
            dec = scheduler.evaluate(self.settings.alarms, now, self.tz, ringing=self.ringing is not None)
            for a, occ in dec.skipped:
                log(f"skipped alarm {a.time_text()} {a.label!r}: missed by more than 15 minutes ({occ.astimezone(self.tz):%Y-%m-%d %H:%M})")
            for a, occ in dec.suppressed:
                log(f"alarm {a.time_text()} {a.label!r} came due while another was ringing; not rung again")
            for a in dec.switched_off:
                log(f"alarm {a.time_text()} {a.label!r} switched off ({'ended' if a.ended else 'one-time'})")
            if dec.changed:
                self.save()
            if dec.ring:
                self.ring(dec.ring[0])
        except Exception as e:
            log(f"ERROR scheduler check: {e!r}")
        return True

    def ring(self, alarm: Alarm, test: bool = False):
        if self.ringing:
            return
        from .ui.ringing import RingSession
        self.preview.stop()
        self.ringing = RingSession(self, alarm, test)
        self.ringing.start()

    def ring_finished(self):
        self.ringing = None


def main(argv=None):
    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)
    return App().run(argv if argv is not None else sys.argv)
