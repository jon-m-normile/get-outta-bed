"""System volume control (pactl), the volume ramp, and GStreamer playback."""
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import GLib, Gst, GstPbutils  # noqa: E402

from . import paths  # noqa: E402
from .log import log  # noqa: E402

Gst.init(None)

RAMP_SECONDS = 180
RAMP_TICK_MS = 500
REASSERT_SECONDS = 10
GAP_SECONDS = 1.5
REPEAT_GAP_SECONDS = 0.5
TEST_SECONDS = 5


class VolumeRamp:
    """volume(t) = start + (max - start) * min(t, RAMP) / RAMP, never below start."""

    def __init__(self, start: int, maximum: int, ramp_seconds: float = RAMP_SECONDS):
        self.start = max(0, min(100, start))
        self.maximum = max(0, min(100, maximum))
        self.ramp_seconds = ramp_seconds

    def target(self, t: float) -> int:
        if self.start >= self.maximum:
            return self.start
        frac = min(max(t, 0.0), self.ramp_seconds) / self.ramp_seconds
        return round(self.start + (self.maximum - self.start) * frac)


class SystemVolume:
    """Default output sink via pactl (PulseAudio or PipeWire-pulse)."""

    def _run(self, *args) -> Optional[str]:
        try:
            r = subprocess.run(["pactl", *args], capture_output=True, text=True, timeout=3)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(f"ERROR pactl {' '.join(args)}: {e}")
            return None
        if r.returncode != 0:
            log(f"ERROR pactl {' '.join(args)}: {r.stderr.strip()}")
            return None
        return r.stdout

    def get(self) -> Optional[Tuple[int, bool]]:
        vol = self._run("get-sink-volume", "@DEFAULT_SINK@")
        mute = self._run("get-sink-mute", "@DEFAULT_SINK@")
        if vol is None or mute is None:
            return None
        m = re.search(r"(\d+)%", vol)
        if not m:
            return None
        return int(m.group(1)), "yes" in mute.lower()

    def set_volume(self, pct: int) -> None:
        self._run("set-sink-volume", "@DEFAULT_SINK@", f"{int(pct)}%")

    def set_mute(self, muted: bool) -> None:
        self._run("set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0")


class RampController:
    """Drives the system volume along a VolumeRamp. Call tick() every RAMP_TICK_MS."""

    def __init__(self, backend, maximum: int, clock: Callable[[], float] = time.monotonic,
                 ramp_seconds: float = RAMP_SECONDS, reassert_seconds: float = REASSERT_SECONDS):
        self.backend = backend
        self.maximum = maximum
        self.clock = clock
        self.ramp_seconds = ramp_seconds
        self.reassert_seconds = reassert_seconds
        self.snapshot: Optional[Tuple[int, bool]] = None
        self.ramp: Optional[VolumeRamp] = None
        self.t0 = 0.0
        self.last_assert = -1e9

    def begin(self) -> Tuple[int, bool]:
        self.snapshot = self.backend.get() or (self.maximum, False)
        self.ramp = VolumeRamp(self.snapshot[0], self.maximum, self.ramp_seconds)
        self.t0 = self.clock()
        self._apply(0.0)
        return self.snapshot

    def _apply(self, t: float) -> None:
        self.backend.set_mute(False)
        self.backend.set_volume(self.ramp.target(t))
        self.last_assert = self.clock()

    def tick(self) -> int:
        t = self.clock() - self.t0
        if t < self.ramp_seconds or self.clock() - self.last_assert >= self.reassert_seconds:
            self._apply(t)
        return self.ramp.target(t)

    def restore(self) -> None:
        if self.snapshot:
            vol, muted = self.snapshot
            self.backend.set_volume(vol)
            self.backend.set_mute(muted)
            self.snapshot = None


def fallback_tone() -> Path:
    return paths.SYSTEM_ALARM_SOUND if paths.SYSTEM_ALARM_SOUND.exists() else paths.BUNDLED_ALARM_SOUND


def probe_duration(path: Path) -> Optional[float]:
    """Duration in seconds, or None if GStreamer can't decode the file."""
    try:
        disc = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        info = disc.discover_uri(path.resolve().as_uri())
    except GLib.Error:
        return None
    if not info.get_audio_streams():
        return None
    return info.get_duration() / Gst.SECOND


