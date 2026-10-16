import time
from datetime import datetime

from gi.repository import GLib, Gtk

from .. import audio
from ..log import log
from ..model import PUZZLE_NAMES, Alarm, format_time
from ..puzzles import choose_puzzle, create
from ..puzzles.base import PuzzleContext
from .photo import load_photo

SAFETY_CAP_MINUTES = 60
GOOD_MORNING_SECONDS = 2


class RingWindow(Gtk.Window):
    """Fullscreen, cannot be closed or escaped until allow_close is set."""

    def __init__(self, app, alarm: Alarm, puzzle):
        super().__init__(application=app, title="Get Outta Bed!", decorated=False)
        self.allow_close = False
        self.add_css_class("ringing")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=30, margin_bottom=30,
                      margin_start=30, margin_end=30)
        self.clock = Gtk.Label()
        self.clock.add_css_class("ring-time")
        box.append(self.clock)
        if alarm.label:
            lbl = Gtk.Label(label=alarm.label)
            lbl.add_css_class("ring-label")
            box.append(lbl)
        instr = Gtk.Label(label="Solve the puzzle to turn off the alarm.")
        instr.add_css_class("ring-instruction")
        box.append(instr)
        self.status = Gtk.Label(visible=False)
        self.status.add_css_class("ring-status")
        box.append(self.status)
        box.append(puzzle)
        self.main = box

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(box, "puzzle")
        gm = Gtk.Label(label="Good morning! ☀️")
        gm.add_css_class("good-morning")
        self.stack.add_named(gm, "done")
        self.set_child(self.stack)

        self.connect("close-request", self._on_close)
        self._tick()
        self._timers = [GLib.timeout_add_seconds(1, self._tick), GLib.timeout_add_seconds(15, self._raise)]
        self.connect("unrealize", lambda *_: [GLib.source_remove(t) for t in self._timers])

    def _tick(self):
        now = datetime.now()
        self.clock.set_label(format_time(now.hour, now.minute))
        return True

    def _raise(self):
        if not self.is_active():
            self.present()
        return True

    def _on_close(self, *_):
        if self.allow_close:
            return False
        GLib.idle_add(self.present)
        return True

    def show_status(self, text: str):
        self.status.set_label(text)
        self.status.set_visible(True)

    def show_good_morning(self):
        self.stack.set_visible_child_name("done")


class RingSession:
    def __init__(self, app, alarm: Alarm, test: bool = False):
        self.app, self.alarm, self.test = app, alarm, test
        self.playlist = None
        self.ramp = None
        self._tick_id = self._cap_id = None
        self.started = 0.0

    def start(self):
        s = self.app.settings
        self.puzzle_key = choose_puzzle(self.alarm.puzzle, s.last_puzzle)
        s.last_puzzle = self.puzzle_key
        self.app.save()

        self.ramp = audio.RampController(self.app.volume, self.alarm.max_volume)
        vol, muted = self.ramp.begin()
        files = self.app.playlist_files(self.alarm)
        self.playlist = audio.Playlist(files, self.alarm.shuffle, self.alarm.pause, self.alarm.repeat)
        self.playlist.start()
        self.started = time.monotonic()
        log(f"RING{' (test)' if self.test else ''} {self.alarm.time_text()} {self.alarm.label!r}: "
            f"start volume {vol}%{' (was muted)' if muted else ''}, max {self.alarm.max_volume}%, "
            f"puzzle {PUZZLE_NAMES[self.puzzle_key]}, "
            f"{len(files)} message(s){' (built-in tone)' if self.playlist.using_fallback else ''}, "
            f"each x{self.alarm.repeat}, {self.alarm.pause:g}s pause")

        self.effects = audio.Effects()
        ctx = PuzzleContext(load_photo(), self.effects, self._duck)
        self.puzzle = create(self.puzzle_key, ctx)
        self.puzzle.connect("solved", self._solved)
        self.window = RingWindow(self.app, self.alarm, self.puzzle)
        self.window.connect("unrealize", lambda *_: self._closed())
        self.window.fullscreen()
        self.window.present()
        self.puzzle.start()

        self._tick_id = GLib.timeout_add(audio.RAMP_TICK_MS, self._tick)
        self._cap_id = GLib.timeout_add_seconds(SAFETY_CAP_MINUTES * 60, self._cap)

    def _duck(self, ducked: bool):
        if self.playlist:
            self.playlist.duck(ducked)

    def _tick(self):
        if self.ramp:
            self.ramp.tick()
        return True

    def stop_audio(self):
        for t in (self._tick_id, self._cap_id):
            if t:
                GLib.source_remove(t)
        self._tick_id = self._cap_id = None
        if self.playlist:
            self.playlist.stop()
            self.playlist = None
        if self.ramp:
            self.ramp.restore()
            self.ramp = None

    def _solved(self, *_):
        secs = time.monotonic() - self.started
        self.stop_audio()
        log(f"SOLVED{' (test)' if self.test else ''} {PUZZLE_NAMES[self.puzzle_key]} after {int(secs // 60)}m {int(secs % 60)}s; volume restored")
        self.window.show_good_morning()
        GLib.timeout_add_seconds(GOOD_MORNING_SECONDS, self._close)

    def _close(self):
        self.window.allow_close = True
        self.window.destroy()
        return False

    def _cap(self):
        self._cap_id = None
        self.stop_audio()
        log(f"Alarm stopped after {SAFETY_CAP_MINUTES} minutes without the puzzle being solved")
        self.window.show_status(f"Alarm stopped after {SAFETY_CAP_MINUTES} minutes")
        self.window.allow_close = True
        self.app.ring_finished()
        return False

    def _closed(self):
        self.stop_audio()
        if self.app.ringing is self:
            self.app.ring_finished()
