import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "data"
SOUNDS_DIR = ASSETS_DIR / "sounds"
DEFAULT_PHOTO = ASSETS_DIR / "default-puzzle.png"
CSS_FILE = ASSETS_DIR / "style.css"
SYSTEM_ALARM_SOUND = Path("/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga")
BUNDLED_ALARM_SOUND = SOUNDS_DIR / "alarm-tone.wav"


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    d = Path(base) / "get-outta-bed"
    (d / "recordings").mkdir(parents=True, exist_ok=True)
    return d


def settings_file() -> Path:
    return data_dir() / "settings.json"


def recordings_dir() -> Path:
    return data_dir() / "recordings"


def photo_file() -> Path:
    return data_dir() / "puzzle-photo.jpg"


def log_file() -> Path:
    return data_dir() / "log.txt"
