from __future__ import annotations

from datetime import datetime
from pathlib import Path

from smartshot.naming import (
    NameSuggestion,
    clean_ocr_for_naming,
    compact_topic,
    format_new_stem_with_options,
    is_low_quality_summary,
    sanitize_filename_component,
    suggest_name,
)


def test_compact_topic_prefers_filename_token() -> None:
    assert compact_topic("Open src/smartshot/naming.py in editor") == "naming"


def test_compact_topic_prefers_domain_label() -> None:
    assert compact_topic("Visit https://superteam.fun for updates") == "superteam"


def test_compact_topic_prefers_visible_heading_over_domain() -> None:
    text = """
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads
    Medium
    Search
    TimeSeries Partitioning Strategy
    The TimeSeries Abstraction was designed to solve the problem of wide
    partitions by dividing the data into discrete time chunks.
    Time Series partitioning breaking up a dataset into Time slices, time buckets and event buckets
    """

    assert compact_topic(text) == "TimeSeries Partitioning Strategy"


def test_compact_topic_ignores_tiny_ocr_noise_near_chart() -> None:
    text = """
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads
    Medium
    Search
    LJ
    Impact of Wide Partitions
    For most of our datasets, we observe an average read latency in the order of
    single-digit milliseconds:
    Ideal Latency for Reads (ms)
    However, in some datasets, as partitions grow too wide, we observe high
    read latencies in the order of seconds, especially towards the tail end:
    """

    assert compact_topic(text) == "Impact Wide Partitions"


def test_compact_topic_ignores_browser_menu_pair() -> None:
    text = """
    Chrome
    File
    Edit
    View
    History
    Bookmarks
    Profiles
    Tab Window
    Help
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads
    TimeSeries Partitioning Strategy
    The TimeSeries Abstraction was designed to solve the problem of wide partitions.
    """

    assert compact_topic(text) == "TimeSeries Partitioning Strategy"


def test_compact_topic_ignores_single_generic_time_label() -> None:
    text = """
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads
    time
    t = time
    TimeSeries Partitioning Strategy
    active interval for reads
    time buckets for efficient time-based access
    """

    assert compact_topic(text) == "TimeSeries Partitioning Strategy"


def test_compact_topic_uses_url_slug_when_heading_is_missing() -> None:
    text = """
    netflixtechblog.com/dynamically-splitting-wide-partitions-in-cassandra-for-time-series-workloads-0eded064f456
    Medium
    Search
    time
    t = time
    active interval for reads
    time buckets for efficient time-based access
    """

    assert compact_topic(text) == "Time Series Partitions by Netflix"


def test_compact_topic_ignores_safari_and_tutorial_tab_title() -> None:
    text = """
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

    assert compact_topic(text) == "Sharded Database"


def test_clean_ocr_for_naming_removes_browser_chrome() -> None:
    text = "Chrome\nTab Window\nSearch\nImpact of Wide Partitions\n100%"

    assert clean_ocr_for_naming(text) == "Impact of Wide Partitions"


def test_is_low_quality_summary_rejects_ui_noise() -> None:
    assert is_low_quality_summary("Tab Window")
    assert is_low_quality_summary("time")
    assert is_low_quality_summary("time by Netflix")
    assert is_low_quality_summary("Tab Window by Netflix")
    assert not is_low_quality_summary("Impact Wide Partitions by Netflix")


def test_compact_topic_uses_heading_like_text() -> None:
    text = "GitHub Issue 482\nFix login redirect after OAuth callback"

    assert compact_topic(text) == "GitHub Issue"


def test_sanitize_filename_component_removes_reserved_characters() -> None:
    assert sanitize_filename_component('Login: failed / "card"?') == "Login failed card"


def test_format_new_stem_can_omit_timestamp() -> None:
    suggestion = NameSuggestion(
        summary="Login Error",
        timestamp=datetime(2026, 5, 12, 11, 56, 50),
    )

    assert format_new_stem_with_options(suggestion, include_timestamp=False) == "Login Error"


def test_format_new_stem_includes_timestamp_by_default() -> None:
    suggestion = NameSuggestion(
        summary="Login Error",
        timestamp=datetime(2026, 5, 12, 11, 56, 50),
    )

    assert (
        format_new_stem_with_options(suggestion)
        == "Login Error - 2026-05-12 at 11.56.50"
    )


def test_suggest_name_uses_macos_screenshot_timestamp(tmp_path: Path) -> None:
    screenshot = tmp_path / "Screenshot 2026-05-12 at 11.56.50.png"
    screenshot.write_bytes(b"placeholder")

    suggestion = suggest_name(screenshot, "Stripe payment failed")

    assert suggestion.summary == "Stripe payment failed"
    assert suggestion.timestamp == datetime(2026, 5, 12, 11, 56, 50)
