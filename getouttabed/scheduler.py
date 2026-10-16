"""Decides which alarms ring on each check. Pure logic; the app calls evaluate()."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from . import recurrence
from .model import Alarm

CHECK_SECONDS = 5
CATCH_UP = timedelta(minutes=15)

Hit = Tuple[Alarm, datetime]


@dataclass
class Decision:
    ring: Optional[Hit] = None
    skipped: List[Hit] = field(default_factory=list)
    suppressed: List[Hit] = field(default_factory=list)
    switched_off: List[Alarm] = field(default_factory=list)
    changed: bool = False


def evaluate(alarms: List[Alarm], now: datetime, tz, ringing: bool = False) -> Decision:
    """Advance every enabled alarm to `now`.

    Occurrences since the alarm was last armed are rung if missed by at most
    CATCH_UP, otherwise skipped. Several alarms due at once ring once; while an
    alarm is already ringing, newly due ones are suppressed.
    """
    dec = Decision()
    due: List[Hit] = []
    for a in alarms:
        if not a.enabled or a.ended:
            continue
        if a.armed_at is None:
            a.arm(now)
            dec.changed = True
            continue
        armed = datetime.fromisoformat(a.armed_at)
        occs = recurrence.occurrences_between(a.rrule, a.dtstart, armed, now, tz)
        if occs:
            *older, latest = occs
            dec.skipped += [(a, o) for o in older]
            if now - latest <= CATCH_UP:
                due.append((a, latest))
            else:
                dec.skipped.append((a, latest))
            a.arm(now)
            dec.changed = True
        if a.next_occurrence(now, tz) is None:
            a.enabled = False
            a.ended = a.rrule is not None
            dec.switched_off.append(a)
            dec.changed = True
    due.sort(key=lambda h: h[1])
    if due and not ringing:
        dec.ring = due[0]
        due = due[1:]
    dec.suppressed = due
    return dec


def next_alarm(alarms: List[Alarm], now: datetime, tz) -> Optional[Hit]:
    best = None
    for a in alarms:
        if not a.enabled or a.ended:
            continue
        occ = a.next_occurrence(now, tz)
        if occ and (best is None or occ < best[1]):
            best = (a, occ)
    return best
