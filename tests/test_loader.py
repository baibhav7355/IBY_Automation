"""Tests for src.pipeline.loader."""

import json
import pytest
from pathlib import Path
from src.pipeline.loader import (
    find_session_chunks,
    find_session_event_files,
    load_session_events,
    iter_session_events,
    load_ground_truth,
    load_ground_truth_manifest,
)


def test_synthetic_multi_chunk_session(tmp_path):
    """Test loading, multi-chunk sorting, utf-8 encoding, and quirk filtering on synthetic data."""
    session_dir = tmp_path / "ses_test_synthetic"
    chunk_2 = session_dir / "chunk_2"
    chunk_1 = session_dir / "chunk_1"
    chunk_2.mkdir(parents=True)
    chunk_1.mkdir(parents=True)

    # Japanese text samples
    sample_text_1 = "住民税通知確認"
    sample_text_2 = "交通費申請承認"

    # Chunk 2 has later events and an unreliable text_input_complete
    chunk_2_events = [
        {
            "event_id": "evt_3",
            "event_type": "text_input_complete",
            "timestamp_ms": 3000,
            "payload": {"final_text": "buggy_content"},
        },
        {
            "event_id": "evt_4",
            "event_type": "keystroke",
            "timestamp_ms": 4000,
            "payload": {"key": "Enter", "comment": sample_text_2},
        },
    ]

    # Chunk 1 has earlier events
    chunk_1_events = [
        {
            "event_id": "evt_1",
            "event_type": "app_switch",
            "timestamp_ms": 1000,
            "context": {"active_app": {"app_name": sample_text_1}},
        },
        {
            "event_id": "evt_2",
            "event_type": "mouse_click",
            "timestamp_ms": 2000,
            "payload": {"button": "left"},
        },
    ]

    with open(chunk_2 / "events.jsonl", "w", encoding="utf-8") as f:
        for ev in chunk_2_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    with open(chunk_1 / "events.jsonl", "w", encoding="utf-8") as f:
        for ev in chunk_1_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # 1. Test finding chunks
    chunks = find_session_chunks(session_dir)
    assert len(chunks) == 2

    # 2. Test drop policy (default)
    events_dropped = load_session_events(session_dir, text_input_policy="drop")
    assert len(events_dropped) == 3
    # Verify chronological sorting
    assert [ev["event_id"] for ev in events_dropped] == ["evt_1", "evt_2", "evt_4"]
    # Verify UTF-8 Japanese text preservation
    assert events_dropped[0]["context"]["active_app"]["app_name"] == sample_text_1
    assert events_dropped[2]["payload"]["comment"] == sample_text_2

    # 3. Test flag policy
    events_flagged = load_session_events(session_dir, text_input_policy="flag")
    assert len(events_flagged) == 4
    buggy_event = [ev for ev in events_flagged if ev["event_type"] == "text_input_complete"][0]
    assert buggy_event["_is_unreliable"] is True
    assert buggy_event["metadata"]["is_buggy_recording"] is True

    # 4. Test iter_session_events generator
    gen_events = list(iter_session_events(session_dir))
    assert len(gen_events) == 3
    assert [ev["timestamp_ms"] for ev in gen_events] == [1000, 2000, 4000]


def test_real_dataset_a_session():
    """Integration test on a real session from dataset_a."""
    session_dir = Path("dataset_a/ses_20260630-121953-LAPTOP-R36BQBTE")
    if not session_dir.exists():
        pytest.skip("Dataset A session directory not found")

    chunks = find_session_chunks(session_dir)
    assert len(chunks) >= 2, f"Expected multi-chunk session, found {len(chunks)} chunks"

    events = load_session_events(session_dir, text_input_policy="drop")
    assert len(events) > 0

    # Ensure strictly sorted by timestamp_ms
    timestamps = [ev["timestamp_ms"] for ev in events]
    assert all(
        timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1)
    ), "Events are not chronologically sorted"

    # Ensure no text_input_complete events leaked through
    event_types = {ev["event_type"] for ev in events}
    assert "text_input_complete" not in event_types

    # Test loading ground truth
    gt = load_ground_truth(session_dir)
    assert gt is not None and len(gt) > 0

    manifest = load_ground_truth_manifest(session_dir)
    assert manifest is not None
    assert "processes" in manifest


def test_real_dataset_b_session():
    """Integration test on a real session from dataset_b (no ground truth)."""
    session_dir = Path("dataset_b/ses_20260701-171614-CHAITANYA0BCF")
    if not session_dir.exists():
        pytest.skip("Dataset B session directory not found")

    chunks = find_session_chunks(session_dir)
    assert len(chunks) == 2, f"Expected 2 chunks, found {len(chunks)}"

    events = load_session_events(session_dir, text_input_policy="drop")
    assert len(events) > 0

    # Ensure strictly sorted
    timestamps = [ev["timestamp_ms"] for ev in events]
    assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))

    # Dataset B should have no ground truth
    gt = load_ground_truth(session_dir)
    assert gt is None
    gt_manifest = load_ground_truth_manifest(session_dir)
    assert gt_manifest is None
