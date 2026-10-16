from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from getouttabed import scheduler
from getouttabed.model import Alarm

NY = ZoneInfo("America/New_York")


def at(*args):
    return datetime(*args, tzinfo=NY)


def make(hour=7, minute=0, rule="FREQ=DAILY", start=date(2026, 10, 16), armed=None):
    a = Alarm(hour=hour, minute=minute, rrule=rule, start_date=start.isoformat())
    a.arm(armed or at(2026, 10, 15, 12))
    return a


def test_rings_on_time():
    a = make()
    assert scheduler.evaluate([a], at(2026, 10, 16, 6, 59, 55), NY).ring is None
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 3), NY)
    assert dec.ring and dec.ring[0] is a
    assert scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 8), NY).ring is None


def test_catch_up_within_15_minutes():
    a = make()
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 15), NY)
    assert dec.ring and dec.ring[0] is a and not dec.skipped


def test_skip_beyond_15_minutes():
    a = make()
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 15, 1), NY)
    assert dec.ring is None and len(dec.skipped) == 1
    assert a.enabled


def test_long_sleep_skips_old_rings_latest_if_fresh():
    a = make(start=date(2026, 10, 13), armed=at(2026, 10, 13, 12))
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 5), NY)
    assert dec.ring and dec.ring[1].astimezone(NY).day == 16
    assert len(dec.skipped) == 2


def test_duplicate_suppression():
    a, b = make(), make()
    dec = scheduler.evaluate([a, b], at(2026, 10, 16, 7, 0, 2), NY)
    assert dec.ring is not None and len(dec.suppressed) == 1


def test_suppressed_while_ringing():
    a = make()
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 2), NY, ringing=True)
    assert dec.ring is None and len(dec.suppressed) == 1


def test_one_time_alarm_switches_off():
    a = make(rule=None)
    dec = scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 2), NY)
    assert dec.ring and not a.enabled and not a.ended
    assert a in dec.switched_off


def test_one_time_skipped_also_switches_off():
    a = make(rule=None)
    dec = scheduler.evaluate([a], at(2026, 10, 16, 9), NY)
    assert dec.ring is None and dec.skipped and not a.enabled


def test_repeating_alarm_ends():
    a = make(rule="FREQ=DAILY;COUNT=2")
    scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 1), NY)
    assert a.enabled
    dec = scheduler.evaluate([a], at(2026, 10, 17, 7, 0, 1), NY)
    assert dec.ring and not a.enabled and a.ended
    assert a.summary() == "Ended"


def test_disabled_alarm_ignored():
    a = make()
    a.enabled = False
    assert scheduler.evaluate([a], at(2026, 10, 16, 7, 0, 1), NY).ring is None


def test_newly_armed_does_not_ring_past_occurrence():
    a = make(armed=at(2026, 10, 16, 7, 5))
    assert scheduler.evaluate([a], at(2026, 10, 16, 7, 6), NY).ring is None


def test_next_alarm():
    a, b = make(hour=7), make(hour=6, minute=45)
    nxt = scheduler.next_alarm([a, b], at(2026, 10, 16, 5), NY)
    assert nxt[0] is b
