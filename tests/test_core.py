from __future__ import annotations

from pathlib import Path

from smartshot import core


def test_rename_image_uses_ocr_text(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")
    monkeypatch.setattr(core, "extract_text", lambda _path: "GitHub Issue 482")
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(screenshot)

    assert result is not None
    assert result.new_path.name == "GitHub Issue.png"
    assert result.new_path.exists()
    assert not screenshot.exists()


def test_rename_image_dry_run_does_not_move_file(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")
    monkeypatch.setattr(core, "extract_text", lambda _path: "Stripe payment failed")
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(screenshot, dry_run=True)

    assert result is not None
    assert (
        result.new_path.name
        == "Stripe payment failed.png"
    )
    assert screenshot.exists()
    assert not result.new_path.exists()


def test_rename_image_can_append_timestamp(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")
    monkeypatch.setattr(core, "extract_text", lambda _path: "Stripe payment failed")
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(screenshot, dry_run=True, include_timestamp=True)

    assert result is not None
    assert (
        result.new_path.name
        == "Stripe payment failed - 2026-05-12 at 11.56.50.png"
    )


def test_rename_image_skips_unclear_ocr_without_force(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")
    monkeypatch.setattr(core, "extract_text", lambda _path: "")
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    assert core.rename_image(screenshot) is None
    assert screenshot.exists()


def test_rename_image_can_force_unclear_ocr(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")
    monkeypatch.setattr(core, "extract_text", lambda _path: "")
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(screenshot, force=True, include_timestamp=False)

    assert result is not None
    assert result.new_path.name == "screenshot.png"


def test_rename_image_ignores_browser_tab_fragments(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-07-17 at 22.31.56.png"
    screenshot.write_bytes(b"placeholder")
    ocr_text = """
    Chrome
    File
    Edit
    View
    History
    Bookmarks
    Profiles
    Tab Window
    Help
    You jus
    Allow tc
    feat(sy
    Allow ru
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads-0eded064f456
    Medium
    Search
    Serving Reads
    The TimeSeries servers load the partition-keys of completed splits
    periodically into in-memory Bloom filters.
    Here is what the Read path looks like:
    TimeSeries Read Path
    FanoutReader
    WidePartitionReader
    WidePartition BloomFilter
    """
    monkeypatch.setattr(core, "extract_text", lambda _path: ocr_text)
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(screenshot, dry_run=True)

    assert result is not None
    assert result.new_path.name == "Serving Reads - 2026-07-17 at 22.31.56.png"


def test_rename_image_uses_visible_heading_over_safari_source(
    monkeypatch, tmp_path: Path
) -> None:
    screenshot = tmp_path / "Screenshot 2026-07-17 at 22.38.24.png"
    screenshot.write_bytes(b"placeholder")
    ocr_text = """
    Safari
    File
    Edit
    View
    History
    Bookmarks
    Window
    Help
    takeuforward.org
    Sharding - Tutorial
    Blog
    Discussion
    Sharded Database
    Sharding involves distributing data rows across multiple nodes. For example:
    Customer ID
    Name
    State
    Components of Sharding
    """
    monkeypatch.setattr(core, "extract_text", lambda _path: ocr_text)
    monkeypatch.setattr(core, "wait_for_file_ready", lambda _path: True)

    result = core.rename_image(
        screenshot,
        dry_run=True,
        include_timestamp=False,
    )

    assert result is not None
    assert result.new_path.name == "Sharded Database.png"
