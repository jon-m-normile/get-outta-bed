import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import List, Optional

from . import recurrence

PUZZLES = [
    ("jigsaw", "Picture Jigsaw"),
    ("sliding", "Sliding Tile"),
    ("balloon", "Balloon Pop"),
    ("math", "Math"),
    ("simon", "Simon"),
    ("surprise", "Surprise me"),
]
PUZZLE_NAMES = dict(PUZZLES)
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".opus", ".flac"}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Recording:
    id: str
    name: str
    filename: str
    duration: float = 0.0


@dataclass
class Alarm:
    id: str = field(default_factory=new_id)
    hour: int = 7
    minute: int = 0
    label: str = ""
    enabled: bool = True
    rrule: Optional[str] = None
    start_date: str = ""
    max_volume: int = 100
    recordings: List[str] = field(default_factory=list)
    shuffle: bool = False
    puzzle: str = "surprise"
    ended: bool = False
    # ISO UTC instant up to which occurrences have been handled (rung or skipped).
    armed_at: Optional[str] = None

    @property
    def start(self) -> date:
        return date.fromisoformat(self.start_date) if self.start_date else date.today()

    @property
    def dtstart(self) -> datetime:
        return datetime.combine(self.start, time(self.hour, self.minute))

    def next_occurrence(self, after: datetime, tz) -> Optional[datetime]:
        return recurrence.next_occurrence(self.rrule, self.dtstart, after, tz)

    def summary(self) -> str:
        if self.ended:
            return "Ended"
        return recurrence.describe(self.rrule, self.start)

    def time_text(self) -> str:
        return format_time(self.hour, self.minute)

    def arm(self, now: datetime) -> None:
        self.armed_at = now.astimezone(timezone.utc).isoformat()


def format_time(hour: int, minute: int) -> str:
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def _from_dict(cls, d: dict):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in names})


@dataclass
class Settings:
    alarms: List[Alarm] = field(default_factory=list)
    recordings: List[Recording] = field(default_factory=list)
    last_puzzle: Optional[str] = None
    version: int = 1

    def recording(self, rid: str) -> Optional[Recording]:
        return next((r for r in self.recordings if r.id == rid), None)

    def alarm(self, aid: str) -> Optional[Alarm]:
        return next((a for a in self.alarms if a.id == aid), None)

    def remove_recording(self, rid: str) -> None:
        self.recordings = [r for r in self.recordings if r.id != rid]
        for a in self.alarms:
            a.recordings = [x for x in a.recordings if x != rid]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        if not isinstance(d, dict):
            raise ValueError("settings root is not an object")
        return cls(
            alarms=[_from_dict(Alarm, a) for a in d.get("alarms", [])],
            recordings=[_from_dict(Recording, r) for r in d.get("recordings", [])],
            last_puzzle=d.get("last_puzzle"),
            version=d.get("version", 1),
        )


def load(path: Path) -> Settings:
    """Load settings; a corrupt file is backed up and replaced by fresh settings."""
    if not path.exists():
        return Settings()
    try:
        return Settings.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, TypeError, KeyError, OSError) as e:
        backup = path.with_name(f"{path.name}.corrupt-{datetime.now():%Y%m%d-%H%M%S}")
        try:
            path.replace(backup)
        except OSError:
            pass
        from .log import log
        log(f"settings.json was unreadable ({e}); backed up to {backup.name} and started fresh")
        return Settings()


def save(settings: Settings, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
