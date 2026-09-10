"""Tests for scripts/evaluate_dataset_a.py evaluation logic.

These tests exercise the core metric functions directly (no subprocess),
using synthetic in-memory fixtures so they run fast and deterministically.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Allow importing scripts/ and src/ from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_dataset_a import (
    compute_boundary_f1,
    compute_segment_iou,
    extract_true_boundaries,
    extract_true_executions,
    load_predictions,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ──────────────────────────────────────────────────────────────────────────────

TOLERANCE_MS = 5_000  # 5 seconds

def _make_manifest(executions: list[dict]) -> dict:
    """Build a minimal gt_manifest-style dict from a list of executions."""
    return {
        "schema_version": "1.1.0",
        "processes": [
            {
                "code": exc["code"],
                "family_name": exc.get("family_name", f"Process-{exc['code']}"),
                "domain": "test",
                "executions": [exc],
            }
            for exc in executions
        ],
    }


def _ms(offset_s: int) -> int:
    """Return epoch-ms for a fixed base + offset_s seconds (base = 1_000_000_000_000)."""
    return 1_000_000_000_000 + offset_s * 1_000


def _iso(offset_s: int) -> str:
    """Return an ISO-8601 UTC string for _ms(offset_s)."""
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(_ms(offset_s) / 1000, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "+00:00")


def _exec(code: str, start_s: int, end_s: int) -> dict:
    return {
        "code": code,
        "family_name": f"Process-{code}",
        "start_ts": _iso(start_s),
        "end_ts": _iso(end_s),
        "exec_id": f"exec-{code}-{start_s}",
    }


# ──────────────────────────────────────────────────────────────────────────────
# extract_true_boundaries
# ──────────────────────────────────────────────────────────────────────────────

class TestExtractTrueBoundaries:
    def test_basic_extraction(self):
        manifest = _make_manifest([_exec("A", 0, 60), _exec("B", 70, 120)])
        boundaries = extract_true_boundaries(manifest)
        # 2 executions × 2 boundaries each = 4
        assert len(boundaries) == 4
        kinds = [b["kind"] for b in boundaries]
        assert kinds.count("start") == 2
        assert kinds.count("end") == 2

    def test_null_end_ts_produces_only_start_boundary(self):
        exec_no_end = {
            "code": "C",
            "family_name": "P-C",
            "start_ts": _iso(0),
            "end_ts": None,
            "exec_id": "exec-C",
        }
        manifest = _make_manifest([exec_no_end])
        boundaries = extract_true_boundaries(manifest)
        assert len(boundaries) == 1
        assert boundaries[0]["kind"] == "start"

    def test_sorted_by_timestamp(self):
        manifest = _make_manifest([_exec("B", 100, 200), _exec("A", 10, 90)])
        boundaries = extract_true_boundaries(manifest)
        ts_list = [b["ts_ms"] for b in boundaries]
        assert ts_list == sorted(ts_list)


# ──────────────────────────────────────────────────────────────────────────────
# compute_boundary_f1
# ──────────────────────────────────────────────────────────────────────────────

class TestBoundaryF1:
    def _true_boundaries(self):
        """Two executions: A[0,60], B[70,120] → 4 boundaries."""
        manifest = _make_manifest([_exec("A", 0, 60), _exec("B", 70, 120)])
        return extract_true_boundaries(manifest)

    def test_perfect_predictions(self):
        true_b = self._true_boundaries()
        # Supply exactly the true timestamps as predictions
        pred_ms = [b["ts_ms"] for b in true_b]
        p, r, f1, details = compute_boundary_f1(pred_ms, true_b, TOLERANCE_MS)
        assert p == pytest.approx(1.0)
        assert r == pytest.approx(1.0)
        assert f1 == pytest.approx(1.0)
        assert len(details) == 4

    def test_zero_predictions(self):
        true_b = self._true_boundaries()
        p, r, f1, details = compute_boundary_f1([], true_b, TOLERANCE_MS)
        assert p == 0.0
        assert r == 0.0
        assert f1 == 0.0
        assert details == []

    def test_tolerance_respected(self):
        # Use executions far apart so +6s shift cannot accidentally match a *different* boundary.
        # A[0,60] and B[200,260] have a 140s gap; cross-boundary leakage is impossible.
        manifest = _make_manifest([_exec("A", 0, 60), _exec("B", 200, 260)])
        true_b = extract_true_boundaries(manifest)  # ts = 0, 60, 200, 260 (all seconds)

        # Within tolerance (+3 s): all 4 should match
        close_pred_ms = [b["ts_ms"] + 3_000 for b in true_b]
        p, r, f1, _ = compute_boundary_f1(close_pred_ms, true_b, TOLERANCE_MS)
        assert f1 == pytest.approx(1.0)

        # Outside tolerance (+6 s): none should match
        far_pred_ms = [b["ts_ms"] + 6_000 for b in true_b]
        p2, r2, f1_2, _ = compute_boundary_f1(far_pred_ms, true_b, TOLERANCE_MS)
        assert f1_2 == pytest.approx(0.0)

    def test_duplicate_predictions_penalised(self):
        """Supplying the same boundary twice should count only one TP."""
        true_b = self._true_boundaries()[:1]  # 1 true boundary
        pred_ms = [true_b[0]["ts_ms"], true_b[0]["ts_ms"]]  # same ts twice
        p, r, f1, details = compute_boundary_f1(pred_ms, true_b, TOLERANCE_MS)
        # 1 TP, 1 FP → precision = 0.5, recall = 1.0
        assert p == pytest.approx(0.5)
        assert r == pytest.approx(1.0)

    def test_partial_recall(self):
        true_b = self._true_boundaries()  # 4 boundaries
        # Only match the first 2
        pred_ms = [b["ts_ms"] for b in true_b[:2]]
        p, r, f1, _ = compute_boundary_f1(pred_ms, true_b, TOLERANCE_MS)
        assert r == pytest.approx(0.5)
        assert p == pytest.approx(1.0)


# ──────────────────────────────────────────────────────────────────────────────
# compute_segment_iou
# ──────────────────────────────────────────────────────────────────────────────

class TestSegmentIoU:
    def _true_execs(self):
        manifest = _make_manifest([_exec("A", 0, 60), _exec("B", 70, 120)])
        return extract_true_executions(manifest)

    def _pred_from_execs(self, true_execs):
        return [{"start_ms": e["start_ms"], "end_ms": e["end_ms"]} for e in true_execs]

    def test_perfect_overlap(self):
        true_execs = self._true_execs()
        preds = self._pred_from_execs(true_execs)
        p, r, f1 = compute_segment_iou(preds, true_execs)
        assert f1 == pytest.approx(1.0)

    def test_zero_overlap(self):
        true_execs = self._true_execs()
        # Predictions completely outside true spans
        preds = [{"start_ms": _ms(200), "end_ms": _ms(300)}]
        p, r, f1 = compute_segment_iou(preds, true_execs)
        assert f1 == pytest.approx(0.0)

    def test_partial_overlap_below_threshold(self):
        true_execs = self._true_execs()[:1]  # A[0,60] → 60 s
        # Overlap only 20 s → IoU = 20/(60+30-20) = 20/70 ≈ 0.286 < 0.5
        preds = [{"start_ms": _ms(40), "end_ms": _ms(70)}]
        p, r, f1 = compute_segment_iou(preds, true_execs, iou_threshold=0.5)
        assert f1 == pytest.approx(0.0)

    def test_partial_overlap_above_threshold(self):
        true_execs = self._true_execs()[:1]  # A[0,60]
        # Overlap 55 s → IoU = 55/(60+60-55) = 55/65 ≈ 0.846 ≥ 0.5
        preds = [{"start_ms": _ms(5), "end_ms": _ms(65)}]
        p, r, f1 = compute_segment_iou(preds, true_execs, iou_threshold=0.5)
        assert f1 > 0.0

    def test_invalid_pred_skipped(self):
        """Predicted segment with end <= start should be ignored."""
        true_execs = self._true_execs()
        preds = [{"start_ms": _ms(10), "end_ms": _ms(5)}]  # reversed
        p, r, f1 = compute_segment_iou(preds, true_execs)
        assert f1 == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# load_predictions
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadPredictions:
    def _write_preds(self, tmp_path, records):
        p = tmp_path / "segments.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p

    def test_basic_load(self, tmp_path):
        records = [
            {"session_id": "ses_A", "start": _iso(0), "end": _iso(60), "label": "proc_a"},
            {"session_id": "ses_A", "start": _iso(70), "end": _iso(120), "label": "proc_b"},
            {"session_id": "ses_B", "start": _iso(0), "end": _iso(30), "label": "proc_c"},
        ]
        p = self._write_preds(tmp_path, records)
        preds = load_predictions(p)
        assert set(preds.keys()) == {"ses_A", "ses_B"}
        assert len(preds["ses_A"]) == 2
        assert len(preds["ses_B"]) == 1

    def test_missing_fields_skipped(self, tmp_path, capsys):
        records = [
            {"session_id": "ses_A", "start": _iso(0), "label": "p"},  # missing end
            {"session_id": "ses_A", "start": _iso(10), "end": _iso(60), "label": "p"},
        ]
        p = self._write_preds(tmp_path, records)
        preds = load_predictions(p)
        assert len(preds["ses_A"]) == 1  # only valid line kept

    def test_malformed_json_skipped(self, tmp_path):
        p = tmp_path / "segments.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write("{bad json\n")
            f.write(json.dumps({"session_id": "ses_A", "start": _iso(0), "end": _iso(60), "label": "p"}) + "\n")
        preds = load_predictions(p)
        assert len(preds["ses_A"]) == 1

    def test_empty_lines_skipped(self, tmp_path):
        p = tmp_path / "segments.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(json.dumps({"session_id": "ses_A", "start": _iso(0), "end": _iso(60), "label": "p"}) + "\n")
        preds = load_predictions(p)
        assert len(preds.get("ses_A", [])) == 1


# ──────────────────────────────────────────────────────────────────────────────
# Integration: evaluate against a real Dataset A session
# ──────────────────────────────────────────────────────────────────────────────

class TestRealDatasetIntegration:
    SESSION = "ses_20260630-121953-LAPTOP-R36BQBTE"
    SESSION_DIR = Path("dataset_a") / SESSION

    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        if not self.SESSION_DIR.exists():
            pytest.skip("Dataset A session directory not found")

    def test_perfect_score_when_using_gt_boundaries(self):
        """Predictions built from valid (non-null) gt executions should yield near-perfect F1.

        NOTE: `extract_true_boundaries` also emits start-only boundaries for
        executions whose end_ts is NULL. Predictions built from `true_execs`
        (which skips null-end_ts rows) will miss those start boundaries,
        so recall cannot reach 1.0 in sessions that have null end_ts records.
        We therefore assert F1 >= 0.90 instead of == 1.0 for robustness.
        """
        from scripts.evaluate_dataset_a import evaluate_session
        from src.pipeline.loader import load_ground_truth_manifest

        manifest = load_ground_truth_manifest(self.SESSION_DIR)
        assert manifest is not None

        true_execs = extract_true_executions(manifest)
        # Build perfect predictions from the executions that have valid end_ts
        preds = [
            {
                "session_id": self.SESSION,
                "start_ms": e["start_ms"],
                "end_ms": e["end_ms"],
                "label": e["code"],
            }
            for e in true_execs
        ]

        result = evaluate_session(self.SESSION, preds, manifest, tolerance_ms=TOLERANCE_MS)
        # Boundary F1 >= 0.90: perfect precision, recall slightly < 1 due to null end_ts
        assert result["boundary_f1"] >= 0.90, (
            f"Boundary F1 too low: {result['boundary_f1']:.4f}. "
            "Check for unexpected boundary mismatches."
        )
        # Segment IoU F1 should be 1.0 since preds match execs exactly
        assert result["segment_f1"] == pytest.approx(1.0, abs=1e-6)

    def test_no_predictions_yields_zero_f1(self):
        from scripts.evaluate_dataset_a import evaluate_session
        from src.pipeline.loader import load_ground_truth_manifest

        manifest = load_ground_truth_manifest(self.SESSION_DIR)
        result = evaluate_session(self.SESSION, [], manifest, tolerance_ms=TOLERANCE_MS)
        assert result["boundary_f1"] == pytest.approx(0.0)
        assert result["segment_f1"] == pytest.approx(0.0)
