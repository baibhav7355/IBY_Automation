"""Ground-truth segmentation evaluator for Dataset A.

Compares a predicted `segments.jsonl` file against the ground truth in
Dataset A's `gt_manifest.json` files.

Metrics
-------
1. **Boundary F1-Score** — Compares predicted segment start/end timestamps
   against each true execution boundary (start_ts / end_ts) using a temporal
   tolerance window (default ±5 s).  Computes Precision, Recall, F1 per
   session and macro-averaged across sessions.

2. **Label Consistency Score** — Checks whether each unique predicted label
   maps consistently to one and only one ground-truth process code/family
   across all sessions.  A label that always maps to the same process
   contributes to a higher consistency score.

Deliverable schema for the prediction file (one JSON object per line)::

    {"session_id": "ses_...", "start": "2026-...", "end": "2026-...", "label": "expense_proc"}

Usage::

    # Basic evaluation
    python scripts/evaluate_dataset_a.py \\
        --predictions predictions/segments.jsonl \\
        --dataset-dir dataset_a

    # Custom tolerance and summary-only output
    python scripts/evaluate_dataset_a.py \\
        --predictions predictions/segments.jsonl \\
        --tolerance 10 --quiet

"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline.loader import load_ground_truth_manifest

# ──────────────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────────────

# A "boundary" is a single timestamp (start or end) with an associated
# ground-truth process code.  Every execution in gt_manifest contributes
# two boundaries: its start_ts and its end_ts.
BoundaryRecord = Dict[str, Any]   # keys: ts_ms (int), ts_iso (str), code, family_name, kind


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if ts_str is None:
        return None
    return datetime.fromisoformat(ts_str)


def _to_ms(dt: Optional[datetime]) -> Optional[int]:
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_f1(p: float, r: float, f1: float) -> str:
    return f"P={_fmt_pct(p)}  R={_fmt_pct(r)}  F1={_fmt_pct(f1)}"


def _header(title: str, width: int = 72) -> None:
    print()
    print("═" * width)
    print(f"  {title}")
    print("═" * width)


def _row(label: str, value: Any, indent: int = 4) -> None:
    print(f"{' ' * indent}{label:<45} {value}")


# ──────────────────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────────────────

def load_predictions(pred_file: Path) -> Dict[str, List[Dict]]:
    """Load predictions and group by session_id.

    Returns:
        Dict mapping session_id → list of prediction records (start_ms, end_ms, label).
    """
    predictions: Dict[str, List[Dict]] = defaultdict(list)
    with open(pred_file, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as err:
                print(f"  WARNING: Skipping malformed JSON at line {line_no}: {err}", file=sys.stderr)
                continue

            session_id = record.get("session_id")
            start_str = record.get("start")
            end_str = record.get("end")
            label = record.get("label", "")

            if not session_id or not start_str or not end_str:
                print(
                    f"  WARNING: Skipping record at line {line_no}: missing required fields "
                    f"(session_id, start, end).",
                    file=sys.stderr,
                )
                continue

            start_dt = _parse_iso(start_str)
            end_dt = _parse_iso(end_str)
            if start_dt is None or end_dt is None:
                print(f"  WARNING: Could not parse timestamps at line {line_no}.", file=sys.stderr)
                continue

            predictions[session_id].append(
                {
                    "session_id": session_id,
                    "start_ms": _to_ms(start_dt),
                    "end_ms": _to_ms(end_dt),
                    "label": label,
                }
            )

    return dict(predictions)


def extract_true_boundaries(manifest: Dict[str, Any]) -> List[BoundaryRecord]:
    """Extract all valid start_ts and end_ts boundaries from gt_manifest.

    Boundaries with null end_ts are still included as start boundaries
    (the end boundary is simply omitted).

    Each returned record has:
        ts_ms: int     - millisecond timestamp
        ts_iso: str    - original ISO string
        code: str      - process code (e.g., 'A')
        family_name: str
        kind: str      - 'start' or 'end'
    """
    boundaries: List[BoundaryRecord] = []
    for proc in manifest.get("processes", []):
        code = proc["code"]
        family = proc.get("family_name", "")
        for exc in proc.get("executions", []):
            start_str = exc.get("start_ts")
            end_str = exc.get("end_ts")

            if start_str:
                start_dt = _parse_iso(start_str)
                boundaries.append(
                    {
                        "ts_ms": _to_ms(start_dt),
                        "ts_iso": start_str,
                        "code": code,
                        "family_name": family,
                        "kind": "start",
                    }
                )
            if end_str:
                end_dt = _parse_iso(end_str)
                boundaries.append(
                    {
                        "ts_ms": _to_ms(end_dt),
                        "ts_iso": end_str,
                        "code": code,
                        "family_name": family,
                        "kind": "end",
                    }
                )

    return sorted(boundaries, key=lambda b: b["ts_ms"])


def extract_true_executions(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract valid executions with both start_ts and end_ts for segment-level evaluation."""
    executions = []
    for proc in manifest.get("processes", []):
        code = proc["code"]
        family = proc.get("family_name", "")
        for exc in proc.get("executions", []):
            start_str = exc.get("start_ts")
            end_str = exc.get("end_ts")
            if start_str and end_str:
                executions.append(
                    {
                        "code": code,
                        "family_name": family,
                        "start_ms": _to_ms(_parse_iso(start_str)),
                        "end_ms": _to_ms(_parse_iso(end_str)),
                        "exec_id": exc.get("exec_id", ""),
                    }
                )
    return sorted(executions, key=lambda e: e["start_ms"])


