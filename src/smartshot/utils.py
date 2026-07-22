from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


_SCREENSHOT_NAME_RE = re.compile(
    r"^Screenshot\s+(?P<date>\d{4}-\d{2}-\d{2})\s+at\s+(?P<time>\d{1,2}\.\d{2}\.\d{2})$",
    re.IGNORECASE,
)


def is_probably_macos_screenshot(path: Path) -> bool:
    if not path.is_file():
        return False

    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return False

    stem = path.stem
    return bool(_SCREENSHOT_NAME_RE.match(stem))


def parse_timestamp_from_macos_screenshot_name(stem: str) -> datetime | None:
    """Parse 'Screenshot YYYY-MM-DD at HH.MM.SS' into a datetime.

    Returns None if the name doesn't match.
    """

    match = _SCREENSHOT_NAME_RE.match(stem)
    if not match:
        return None

    date_str = match.group("date")
    time_str = match.group("time")
    # macOS uses dots in the time segment.
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H.%M.%S")


def safe_slug(text: str, *, max_len: int = 80) -> str:
    """Create a filesystem-friendly slug.

    - Normalizes unicode
    - Keeps letters/digits/spaces/hyphens/underscores
    - Collapses whitespace to single hyphen
    """

    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()

    normalized = re.sub(r"[^a-z0-9 _-]+", "", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")

    if not normalized:
        return "screenshot"

    return normalized[:max_len].rstrip("-")


def ensure_unique_path(path: Path) -> Path:
    """If path exists, append ' (2)', ' (3)' ... before the suffix."""

    if not path.exists():
        return path

    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    for i in range(2, 10_000):
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not find a unique filename for: {path}")
