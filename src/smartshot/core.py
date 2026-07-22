from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .naming import (
    format_new_stem_with_options,
    suggest_name,
)
from .ocr import extract_text
from .utils import ensure_unique_path


@dataclass(frozen=True)
class RenameResult:
    original_path: Path
    new_path: Path
    ocr_text: str


def wait_for_file_ready(
    path: Path,
    *,
    timeout_s: float = 10.0,
    stable_for_s: float = 0.5,
    poll_s: float = 0.1,
) -> bool:
    """Wait until file size stops changing (best-effort)."""

    start = time.time()
    last_size: int | None = None
    last_change = time.time()

    while True:
        now = time.time()
        if now - start > timeout_s:
            return False

        try:
            size = path.stat().st_size
        except FileNotFoundError:
            time.sleep(poll_s)
            continue
        except Exception:
            # If we can't stat, just retry a bit.
            time.sleep(poll_s)
            continue

        if last_size is None or size != last_size:
            last_size = size
            last_change = now
        elif now - last_change >= stable_for_s:
            return True

        time.sleep(poll_s)


def rename_image(
    image_path: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    include_timestamp: bool = False,
) -> RenameResult | None:
    """Rename an image file based on OCR content.

    Returns RenameResult when a rename is (or would be) performed.
    Returns None when no rename is performed.
    """

    image_path = Path(image_path)
    if not image_path.exists() or not image_path.is_file():
        return None

    # Wait for the screenshot to finish writing.
    wait_for_file_ready(image_path)

    ocr_text = extract_text(image_path)

    suggestion = suggest_name(image_path, ocr_text)

    # If we couldn't derive anything useful, skip unless forced.
    if not force and suggestion.summary.lower() in {"screenshot", "screen-shot", "screen shot"}:
        return None

    new_stem = format_new_stem_with_options(
        suggestion, include_timestamp=include_timestamp
    )
    candidate = image_path.with_name(f"{new_stem}{image_path.suffix}")

    # No-op
    if candidate.resolve() == image_path.resolve():
        return None

    candidate = ensure_unique_path(candidate)

    if not dry_run:
        image_path.rename(candidate)

    return RenameResult(
        original_path=image_path,
        new_path=candidate,
        ocr_text=ocr_text,
    )