# ──────────────────────────────────────────────────────────────────────────────
# Boundary F1
# ──────────────────────────────────────────────────────────────────────────────

def compute_boundary_f1(
    pred_boundaries_ms: List[int],
    true_boundaries: List[BoundaryRecord],
    tolerance_ms: int,
) -> Tuple[float, float, float, List[Dict]]:
    """Compute Precision, Recall, F1 for predicted vs. true boundaries.

    Strategy:
    - Each predicted boundary can match at most one true boundary (greedy,
      sorted by temporal distance).
    - A predicted boundary is a True Positive if there exists an unmatched
      true boundary within ±tolerance_ms.
    - Duplicates are False Positives.

    Args:
        pred_boundaries_ms: List of predicted boundary timestamps in ms.
        true_boundaries: List of BoundaryRecord dicts from the manifest.
        tolerance_ms: Matching tolerance in milliseconds.

    Returns:
        (precision, recall, f1, match_details)
        match_details: list of {pred_ms, true_ms, code, kind, delta_ms} for TP matches.
    """
    true_ms_list = [b["ts_ms"] for b in true_boundaries]
    true_used = [False] * len(true_ms_list)
    tp = 0
    match_details = []

    for pred_ms in sorted(pred_boundaries_ms):
        # Find the closest unmatched true boundary within tolerance
        best_idx = -1
        best_delta = float("inf")

        for i, true_ms in enumerate(true_ms_list):
            if true_used[i]:
                continue
            delta = abs(pred_ms - true_ms)
            if delta <= tolerance_ms and delta < best_delta:
                best_delta = delta
                best_idx = i

        if best_idx >= 0:
            tp += 1
            true_used[best_idx] = True
            match_details.append(
                {
                    "pred_ms": pred_ms,
                    "true_ms": true_ms_list[best_idx],
                    "code": true_boundaries[best_idx]["code"],
                    "kind": true_boundaries[best_idx]["kind"],
                    "delta_ms": int(best_delta),
                }
            )

    total_pred = len(pred_boundaries_ms)
    total_true = len(true_ms_list)
    fp = total_pred - tp
    fn = total_true - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1, match_details


# ──────────────────────────────────────────────────────────────────────────────
# Segment-level IoU (for per-execution overlap)
# ──────────────────────────────────────────────────────────────────────────────

def compute_segment_iou(
    pred_segs: List[Dict],
    true_execs: List[Dict],
    iou_threshold: float = 0.5,
) -> Tuple[float, float, float]:
    """Compute segment-level Precision, Recall, F1 using IoU overlap.

    A predicted segment matches a true execution if their temporal
    intersection-over-union exceeds `iou_threshold`.
    """
    true_used = [False] * len(true_execs)
    tp = 0

    for pred in pred_segs:
        ps, pe = pred["start_ms"], pred["end_ms"]
        if pe <= ps:
            continue

        best_iou = 0.0
        best_idx = -1

        for i, true_exc in enumerate(true_execs):
            if true_used[i]:
                continue
            ts, te = true_exc["start_ms"], true_exc["end_ms"]

            inter_start = max(ps, ts)
            inter_end = min(pe, te)
            intersection = max(0, inter_end - inter_start)

            union = (pe - ps) + (te - ts) - intersection
            iou = intersection / union if union > 0 else 0.0

            if iou > best_iou:
                best_iou = iou
                best_idx = i

        if best_idx >= 0 and best_iou >= iou_threshold:
            tp += 1
            true_used[best_idx] = True

    total_pred = len([p for p in pred_segs if p["end_ms"] > p["start_ms"]])
    total_true = len(true_execs)
    fp = total_pred - tp
    fn = total_true - tp

    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


# ──────────────────────────────────────────────────────────────────────────────
# Label consistency
# ──────────────────────────────────────────────────────────────────────────────

