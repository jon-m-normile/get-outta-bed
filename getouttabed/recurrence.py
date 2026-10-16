"""Repeat rules as RFC 5545 RRULE strings, evaluated in local wall-clock time.

Occurrences are generated as naive local datetimes by dateutil, then localized
with zoneinfo (fold=0). A wall time that falls in the spring-forward gap maps to
the instant one hour later on the clock (2:30 -> 3:30 EDT); a wall time in the
fall-back repeated hour rings only on its first occurrence.
"""
import calendar
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from dateutil.rrule import rrulestr

DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", -1: "last"}
WEEKDAYS_RULE = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
FREQ_UNITS = {"DAILY": "day", "WEEKLY": "week", "MONTHLY": "month", "YEARLY": "year"}

# Lookback when searching for occurrences, wide enough to cover any DST shift.
_SLACK = timedelta(hours=3)


def local_tz():
    from zoneinfo import ZoneInfo
    name = os.environ.get("TZ", "").lstrip(":")
    if not name:
        try:
            name = Path("/etc/timezone").read_text().strip()
        except OSError:
            link = os.path.realpath("/etc/localtime")
            name = link.split("zoneinfo/", 1)[1] if "zoneinfo/" in link else ""
    try:
        return ZoneInfo(name) if name else ZoneInfo("localtime")
    except Exception:
        from dateutil import tz
        return tz.tzlocal()


def to_utc(naive: datetime, tz) -> datetime:
    return naive.replace(tzinfo=tz, fold=0).astimezone(timezone.utc)


def parse_parts(rule: str) -> dict:
    rule = rule.strip()
    if rule.upper().startswith("RRULE:"):
        rule = rule[6:]
    parts = {}
    for item in rule.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip().upper()] = v.strip().upper()
    return parts


def build_rule(freq: str, interval: int = 1, byday: Optional[List[str]] = None,
               bymonthday: Optional[int] = None, bymonth: Optional[int] = None,
               until: Optional[date] = None, count: Optional[int] = None) -> str:
    out = [f"FREQ={freq}"]
    if interval and interval > 1:
        out.append(f"INTERVAL={interval}")
    if bymonth:
        out.append(f"BYMONTH={bymonth}")
    if bymonthday:
        out.append(f"BYMONTHDAY={bymonthday}")
    if byday:
        out.append("BYDAY=" + ",".join(byday))
    if until:
        out.append(f"UNTIL={until.strftime('%Y%m%d')}T235959")
    elif count:
        out.append(f"COUNT={count}")
    return ";".join(out)


def _iter_naive(rule: Optional[str], dtstart: datetime, after: datetime) -> Iterator[datetime]:
    """Naive local occurrences at or after `after` (naive local)."""
    if not rule:
        if dtstart >= after:
            yield dtstart
        return
    rr = rrulestr(rule, dtstart=dtstart)
    yield from rr.xafter(after, inc=True)


def next_occurrence(rule: Optional[str], dtstart: datetime, after: datetime, tz) -> Optional[datetime]:
    """First occurrence strictly after the aware datetime `after`, as aware UTC."""
    after_utc = after.astimezone(timezone.utc)
    start = after_utc.astimezone(tz).replace(tzinfo=None) - _SLACK
    for naive in _iter_naive(rule, dtstart, start):
        occ = to_utc(naive, tz)
        if occ > after_utc:
            return occ
    return None


def occurrences_between(rule: Optional[str], dtstart: datetime, start: datetime, end: datetime, tz) -> List[datetime]:
    """Occurrences with start < occ <= end (aware inputs), as aware UTC, ascending."""
    start_utc, end_utc = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    lookback = start_utc.astimezone(tz).replace(tzinfo=None) - _SLACK
    horizon = end_utc.astimezone(tz).replace(tzinfo=None) + _SLACK
    out, seen = [], set()
    for naive in _iter_naive(rule, dtstart, lookback):
        if naive > horizon:
            break
        occ = to_utc(naive, tz)
        if start_utc < occ <= end_utc and occ not in seen:
            seen.add(occ)
            out.append(occ)
    return sorted(out)


def default_start_date(hour: int, minute: int, now: datetime) -> date:
    """The next date on which hour:minute comes around (today if still ahead)."""
    today = now.date()
    if time(hour, minute) > now.time().replace(tzinfo=None):
        return today
    return today + timedelta(days=1)


