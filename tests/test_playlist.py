import pytest

from getouttabed import audio


class FakePlayer:
    def __init__(self):
        self.played = []

    def play(self, path, volume):
        self.played.append(path.name)

    def stop(self):
        pass


@pytest.fixture
def timers(monkeypatch):
    pending = []
    monkeypatch.setattr(audio.GLib, "timeout_add", lambda ms, fn: pending.append((ms, fn)) or len(pending))
    return pending


def make(tmp_path, names, **kw):
    files = []
    for n in names:
        (tmp_path / n).write_bytes(b"")
        files.append(tmp_path / n)
    pl = audio.Playlist(files, **kw)
    pl.player = FakePlayer()
    return pl


def run(pl, timers, ends):
    """Simulate `ends` end-of-stream events, firing each scheduled timer; returns the delays used."""
    delays = []
    for _ in range(ends):
        pl._on_eos()
        ms, fn = timers.pop()
        delays.append(ms)
        fn()
    return delays


def test_repeat_then_pause(tmp_path, timers):
    pl = make(tmp_path, ["a.wav", "b.wav"], gap=3, repeat=2)
    pl.start()
    delays = run(pl, timers, 5)
    assert pl.player.played == ["a.wav", "a.wav", "b.wav", "b.wav", "a.wav", "a.wav"]
    assert delays == [500, 3000, 500, 3000, 500]


def test_default_plays_each_once(tmp_path, timers):
    pl = make(tmp_path, ["a.wav", "b.wav"])
    pl.start()
    delays = run(pl, timers, 2)
    assert pl.player.played == ["a.wav", "b.wav", "a.wav"]
    assert delays == [1500, 1500]


def test_zero_pause(tmp_path, timers):
    pl = make(tmp_path, ["a.wav", "b.wav"], gap=0, repeat=1)
    pl.start()
    assert run(pl, timers, 1) == [0]


def test_single_file_repeats_then_pauses(tmp_path, timers):
    pl = make(tmp_path, ["a.wav"], gap=10, repeat=3)
    pl.start()
    assert run(pl, timers, 4) == [500, 500, 10000, 500]
    assert pl.player.played == ["a.wav"] * 5


def test_old_alarm_gets_defaults():
    from getouttabed.model import Alarm, _from_dict
    a = _from_dict(Alarm, {"id": "x", "hour": 6, "minute": 30})
    assert (a.repeat, a.pause) == (1, 1.5)