class _Player:
    """A playbin wrapper reporting end-of-stream and errors on the main loop."""

    def __init__(self, on_eos: Callable[[], None], on_error: Callable[[str], None]):
        self.bin = Gst.ElementFactory.make("playbin", None)
        self.on_eos, self.on_error = on_eos, on_error
        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self._watch = bus.connect("message", self._on_message)

    def _on_message(self, _bus, msg):
        if msg.type == Gst.MessageType.EOS:
            self.on_eos()
        elif msg.type == Gst.MessageType.ERROR:
            err, _ = msg.parse_error()
            self.on_error(err.message)

    def play(self, path: Path, volume: float = 1.0) -> None:
        self.bin.set_state(Gst.State.NULL)
        self.bin.set_property("uri", Path(path).resolve().as_uri())
        self.bin.set_property("volume", volume)
        self.bin.set_state(Gst.State.PLAYING)

    def set_volume(self, volume: float) -> None:
        self.bin.set_property("volume", volume)

    def stop(self) -> None:
        self.bin.set_state(Gst.State.NULL)

    def dispose(self) -> None:
        self.stop()
        bus = self.bin.get_bus()
        bus.disconnect(self._watch)
        bus.remove_signal_watch()


def next_index(n: int, current: Optional[int], shuffle: bool, rng=random) -> int:
    if n <= 1:
        return 0
    if not shuffle:
        return 0 if current is None else (current + 1) % n
    choices = [i for i in range(n) if i != current]
    return rng.choice(choices)


class Playlist:
    """Loops files, playing each `repeat` times with `gap` seconds before the next;
    falls back to the alarm tone."""

    def __init__(self, files: List[Path], shuffle: bool = False, gap: float = GAP_SECONDS, repeat: int = 1):
        self.files = [Path(f) for f in files if Path(f).exists()]
        self.shuffle = shuffle
        self.gap = gap
        self.repeat = max(1, repeat)
        self.plays = 0
        self.index: Optional[int] = None
        self.volume = 1.0
        self.running = False
        self._timer = None
        self.player = _Player(self._on_eos, self._on_error)
        self.using_fallback = not self.files
        if not self.files:
            self.files = [fallback_tone()]

    def start(self) -> None:
        self.running = True
        self._play_next()

    def _play_next(self) -> bool:
        self._timer = None
        if not self.running:
            return False
        self.index = next_index(len(self.files), self.index, self.shuffle)
        self.plays = 0
        return self._play_current()

    def _play_current(self) -> bool:
        self._timer = None
        if not self.running:
            return False
        self.plays += 1
        self.player.play(self.files[self.index], self.volume)
        return False

    def _on_eos(self) -> None:
        self.player.stop()
        if not self.running or self._timer is not None:
            return
        if self.plays < self.repeat:
            self._timer = GLib.timeout_add(int(REPEAT_GAP_SECONDS * 1000), self._play_current)
        else:
            self._timer = GLib.timeout_add(int(self.gap * 1000), self._play_next)

    def _on_error(self, message: str) -> None:
        log(f"ERROR playing {self.files[self.index]}: {message}")
        self.player.stop()
        self.files.pop(self.index)
        self.index = None
        if not self.files:
            if self.using_fallback:
                self.running = False
                return
            self.files, self.using_fallback = [fallback_tone()], True
        if self.running and self._timer is None:
            self._timer = GLib.timeout_add(200, self._play_next)

    def duck(self, ducked: bool) -> None:
        self.volume = 0.0 if ducked else 1.0
        self.player.set_volume(self.volume)

    def stop(self) -> None:
        self.running = False
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
        self.player.dispose()


class Effects:
    """Fire-and-forget short sounds (balloon pop, Simon tones)."""

    def __init__(self):
        self._live = set()

    def play(self, name: str, volume: float = 1.0) -> None:
        path = paths.SOUNDS_DIR / name
        if not path.exists():
            return
        holder = {}

        def done(*_):
            p = holder.pop("p", None)
            if p:
                GLib.idle_add(self._finish, p)

        p = _Player(done, lambda m: done())
        holder["p"] = p
        self._live.add(p)
        p.play(path, volume)

    def _finish(self, p) -> bool:
        p.dispose()
        self._live.discard(p)
        return False


class Preview:
    """Plays one file at a time for the library and the editor's Test button."""

    def __init__(self):
        self.player = _Player(self.stop, lambda m: (log(f"ERROR preview: {m}"), self.stop()))
        self._timer = None
        self._restore: Optional[Callable[[], None]] = None
        self.playing: Optional[Path] = None

    def play(self, path: Path, seconds: Optional[float] = None,
             restore: Optional[Callable[[], None]] = None) -> None:
        self.stop()
        self.playing = Path(path)
        self._restore = restore
        self.player.play(path)
        if seconds:
            self._timer = GLib.timeout_add(int(seconds * 1000), self._timeout)

    def _timeout(self) -> bool:
        self._timer = None
        self.stop()
        return False

    def stop(self) -> None:
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
        self.player.stop()
        self.playing = None
        if self._restore:
            restore, self._restore = self._restore, None
            restore()
