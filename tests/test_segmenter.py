"""Unit tests for the Entity-Centric Golden Thread Segmenter."""
from __future__ import annotations

import pytest
from src.segmentation.segmenter import (
    GoldenThreadSegmenter,
    Segment,
    filter_events,
    extract_segment_context,
    generate_segment_label,
    segment_session,
    _is_hub_url,
    _get_clipboard_anchor,
)


def test_filter_events_discards_noise_and_keeps_state_changers():
    events = [
        {"event_type": "mouse_scroll", "timestamp_ms": 1000},
        {"event_type": "screenshot_smart", "timestamp_ms": 1050},
        {"event_type": "session_start", "timestamp_ms": 1100},
        {
            "event_type": "keystroke",
            "timestamp_ms": 1200,
            "payload": {"key": "a", "modifiers": {"ctrl": False}},
        },
        {
            "event_type": "keystroke",
            "timestamp_ms": 1300,
            "payload": {"key": "c", "modifiers": {"ctrl": True}},  # Ctrl+C shortcut
        },
        {
            "event_type": "mouse_click",
            "timestamp_ms": 1400,
            "payload": {"target_element": {"name": "random text"}},
        },
        {
            "event_type": "mouse_click",
            "timestamp_ms": 1500,
            "payload": {"target_element": {"name": "確定"}},  # Submit/confirm button
        },
        {
            "event_type": "app_switch",
            "timestamp_ms": 1600,
            "payload": {"new_app": {"app_name": "Google Chrome"}},
        },
        {
            "event_type": "clipboard_change",
            "timestamp_ms": 1700,
            "payload": {"text_length": 42},
        },
        {
            "event_type": "browser_navigation",
            "timestamp_ms": 1800,
            "payload": {"url": "http://127.0.0.1:5122/#/dashboard"},
        },
        {
            "event_type": "window_title_change",
            "timestamp_ms": 1900,
            "payload": {"new_title": "財務会計システム - Google Chrome"},
        },
    ]

    filtered = filter_events(events)
    retained_types = [e["event_type"] for e in filtered]

    # Dropped: mouse_scroll, screenshot_smart, session_start, raw keystroke 'a', non-submit click
    assert "mouse_scroll" not in retained_types
    assert "screenshot_smart" not in retained_types
    assert "session_start" not in retained_types
    assert len([e for e in filtered if e["event_type"] == "mouse_click"]) == 1
    assert len([e for e in filtered if e["event_type"] == "keystroke"]) == 1

    # Kept
    assert "app_switch" in retained_types
    assert "clipboard_change" in retained_types
    assert "browser_navigation" in retained_types
    assert "window_title_change" in retained_types


def test_is_hub_url():
    assert _is_hub_url("http://127.0.0.1:5122/")
    assert _is_hub_url("http://127.0.0.1:5122/#/dashboard")
    assert _is_hub_url("http://127.0.0.1:5122/dashboard")
    assert _is_hub_url("https://example.com/index")
    assert _is_hub_url("https://example.com/index.html")
    assert not _is_hub_url("http://127.0.0.1:5122/#/resident-tax")
    assert not _is_hub_url("http://127.0.0.1:5122/form/submit")


def test_get_clipboard_anchor():
    # Text content available
    ev1 = {"event_type": "clipboard_change", "payload": {"text_content": "田中 太郎"}}
    assert _get_clipboard_anchor(ev1) == "田中 太郎"

    # Masked text content, length available
    ev2 = {"event_type": "clipboard_change", "payload": {"text_content": None, "text_length": 55}}
    assert _get_clipboard_anchor(ev2) == "len_55"

    # Non-clipboard
    ev3 = {"event_type": "app_switch", "payload": {}}
    assert _get_clipboard_anchor(ev3) is None


