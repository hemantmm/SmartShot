from __future__ import annotations

from datetime import datetime

from smartshot.utils import (
    ensure_unique_path,
    is_probably_macos_screenshot,
    parse_timestamp_from_macos_screenshot_name,
)


def test_parse_timestamp_from_macos_screenshot_name() -> None:
    parsed = parse_timestamp_from_macos_screenshot_name(
        "Screenshot 2026-05-12 at 11.56.50"
    )

    assert parsed == datetime(2026, 5, 12, 11, 56, 50)


def test_parse_timestamp_returns_none_for_non_screenshot_name() -> None:
    assert parse_timestamp_from_macos_screenshot_name("Login Error") is None


def test_is_probably_macos_screenshot_accepts_standard_name(tmp_path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")

    assert is_probably_macos_screenshot(screenshot)


def test_is_probably_macos_screenshot_rejects_renamed_file(tmp_path) -> None:
    screenshot = tmp_path / "Login Error - 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")

    assert not is_probably_macos_screenshot(screenshot)


def test_ensure_unique_path_adds_suffix_when_file_exists(tmp_path) -> None:
    existing = tmp_path / "Login Error.png"
    existing.write_bytes(b"placeholder")

    assert ensure_unique_path(existing) == tmp_path / "Login Error (2).png"
