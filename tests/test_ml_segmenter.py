"""Unit tests for ML Golden Thread Segmenter (Phase 3+ Machine Learning)."""

from __future__ import annotations

import pytest
from pathlib import Path
from src.segmentation.ml_segmenter import (
    MLGoldenThreadSegmenter,
    extract_features_from_session,
    extract_execution_context,
    get_app_category,
    is_hub_url,
    FEATURE_NAMES,
)
from src.segmentation.segmenter import Segment


def test_app_category_and_hub_url():
    assert get_app_category("Google Chrome") == 1
    assert get_app_category("EXCEL.EXE") == 2
    assert get_app_category("Microsoft Word") == 3
    assert get_app_category("Notepad") == 4
    assert get_app_category("UnknownApp") == 0

    assert is_hub_url("http://127.0.0.1:5122/#/dashboard") is True
    assert is_hub_url("http://127.0.0.1:5123/index") is True
    assert is_hub_url("http://127.0.0.1:5124") is True
    assert is_hub_url("http://127.0.0.1:5122/payroll/edit/123") is False


def test_feature_extraction_shape_and_empty():
    empty_X = extract_features_from_session([])
    assert empty_X.shape == (0, len(FEATURE_NAMES))

    events = [
        {
            "event_type": "app_switch",
            "timestamp_ms": 1000,
            "correlation": {"ms_since_last_event": 0},
            "context": {
                "active_app": {"app_name": "Google Chrome", "window_title": "HR人事給与システム - Google Chrome"},
                "active_browser_tab": {"url": "http://127.0.0.1:5122/#/dashboard"},
            },
        },
        {
            "event_type": "clipboard_change",
            "timestamp_ms": 5000,
            "correlation": {"ms_since_last_event": 4000},
            "payload": {"text_content": "EMP_98234"},
        },
    ]
    X = extract_features_from_session(events)
    assert X.shape == (2, len(FEATURE_NAMES))
    # Check is_app_sw
    assert X[0, 2] == 1.0
    # Check is_clip
    assert X[1, 3] == 1.0
    # Check has_id for EMP_98234
    assert X[1, 9] == 1.0


def test_extract_execution_context():
    events = [
        {
            "event_type": "browser_navigation",
            "timestamp_ms": 2000,
            "context": {
                "active_browser_tab": {"url": "http://127.0.0.1:5122/#/resident-tax"},
                "active_app": {"window_title": "HR人事給与システム - Google Chrome"},
            },
            "payload": {
                "target_element": {"name": "東京都渋谷区"},
            },
        }
    ]
    doc = extract_execution_context(events, 1000, 3000)
    assert "SYS_HR_5122" in doc
    assert "ROUTE__resident-tax" in doc
    assert "HR人事給与システム" in doc
    assert "東京都渋谷区" in doc


def test_ml_segmenter_initialization_and_fallback():
    # Segmenter with non-existent model paths should fall back gracefully
    segmenter = MLGoldenThreadSegmenter(
        session_id="test_fallback_session",
        boundary_model_path="non_existent_boundary.pkl",
        label_model_path="non_existent_label.pkl",
    )
    assert segmenter.boundary_model is None
    assert segmenter.label_model is None

    # Empty event stream yields no segments
    assert list(segmenter.segment([])) == []


def test_ml_segmenter_with_trained_models():
    # Test loading actual trained production models
    segmenter = MLGoldenThreadSegmenter(session_id="ses_test_ml")
    assert segmenter.boundary_model is not None
    assert segmenter.label_model is not None

    # Synthetic event sequence spanning 40 seconds
    base_t = 1700000000000
    events = []
    # Segment 1: resident tax operations on port 5122
    for i in range(25):
        events.append({
            "event_type": "mouse_click" if i % 2 == 0 else "keystroke",
            "timestamp_ms": base_t + i * 1000,
            "correlation": {"ms_since_last_event": 1000},
            "context": {
                "active_app": {"app_name": "Google Chrome", "window_title": "HR人事給与システム - Google Chrome"},
                "active_browser_tab": {"url": "http://127.0.0.1:5122/#/tax"},
            },
            "payload": {
                "target_element": {"name": "東京都渋谷区"},
                "text_content": "EMP_001",
            },
        })

    # Add an app switch transition boundary
    events.append({
        "event_type": "app_switch",
        "timestamp_ms": base_t + 26000,
        "correlation": {"ms_since_last_event": 1000},
        "context": {
            "active_app": {"app_name": "Google Chrome", "window_title": "財務会計システム - Google Chrome"},
            "active_browser_tab": {"url": "http://127.0.0.1:5123/#/invoices"},
        },
    })

    # Segment 2: invoice operations on port 5123
    for i in range(27, 50):
        events.append({
            "event_type": "mouse_click",
            "timestamp_ms": base_t + i * 1000,
            "correlation": {"ms_since_last_event": 1000},
            "context": {
                "active_app": {"app_name": "Google Chrome", "window_title": "財務会計システム - Google Chrome"},
                "active_browser_tab": {"url": "http://127.0.0.1:5123/#/invoices"},
            },
            "payload": {
                "target_element": {"name": "請求書承認"},
            },
        })

    segs = list(segmenter.segment(events))
    assert len(segs) >= 1
    for s in segs:
        assert isinstance(s, Segment)
        assert s.session_id == "ses_test_ml"
        assert s.start_ms < s.end_ms
        assert s.duration_s > 0
        deliv = s.to_deliverable()
        assert "session_id" in deliv
        assert "start" in deliv
        assert "end" in deliv
        assert "label" in deliv