def test_extract_segment_context_and_label():
    events = [
        {
            "event_type": "app_switch",
            "timestamp_ms": 1000,
            "context": {
                "active_app": {
                    "app_name": "Google Chrome",
                    "window_title": "HR人事給与システム - Google Chrome",
                },
                "active_browser_tab": {"url": "http://127.0.0.1:5122/#/leave-applications"},
                "extracted_text": "有給休暇申請書",
            },
        },
        {
            "event_type": "app_switch",
            "timestamp_ms": 2000,
            "context": {
                "active_app": {"app_name": "Microsoft Excel", "window_title": "attendance.xlsx"},
                "extracted_text": "勤怠管理表",
            },
        },
    ]

    ctx = extract_segment_context(events)
    assert ctx["portal_system"] == "HR人事給与システム"
    assert "Google Chrome" in ctx["apps"]
    assert "Microsoft Excel" in ctx["apps"]
    assert "http://127.0.0.1:5122/#/leave-applications" in ctx["urls"]
    assert "有給休暇申請書" in ctx["extracted_text"]

    # Mock fallback returns process_unknown
    label_mock = generate_segment_label(ctx)
    assert label_mock == "process_unknown"

    # Rule-based fallback returns hr_process
    label_rules = generate_segment_label(ctx, fallback_to_rules=True)
    assert label_rules == "hr_process"

    # LLM hook returns LLM summary
    label_llm = generate_segment_label(ctx, llm_fn=lambda c: "custom_hr_task")
    assert label_llm == "custom_hr_task"


def test_golden_thread_segmenter_boundary_detection():
    # Build synthetic event sequence with 2 distinct processes
    base_ms = 1782800000000

    events = [
        # Process 1: Starts in Chrome at Finance portal
        {
            "event_type": "app_switch",
            "timestamp_ms": base_ms,
            "payload": {"new_app": {"app_name": "Google Chrome", "window_title": "財務会計システム - Google Chrome"}},
            "context": {"active_browser_tab": {"url": "http://127.0.0.1:5123/#/invoices"}},
        },
        # Switched to Excel to copy invoice entity
        {
            "event_type": "app_switch",
            "timestamp_ms": base_ms + 5_000,
            "payload": {"new_app": {"app_name": "Microsoft Excel", "window_title": "Invoices.xlsx"}},
        },
        # Anchor copied
        {
            "event_type": "clipboard_change",
            "timestamp_ms": base_ms + 10_000,
            "payload": {"text_length": 50},
        },
        # User returns to Chrome Hub to complete task
        {
            "event_type": "app_switch",
            "timestamp_ms": base_ms + 25_000,
            "payload": {"new_app": {"app_name": "Google Chrome", "window_title": "財務会計システム - Google Chrome"}},
            "context": {"active_browser_tab": {"url": "http://127.0.0.1:5123/#/dashboard"}},
        },
        # Process 2: User switches to HR portal
        {
            "event_type": "app_switch",
            "timestamp_ms": base_ms + 26_000,
            "payload": {"new_app": {"app_name": "Google Chrome", "window_title": "HR人事給与システム - Google Chrome"}},
            "context": {"active_browser_tab": {"url": "http://127.0.0.1:5122/#/onboarding"}},
        },
        # Copy new employee anchor
        {
            "event_type": "clipboard_change",
            "timestamp_ms": base_ms + 35_000,
            "payload": {"text_length": 25},
        },
        # Prolonged idle timeout (>60s)
        {
            "event_type": "app_switch",
            "timestamp_ms": base_ms + 110_000,
            "payload": {"new_app": {"app_name": "Google Chrome", "window_title": "HR人事給与システム - Google Chrome"}},
        },
    ]

    segmenter = GoldenThreadSegmenter(session_id="test_ses", idle_timeout_ms=60_000, min_segment_ms=5_000)
    segments = list(segmenter.segment(events))

    assert len(segments) >= 2
    seg1 = segments[0]
    seg2 = segments[1]

    assert seg1.session_id == "test_ses"
    assert seg1.duration_s >= 5.0
    deliv = seg1.to_deliverable()
    assert deliv["session_id"] == "test_ses"
    assert "start" in deliv
    assert "end" in deliv
    assert deliv["label"] == "process_unknown"