def compute_label_consistency(
    predictions: Dict[str, List[Dict]],
    dataset_dir: Path,
    iou_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Check whether each predicted label consistently maps to one process code.

    For every prediction segment, we find the best-overlapping ground-truth
    execution and record the pair (label, process_code).  We then compute how
    often each label maps to its most-frequent code (purity).

    Returns a dict with:
        label_to_codes: {label: Counter({code: count})}
        label_purities: {label: purity}
        macro_purity: float
    """
    label_to_codes: Dict[str, dict] = defaultdict(lambda: defaultdict(int))

    for session_id, preds in predictions.items():
        # Find the session directory
        ses_dir = dataset_dir / session_id
        if not ses_dir.exists():
            continue
        manifest = load_ground_truth_manifest(ses_dir)
        if manifest is None:
            continue

        true_execs = extract_true_executions(manifest)

        for pred in preds:
            ps, pe = pred["start_ms"], pred["end_ms"]
            if pe <= ps:
                continue
            label = pred["label"]

            # Find the best-overlapping ground truth execution
            best_iou = 0.0
            best_code = "__no_match__"

            for exc in true_execs:
                ts, te = exc["start_ms"], exc["end_ms"]
                inter_start = max(ps, ts)
                inter_end = min(pe, te)
                intersection = max(0, inter_end - inter_start)
                union = (pe - ps) + (te - ts) - intersection
                iou = intersection / union if union > 0 else 0.0
                if iou > best_iou:
                    best_iou = iou
                    best_code = exc["code"]

            if best_iou >= iou_threshold:
                label_to_codes[label][best_code] += 1

    label_purities: Dict[str, float] = {}
    for label, code_counts in label_to_codes.items():
        total = sum(code_counts.values())
        most_common_count = max(code_counts.values())
        label_purities[label] = most_common_count / total if total > 0 else 0.0

    macro_purity = (
        sum(label_purities.values()) / len(label_purities) if label_purities else 0.0
    )

    return {
        "label_to_codes": {k: dict(v) for k, v in label_to_codes.items()},
        "label_purities": label_purities,
        "macro_purity": macro_purity,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Per-session evaluation
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_session(
    session_id: str,
    preds: List[Dict],
    manifest: Dict[str, Any],
    tolerance_ms: int,
) -> Dict[str, Any]:
    """Run all metrics for a single session."""
    true_boundaries = extract_true_boundaries(manifest)
    true_execs = extract_true_executions(manifest)

    # Collect predicted boundaries (start + end of each segment)
    pred_boundaries_ms: List[int] = []
    for pred in preds:
        pred_boundaries_ms.append(pred["start_ms"])
        pred_boundaries_ms.append(pred["end_ms"])

    # 1. Boundary F1
    bp, br, bf1, match_details = compute_boundary_f1(
        pred_boundaries_ms, true_boundaries, tolerance_ms
    )

    # 2. Segment IoU F1
    sp, sr, sf1 = compute_segment_iou(preds, true_execs)

    return {
        "session_id": session_id,
        "pred_count": len(preds),
        "true_exec_count": len(true_execs),
        "true_boundary_count": len(true_boundaries),
        "boundary_precision": bp,
        "boundary_recall": br,
        "boundary_f1": bf1,
        "segment_precision": sp,
        "segment_recall": sr,
        "segment_f1": sf1,
        "match_details": match_details,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────────

def print_full_report(
    session_results: List[Dict],
    consistency: Dict,
    tolerance_ms: int,
    quiet: bool,
) -> None:
    _header("DATASET A — SEGMENTATION EVALUATION REPORT")

    # ── Summary ──────────────────────────────────────────────────────────────
    n = len(session_results)
    if n == 0:
        print("  No matching sessions found. Check your session_id values.")
        return

    def _macro_avg(key: str) -> float:
        vals = [r[key] for r in session_results]
        return sum(vals) / len(vals) if vals else 0.0

    b_p = _macro_avg("boundary_precision")
    b_r = _macro_avg("boundary_recall")
    b_f1 = _macro_avg("boundary_f1")
    s_p = _macro_avg("segment_precision")
    s_r = _macro_avg("segment_recall")
    s_f1 = _macro_avg("segment_f1")

    print(f"\n  Evaluated: {n} sessions  |  Boundary tolerance: ±{tolerance_ms // 1000} s")

    print(f"\n  {'Metric':<35} {'Value'}")
    print("  " + "─" * 60)
    print(f"  {'Boundary F1 (macro-avg)':<35} {_fmt_pct(b_f1)}")
    print(f"  {'  Boundary Precision':<35} {_fmt_pct(b_p)}")
    print(f"  {'  Boundary Recall':<35} {_fmt_pct(b_r)}")
    print(f"  {'Segment IoU F1 (macro-avg, IoU≥0.5)':<35} {_fmt_pct(s_f1)}")
    print(f"  {'  Segment Precision':<35} {_fmt_pct(s_p)}")
    print(f"  {'  Segment Recall':<35} {_fmt_pct(s_r)}")
    print(f"  {'Label Consistency (macro purity)':<35} {_fmt_pct(consistency['macro_purity'])}")

    # ── Per-session breakdown ────────────────────────────────────────────────
    if not quiet:
        _header("Per-Session Breakdown")
        hdr = f"  {'Session':<50} {'PredN':>5} {'TrueN':>5}  {'BndF1':>7}  {'SegF1':>7}"
        print(hdr)
        print("  " + "─" * (len(hdr) - 2))
        for r in sorted(session_results, key=lambda x: -x["boundary_f1"]):
            sid = r["session_id"][:48]
            print(
                f"  {sid:<50} {r['pred_count']:>5} {r['true_exec_count']:>5}  "
                f"{_fmt_pct(r['boundary_f1']):>7}  {_fmt_pct(r['segment_f1']):>7}"
            )

    # ── Label consistency breakdown ──────────────────────────────────────────
    if not quiet and consistency["label_to_codes"]:
        _header("Label Consistency Breakdown")
        print(f"\n  {'Label':<30} {'Purity':>7}  Mapped process codes")
        print("  " + "─" * 65)
        for label, purity in sorted(
            consistency["label_purities"].items(), key=lambda x: -x[1]
        ):
            codes = consistency["label_to_codes"].get(label, {})
            codes_str = "  ".join(f"{k}({v})" for k, v in sorted(codes.items(), key=lambda x: -x[1]))
            print(f"  {label:<30} {_fmt_pct(purity):>7}  {codes_str}")

    # ── Final scorecard ──────────────────────────────────────────────────────
    _header("Final Scorecard")
    print(f"""
  ┌─────────────────────────────────────────────┐
  │  Boundary F1        {_fmt_pct(b_f1):>8}  (P={_fmt_pct(b_p)}, R={_fmt_pct(b_r)})  
  │  Segment IoU F1     {_fmt_pct(s_f1):>8}  (P={_fmt_pct(s_p)}, R={_fmt_pct(s_r)})  
  │  Label Consistency  {_fmt_pct(consistency['macro_purity']):>8}                      
  └─────────────────────────────────────────────┘
""")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate segmentation predictions against Dataset A ground truth."
    )
    parser.add_argument(
        "--predictions",
        "-p",
        type=Path,
        required=True,
        help="Path to the predicted segments.jsonl file.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("dataset_a"),
        help="Path to the dataset_a directory (default: dataset_a).",
    )
    parser.add_argument(
        "--tolerance",
        "-t",
        type=int,
        default=5,
        help="Boundary matching tolerance in seconds (default: 5).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Print only the summary scorecard, not per-session detail.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional: write full results to a JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tolerance_ms = args.tolerance * 1000

    if not args.predictions.exists():
        print(f"ERROR: Predictions file not found: {args.predictions}", file=sys.stderr)
        sys.exit(1)

    if not args.dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {args.dataset_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading predictions from: {args.predictions}")
    predictions = load_predictions(args.predictions)
    print(f"  → {len(predictions)} sessions with predictions loaded.")
    print(f"  → {sum(len(v) for v in predictions.values())} total predicted segments.")

    session_results: List[Dict] = []
    unmatched_sessions: List[str] = []

    for session_id, preds in sorted(predictions.items()):
        ses_dir = args.dataset_dir / session_id
        if not ses_dir.exists():
            unmatched_sessions.append(session_id)
            continue
        manifest = load_ground_truth_manifest(ses_dir)
        if manifest is None:
            unmatched_sessions.append(session_id)
            continue

        result = evaluate_session(session_id, preds, manifest, tolerance_ms)
        session_results.append(result)

    if unmatched_sessions:
        print(
            f"\n  WARNING: {len(unmatched_sessions)} predicted session(s) not found "
            f"in {args.dataset_dir}:",
            file=sys.stderr,
        )
        for s in unmatched_sessions[:5]:
            print(f"    - {s}", file=sys.stderr)
        if len(unmatched_sessions) > 5:
            print(f"    ... and {len(unmatched_sessions) - 5} more", file=sys.stderr)

    print("Computing label consistency...")
    consistency = compute_label_consistency(predictions, args.dataset_dir)

    print_full_report(session_results, consistency, tolerance_ms, quiet=args.quiet)

    if args.output_json:
        output = {
            "session_results": [
                {k: v for k, v in r.items() if k != "match_details"}
                for r in session_results
            ],
            "label_consistency": consistency,
            "macro_boundary_f1": (
                sum(r["boundary_f1"] for r in session_results) / len(session_results)
                if session_results else 0.0
            ),
            "macro_segment_f1": (
                sum(r["segment_f1"] for r in session_results) / len(session_results)
                if session_results else 0.0
            ),
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  Results saved to: {args.output_json}")


if __name__ == "__main__":
    main()
