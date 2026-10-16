from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from getouttabed import recurrence as r

NY = ZoneInfo("America/New_York")


def local(*args, fold=0):
    return datetime(*args, tzinfo=NY, fold=fold)


def nexts(rule, dtstart, after, k=5):
    out, t = [], after
    for _ in range(k):
        occ = r.next_occurrence(rule, dtstart, t, NY)
        if occ is None:
            break
        out.append(occ.astimezone(NY))
        t = occ
    return out


def wall(dts):
    return [(d.year, d.month, d.day, d.hour, d.minute) for d in dts]


# --- presets ---------------------------------------------------------------

def test_presets_for_third_friday():
    labels = dict(r.presets(date(2026, 10, 16)))
    assert labels["Weekly on Friday"] == "FREQ=WEEKLY;BYDAY=FR"
    assert labels["Monthly on the third Friday"] == "FREQ=MONTHLY;BYDAY=3FR"
    assert labels["Annually on October 16"] == "FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=16"
    assert labels["Every weekday (Monday to Friday)"] == r.WEEKDAYS_RULE
    assert labels["Does not repeat"] is None
    assert labels["Daily"] == "FREQ=DAILY"
    assert "Monthly on the last Friday" not in labels


def test_presets_last_weekday():
    labels = dict(r.presets(date(2026, 10, 30)))  # 5th/last Friday
    assert labels["Monthly on the last Friday"] == "FREQ=MONTHLY;BYDAY=-1FR"
    assert not any(k.startswith("Monthly on the fifth") for k in labels)
    labels = dict(r.presets(date(2026, 10, 26)))  # 4th and last Monday
    assert "Monthly on the fourth Monday" in labels and "Monthly on the last Monday" in labels


def test_does_not_repeat_rings_once():
    start = datetime(2026, 10, 17, 7, 0)
    occs = nexts(None, start, local(2026, 10, 16, 12))
    assert wall(occs) == [(2026, 10, 17, 7, 0)]
    assert r.next_occurrence(None, start, local(2026, 10, 17, 7, 0), NY) is None


def test_daily():
    occs = nexts("FREQ=DAILY", datetime(2026, 10, 16, 6, 45), local(2026, 10, 16, 7), 3)
    assert wall(occs) == [(2026, 10, 17, 6, 45), (2026, 10, 18, 6, 45), (2026, 10, 19, 6, 45)]


def test_weekly_on_weekday():
    occs = nexts("FREQ=WEEKLY;BYDAY=FR", datetime(2026, 10, 16, 7), local(2026, 10, 16, 8), 2)
    assert wall(occs) == [(2026, 10, 23, 7, 0), (2026, 10, 30, 7, 0)]


def test_weekdays_skip_weekend():
    occs = nexts(r.WEEKDAYS_RULE, datetime(2026, 10, 16, 6, 45), local(2026, 10, 16, 7), 3)
    assert wall(occs) == [(2026, 10, 19, 6, 45), (2026, 10, 20, 6, 45), (2026, 10, 21, 6, 45)]


def test_monthly_nth_weekday():
    occs = nexts("FREQ=MONTHLY;BYDAY=3FR", datetime(2026, 10, 16, 7), local(2026, 10, 16, 8), 3)
    assert wall(occs) == [(2026, 11, 20, 7, 0), (2026, 12, 18, 7, 0), (2027, 1, 15, 7, 0)]


def test_monthly_last_weekday():
    occs = nexts("FREQ=MONTHLY;BYDAY=-1FR", datetime(2026, 10, 30, 7), local(2026, 10, 30, 8), 3)
    assert wall(occs) == [(2026, 11, 27, 7, 0), (2026, 12, 25, 7, 0), (2027, 1, 29, 7, 0)]


def test_annual():
    occs = nexts("FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=16", datetime(2026, 10, 16, 7), local(2026, 10, 16, 8), 2)
    assert wall(occs) == [(2027, 10, 16, 7, 0), (2028, 10, 16, 7, 0)]


# --- custom ----------------------------------------------------------------

def test_every_two_weeks_mon_thu():
    rule = r.build_rule("WEEKLY", 2, ["MO", "TH"])
    assert rule == "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,TH"
    occs = nexts(rule, datetime(2026, 10, 19, 7), local(2026, 10, 18), 4)
    assert wall(occs) == [(2026, 10, 19, 7, 0), (2026, 10, 22, 7, 0), (2026, 11, 2, 7, 0), (2026, 11, 5, 7, 0)]


def test_every_three_days():
    occs = nexts(r.build_rule("DAILY", 3), datetime(2026, 10, 16, 7), local(2026, 10, 16, 6), 3)
    assert wall(occs) == [(2026, 10, 16, 7, 0), (2026, 10, 19, 7, 0), (2026, 10, 22, 7, 0)]


def test_monthly_by_day_every_two_months():
    occs = nexts(r.build_rule("MONTHLY", 2, bymonthday=16), datetime(2026, 10, 16, 7), local(2026, 10, 16, 8), 2)
    assert wall(occs) == [(2026, 12, 16, 7, 0), (2027, 2, 16, 7, 0)]


def test_monthly_nth_every_two_months():
    occs = nexts(r.build_rule("MONTHLY", 2, byday=["3FR"]), datetime(2026, 10, 16, 7), local(2026, 10, 16, 8), 2)
    assert wall(occs) == [(2026, 12, 18, 7, 0), (2027, 2, 19, 7, 0)]


def test_every_two_years():
    occs = nexts(r.build_rule("YEARLY", 2, bymonth=3, bymonthday=1), datetime(2026, 3, 1, 7), local(2026, 3, 2), 1)
    assert wall(occs) == [(2028, 3, 1, 7, 0)]