def nth_weekday(d: date) -> Tuple[int, bool]:
    """(n, is_last) for d's weekday within its month, e.g. (3, False) for 3rd Friday."""
    n = (d.day - 1) // 7 + 1
    is_last = d.day + 7 > calendar.monthrange(d.year, d.month)[1]
    return n, is_last


def monthly_nth_code(d: date) -> str:
    n, _ = nth_weekday(d)
    return f"{-1 if n == 5 else n}{DAY_CODES[d.weekday()]}"


def presets(d: date) -> List[Tuple[str, Optional[str]]]:
    code, name = DAY_CODES[d.weekday()], DAY_NAMES[d.weekday()]
    n, is_last = nth_weekday(d)
    out = [
        ("Does not repeat", None),
        ("Daily", "FREQ=DAILY"),
        (f"Weekly on {name}", f"FREQ=WEEKLY;BYDAY={code}"),
    ]
    if n <= 4:
        out.append((f"Monthly on the {ORDINALS[n]} {name}", f"FREQ=MONTHLY;BYDAY={n}{code}"))
    if is_last:
        out.append((f"Monthly on the last {name}", f"FREQ=MONTHLY;BYDAY=-1{code}"))
    out.append((f"Annually on {d.strftime('%B')} {d.day}",
                f"FREQ=YEARLY;BYMONTH={d.month};BYMONTHDAY={d.day}"))
    out.append(("Every weekday (Monday to Friday)", WEEKDAYS_RULE))
    return out


def _split_byday(token: str) -> Tuple[int, str]:
    return (int(token[:-2]) if token[:-2] else 0), token[-2:]


def _join(items: List[str], long: bool) -> str:
    if not long or len(items) < 2:
        return ", ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _fmt_date(d: date, ref_year: int) -> str:
    s = f"{d.strftime('%b')} {d.day}"
    return s if d.year == ref_year else f"{s}, {d.year}"


def describe(rule: Optional[str], start: date, long: bool = False) -> str:
    """Plain-English summary; short for list rows, long for the custom dialog."""
    if not rule:
        return f"Does not repeat — {start.strftime('%a')}, {start.strftime('%b')} {start.day}"
    p = parse_parts(rule)
    freq = p.get("FREQ", "DAILY")
    n = int(p.get("INTERVAL", "1") or 1)
    unit = FREQ_UNITS.get(freq, "day")
    every = {"DAILY": "Daily", "WEEKLY": "Weekly", "MONTHLY": "Monthly", "YEARLY": "Annually"}[freq] \
        if n == 1 else f"Every {n} {unit}s"
    if n == 1 and freq == "DAILY":
        text = "Daily"
    elif freq == "DAILY":
        text = f"Every {n} days"
    elif freq == "WEEKLY":
        days = [d for d in DAY_CODES if d in p.get("BYDAY", DAY_CODES[start.weekday()]).split(",")]
        if n == 1 and days == DAY_CODES[:5]:
            text = "Every weekday (Monday to Friday)" if long else "Weekdays"
        elif n == 1 and days == DAY_CODES:
            text = "Daily"
        else:
            names = [(DAY_NAMES if long else DAY_SHORT)[DAY_CODES.index(d)] for d in days]
            text = f"{every} on {_join(names, long)}"
    elif freq == "MONTHLY":
        if "BYDAY" in p:
            k, code = _split_byday(p["BYDAY"].split(",")[0])
            text = f"{every} on the {ORDINALS.get(k, str(k))} {DAY_NAMES[DAY_CODES.index(code)]}"
        else:
            text = f"{every} on day {p.get('BYMONTHDAY', start.day)}"
    else:
        month = int(p.get("BYMONTH", start.month))
        day = int(p.get("BYMONTHDAY", start.day))
        text = f"{every} on {calendar.month_name[month]} {day}"
    if "UNTIL" in p:
        u = datetime.strptime(p["UNTIL"][:8], "%Y%m%d").date()
        text += f", until {_fmt_date(u, start.year)}"
    elif "COUNT" in p:
        c = int(p["COUNT"])
        text += ", once" if c == 1 else f", {c} times"
    return text
