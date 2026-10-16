import threading
from datetime import datetime

from . import paths

MAX_LINES = 1000
_lock = threading.Lock()


def log(message: str, path=None) -> None:
    path = path or paths.log_file()
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {message}\n"
    with _lock:
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
            lines.append(line)
            lines = lines[-MAX_LINES:]
            tmp = path.with_suffix(".tmp")
            tmp.write_text("".join(lines), encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            print(f"log write failed: {e}: {line}", end="")