def test_ends_on_date_inclusive():
    rule = r.build_rule("DAILY", until=date(2026, 10, 18))
    occs = nexts(rule, datetime(2026, 10, 16, 7), local(2026, 10, 16, 0), 10)
    assert wall(occs) == [(2026, 10, 16, 7, 0), (2026, 10, 17, 7, 0), (2026, 10, 18, 7, 0)]


def test_ends_after_count():
    rule = r.build_rule("WEEKLY", byday=["MO", "WE"], count=3)
    occs = nexts(rule, datetime(2026, 10, 19, 7), local(2026, 10, 1), 10)
    assert wall(occs) == [(2026, 10, 19, 7, 0), (2026, 10, 21, 7, 0), (2026, 10, 26, 7, 0)]


# --- DST (America/New_York) --------------------------------------------------

def test_spring_forward_gap_rings_one_hour_later_on_clock():
    # 2027-03-14 02:00 EST -> 03:00 EDT; 02:30 does not exist.
    occs = nexts("FREQ=DAILY", datetime(2027, 3, 13, 2, 30), local(2027, 3, 13, 0), 3)
    assert wall(occs) == [(2027, 3, 13, 2, 30), (2027, 3, 14, 3, 30), (2027, 3, 15, 2, 30)]
    assert occs[1].astimezone(timezone.utc).hour == 7


def test_spring_forward_regular_time_keeps_wall_clock():
    occs = nexts("FREQ=DAILY", datetime(2027, 3, 13, 7, 0), local(2027, 3, 13, 0), 2)
    assert wall(occs) == [(2027, 3, 13, 7, 0), (2027, 3, 14, 7, 0)]
    assert occs[1].astimezone(timezone.utc) - occs[0].astimezone(timezone.utc) == timedelta(hours=23)


def test_fall_back_repeated_hour_rings_once():
    # 2026-11-01 02:00 EDT -> 01:00 EST; 01:30 happens twice.
    occs = nexts("FREQ=DAILY", datetime(2026, 10, 31, 1, 30), local(2026, 10, 31, 0), 3)
    assert wall(occs) == [(2026, 10, 31, 1, 30), (2026, 11, 1, 1, 30), (2026, 11, 2, 1, 30)]
    assert occs[2].astimezone(timezone.utc) - occs[1].astimezone(timezone.utc) == timedelta(hours=25)
    second_pass = local(2026, 11, 1, 1, 45, fold=1)
    nxt = r.next_occurrence("FREQ=DAILY", datetime(2026, 10, 31, 1, 30), second_pass, NY).astimezone(NY)
    assert wall([nxt]) == [(2026, 11, 2, 1, 30)]


def test_fall_back_occurrences_between_no_duplicate():
    dt = datetime(2026, 10, 31, 1, 30)
    occs = r.occurrences_between("FREQ=DAILY", dt, local(2026, 11, 1, 0), local(2026, 11, 1, 3), NY)
    assert len(occs) == 1


# --- odd calendar days ---------------------------------------------------------

def test_feb_29_annual_only_leap_years():
    occs = nexts("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29", datetime(2028, 2, 29, 7), local(2028, 3, 1), 2)
    assert wall(occs) == [(2032, 2, 29, 7, 0), (2036, 2, 29, 7, 0)]


def test_31st_skips_short_months():
    occs = nexts("FREQ=MONTHLY;BYMONTHDAY=31", datetime(2026, 1, 31, 7), local(2026, 2, 1), 3)
    assert wall(occs) == [(2026, 3, 31, 7, 0), (2026, 5, 31, 7, 0), (2026, 7, 31, 7, 0)]


# --- descriptions --------------------------------------------------------------

@pytest.mark.parametrize("rule,start,short,long", [
    (None, date(2026, 10, 17), "Does not repeat — Sat, Oct 17", "Does not repeat — Sat, Oct 17"),
    ("FREQ=DAILY", date(2026, 10, 16), "Daily", "Daily"),
    (r.WEEKDAYS_RULE, date(2026, 10, 16), "Weekdays", "Every weekday (Monday to Friday)"),
    ("FREQ=WEEKLY;BYDAY=FR", date(2026, 10, 16), "Weekly on Fri", "Weekly on Friday"),
    ("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,TH", date(2026, 10, 19), "Every 2 weeks on Mon, Thu",
     "Every 2 weeks on Monday and Thursday"),
    ("FREQ=MONTHLY;BYDAY=3FR", date(2026, 10, 16), "Monthly on the third Friday", "Monthly on the third Friday"),
    ("FREQ=MONTHLY;BYDAY=-1FR", date(2026, 10, 30), "Monthly on the last Friday", "Monthly on the last Friday"),
    ("FREQ=MONTHLY;BYMONTHDAY=16", date(2026, 10, 16), "Monthly on day 16", "Monthly on day 16"),
    ("FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=16", date(2026, 10, 16), "Annually on October 16", "Annually on October 16"),
    ("FREQ=DAILY;INTERVAL=3;COUNT=5", date(2026, 10, 16), "Every 3 days, 5 times", "Every 3 days, 5 times"),
])
def test_describe(rule, start, short, long):
    assert r.describe(rule, start) == short
    assert r.describe(rule, start, long=True) == long


def test_describe_until():
    rule = r.build_rule("WEEKLY", 2, ["MO", "TH"], until=date(2026, 12, 19))
    assert r.describe(rule, date(2026, 10, 19), long=True) == "Every 2 weeks on Monday and Thursday, until Dec 19"


def test_default_start_date():
    now = local(2026, 10, 16, 8, 0)
    assert r.default_start_date(7, 0, now) == date(2026, 10, 17)
    assert r.default_start_date(9, 0, now) == date(2026, 10, 16)
