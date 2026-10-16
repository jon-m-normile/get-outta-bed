from getouttabed.audio import RAMP_SECONDS, RampController, VolumeRamp, next_index


class FakeVolume:
    def __init__(self, vol, muted=False):
        self.vol, self.muted = vol, muted
        self.history = []

    def get(self):
        return self.vol, self.muted

    def set_volume(self, v):
        self.vol = v
        self.history.append(v)

    def set_mute(self, m):
        self.muted = m


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_ramp_constant():
    assert RAMP_SECONDS == 180


def test_ramp_curve():
    r = VolumeRamp(20, 100)
    assert r.target(0) == 20
    assert r.target(90) == 60
    assert r.target(180) == 100
    assert r.target(500) == 100


def test_never_lowered_when_start_above_max():
    r = VolumeRamp(80, 50)
    assert {r.target(t) for t in (0, 90, 180, 1000)} == {80}


def test_controller_fake_time():
    vol, clock = FakeVolume(30), Clock()
    c = RampController(vol, 90, clock=clock)
    c.begin()
    assert vol.vol == 30
    clock.t += 90
    c.tick()
    assert vol.vol == 60
    clock.t += 90
    c.tick()
    assert vol.vol == 90
    clock.t += 1000
    c.tick()
    assert vol.vol == 90
    c.restore()
    assert vol.vol == 30


def test_muted_start_is_unmuted_and_restored():
    vol, clock = FakeVolume(40, muted=True), Clock()
    c = RampController(vol, 100, clock=clock)
    c.begin()
    assert not vol.muted and vol.vol == 40
    c.restore()
    assert vol.muted and vol.vol == 40


def test_zero_start():
    vol, clock = FakeVolume(0), Clock()
    c = RampController(vol, 100, clock=clock)
    c.begin()
    assert vol.vol == 0
    clock.t += 90
    c.tick()
    assert vol.vol == 50


def test_turned_down_during_ramp_continues_from_expected():
    vol, clock = FakeVolume(0), Clock()
    c = RampController(vol, 100, clock=clock)
    c.begin()
    clock.t += 60
    c.tick()
    vol.vol = 5
    clock.t += 1
    c.tick()
    assert vol.vol == round(61 * 100 / 180)


def test_reassert_after_ramp_every_10_seconds():
    vol, clock = FakeVolume(50), Clock()
    c = RampController(vol, 100, clock=clock)
    c.begin()
    clock.t += 181
    c.tick()
    vol.vol, vol.muted = 10, True
    clock.t += 5
    c.tick()
    assert vol.vol == 10
    clock.t += 5
    c.tick()
    assert vol.vol == 100 and not vol.muted


def test_shuffle_never_repeats():
    import random
    rng = random.Random(1)
    cur = None
    for _ in range(200):
        nxt = next_index(4, cur, True, rng)
        assert nxt != cur
        cur = nxt


def test_in_order_loops():
    seq, cur = [], None
    for _ in range(5):
        cur = next_index(3, cur, False)
        seq.append(cur)
    assert seq == [0, 1, 2, 0, 1]
