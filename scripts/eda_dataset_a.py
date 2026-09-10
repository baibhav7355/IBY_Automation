"""Exploratory Data Analysis for Dataset A --- ground-truth sessions.

Produces console-formatted statistics useful for tuning the segmentation
heuristics in Phase 3, covering:

  1. Dataset-wide execution statistics (duration, event count per execution).
  2. Process-level breakdown (code -> family_name, avg duration, frequency).
  3. Most common operation-log event types that appear immediately after
     a 'process_started' ground-truth boundary.
  4. App mix per process code.
  5. Anomaly / quirk counts: duplicate process_started, null end_ts.

Usage::

    python scripts/eda_dataset_a.py [--dataset-dir DATASET_DIR] [--top N]

"""
from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline.loader import (
    find_session_event_files,
    load_session_events,
    load_ground_truth,
    load_ground_truth_manifest,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def _parse_ts(ts_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string to a timezone-aware datetime."""
    if ts_str is None:
        return None
    return datetime.fromisoformat(ts_str)


def _fmt(value: float, unit: str = "s") -> str:
    return f"{value:.1f} {unit}"


def _header(title: str, width: int = 72) -> None:
    print()
    print("═" * width)
    print(f"  {title}")
    print("═" * width)


def _sub(title: str) -> None:
    print(f"\n  ── {title} ──")


def _row(label: str, value: Any, indent: int = 4) -> None:
    pad = " " * indent
    print(f"{pad}{label:<45} {value}")


# ──────────────────────────────────────────────────────────────────────────────
# Data loading helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_all_sessions(dataset_dir: Path) -> List[Dict[str, Any]]:
    """Load manifest, gt, and events for every session in dataset_dir.

    Returns a list of per-session dicts with keys:
        session_id, session_dir, manifest, gt_records, events
    """
    sessions = []
    session_dirs = sorted(
        [p for p in dataset_dir.iterdir() if p.is_dir() and p.name.startswith("ses_")]
    )

    for ses_dir in session_dirs:
        manifest = load_ground_truth_manifest(ses_dir)
        gt_records = load_ground_truth(ses_dir)
        if manifest is None or gt_records is None:
            continue  # Skip sessions without ground truth (shouldn't happen for dataset_a)

        # We load events lazily per-session; keep the path list for later
        event_files = find_session_event_files(ses_dir)

        sessions.append(
            {
                "session_id": ses_dir.name,
                "session_dir": ses_dir,
                "manifest": manifest,
                "gt_records": gt_records,
                "event_files": event_files,
            }
        )

    return sessions


# ──────────────────────────────────────────────────────────────────────────────
# Analysis functions
# ──────────────────────────────────────────────────────────────────────────────

def compute_execution_stats(sessions: List[Dict]) -> Dict[str, Any]:
    """Aggregate statistics across all process executions in all sessions."""
    durations: List[float] = []
    exec_counts_per_session: List[int] = []
    per_process: Dict[str, Dict[str, Any]] = {}
    null_end_count = 0
    duplicate_started_count = 0

    for ses in sessions:
        manifest = ses["manifest"]
        gt_records = ses["gt_records"]

        # ── Duplicate process_started check (schema quirk documented) ──
        started_events = [r for r in gt_records if r.get("event") == "process_started"]
        for i in range(1, len(started_events)):
            if started_events[i].get("process_code") == started_events[i - 1].get("process_code"):
                duplicate_started_count += 1

        ses_exec_count = 0
        for proc in manifest.get("processes", []):
            code = proc["code"]
            family = proc.get("family_name", "")
            domain = proc.get("domain", "")
            if code not in per_process:
                per_process[code] = {
                    "family_name": family,
                    "domain": domain,
                    "durations": [],
                    "exec_count": 0,
                    "apps": Counter(),
                    "variants": Counter(),
                }

            for exc in proc.get("executions", []):
                start_ts = exc.get("start_ts")
                end_ts = exc.get("end_ts")
                if start_ts is None:
                    continue
                if end_ts is None:
                    null_end_count += 1
                    # Use next process start (approx) - skip for aggregate stats
                    continue

                start = _parse_ts(start_ts)
                end = _parse_ts(end_ts)
                dur = (end - start).total_seconds()
                durations.append(dur)
                per_process[code]["durations"].append(dur)
                per_process[code]["exec_count"] += 1
                per_process[code]["variants"][exc.get("variant", "?")] += 1
                for app in exc.get("apps", []):
                    per_process[code]["apps"][app] += 1
                ses_exec_count += 1

        exec_counts_per_session.append(ses_exec_count)

    return {
        "total_sessions": len(sessions),
        "total_executions": sum(len(s["manifest"].get("processes", [])) for s in sessions),
        "total_executions_with_end": len(durations),
        "null_end_count": null_end_count,
        "duplicate_started_count": duplicate_started_count,
        "exec_counts_per_session": exec_counts_per_session,
        "all_durations": durations,
        "per_process": per_process,
    }


def compute_event_context_after_boundary(sessions: List[Dict], lookahead: int = 5) -> Counter:
    """Find the most frequent operation-log event_types immediately after each
    process_started ground-truth boundary.

    For each session, we build a timestamp-indexed event list (using the operation
    log), then for each process_started boundary timestamp, we take the next
    `lookahead` events and tally their event_types.
    """
    event_type_counter: Counter = Counter()
    app_counter: Counter = Counter()

    for ses in sessions:
        manifest = ses["manifest"]
        # Load operation log events (with text_input_complete dropped)
        events = load_session_events(ses["session_dir"], text_input_policy="drop")
        if not events:
            continue

        # Index events by timestamp for binary-search-style lookup
        ts_list = [ev.get("timestamp_ms", 0) for ev in events]

        boundaries = manifest.get("expected_boundaries", [])
        for boundary in boundaries:
            if boundary.get("type") not in ("process_started", "process_resumed"):
                continue

            boundary_dt = _parse_ts(boundary["ts"])
            boundary_ms = int(boundary_dt.timestamp() * 1000)

            # Find first event >= boundary_ms
            lo, hi = 0, len(ts_list)
            while lo < hi:
                mid = (lo + hi) // 2
                if ts_list[mid] < boundary_ms:
                    lo = mid + 1
                else:
                    hi = mid
            start_idx = lo

            for ev in events[start_idx: start_idx + lookahead]:
                event_type_counter[ev.get("event_type", "unknown")] += 1
                active_app = (
                    ev.get("context", {}).get("active_app", {}) or {}
                )
                app_name = active_app.get("app_name") or active_app.get("process_name")
                if app_name:
                    app_counter[app_name] += 1

    return event_type_counter, app_counter


def compute_idle_gap_stats(sessions: List[Dict]) -> Dict[str, Any]:
    """Compute statistics about time gaps between consecutive events.

    These gaps can indicate idle periods, which may be natural segmentation points.
    """
    all_gaps: List[float] = []
    large_gaps: List[float] = []
    LARGE_GAP_THRESHOLD_MS = 5_000  # 5 seconds

    for ses in sessions:
        events = load_session_events(ses["session_dir"], text_input_policy="drop")
        for i in range(1, len(events)):
            gap_ms = events[i].get("timestamp_ms", 0) - events[i - 1].get("timestamp_ms", 0)
            if gap_ms > 0:
                all_gaps.append(gap_ms)
                if gap_ms >= LARGE_GAP_THRESHOLD_MS:
                    large_gaps.append(gap_ms)

    if not all_gaps:
        return {}

    all_gaps.sort()
    n = len(all_gaps)
    return {
        "count": n,
        "median_ms": all_gaps[n // 2],
        "p90_ms": all_gaps[int(n * 0.90)],
        "p95_ms": all_gaps[int(n * 0.95)],
        "p99_ms": all_gaps[int(n * 0.99)],
        "large_gap_count": len(large_gaps),
        "large_gap_threshold_ms": LARGE_GAP_THRESHOLD_MS,
        "large_gap_median_ms": sorted(large_gaps)[len(large_gaps) // 2] if large_gaps else 0,
        "large_gap_max_ms": max(large_gaps) if large_gaps else 0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────────

def _stats_summary(values: List[float]) -> str:
    if not values:
        return "N/A"
    n = len(values)
    sv = sorted(values)
    mean = sum(values) / n
    median = sv[n // 2]
    return (
        f"mean={mean:.1f}s  median={median:.1f}s  "
        f"min={sv[0]:.1f}s  max={sv[-1]:.1f}s  (n={n})"
    )


def print_report(
    stats: Dict,
    event_after_boundary_counter: Counter,
    app_after_boundary_counter: Counter,
    gap_stats: Dict,
    top_n: int = 10,
) -> None:
    _header("DATASET A — EXPLORATORY DATA ANALYSIS")

    # ── 1. Dataset overview ──────────────────────────────────────────────────
    _sub("1. Dataset Overview")
    _row("Sessions", stats["total_sessions"])
    _row("Total executions (all sessions)", stats["total_executions_with_end"] + stats["null_end_count"])
    _row("  With valid end_ts", stats["total_executions_with_end"])
    _row("  With null end_ts (skipped)", stats["null_end_count"])
    _row("Duplicate process_started (schema quirk)", stats["duplicate_started_count"])

    exec_counts = stats["exec_counts_per_session"]
    if exec_counts:
        _row("Avg executions / session", f"{sum(exec_counts)/len(exec_counts):.1f}")
        _row("Min / max executions in a session", f"{min(exec_counts)} / {max(exec_counts)}")

    # ── 2. Execution duration statistics ────────────────────────────────────
    _sub("2. Execution Duration (seconds)")
    _row("All processes", _stats_summary(stats["all_durations"]))

    # ── 3. Per-process breakdown ─────────────────────────────────────────────
    _sub("3. Per-Process Breakdown")
    print()
    header = f"  {'Code':<6} {'Family (Japanese)':<30} {'Domain':<10} {'Execs':>6}  Duration"
    print(header)
    print("  " + "─" * (len(header) - 2))
    pp = stats["per_process"]
    for code in sorted(pp.keys()):
        p = pp[code]
        durs = p["durations"]
        dur_str = _stats_summary(durs) if durs else "—"
        print(
            f"  {code:<6} {p['family_name']:<30} {p['domain']:<10} {p['exec_count']:>6}  {dur_str}"
        )

    # ── 4. App mix per process code ──────────────────────────────────────────
    _sub("4. App Mix per Process Code")
    for code in sorted(pp.keys()):
        apps = pp[code]["apps"].most_common(5)
        apps_str = ", ".join(f"{app}({cnt})" for app, cnt in apps) if apps else "—"
        print(f"  {code}: {apps_str}")

    # ── 5. Variants per process code ─────────────────────────────────────────
    _sub("5. Handling Variants per Process Code")
    for code in sorted(pp.keys()):
        variants = pp[code]["variants"]
        v_str = ", ".join(f"{v}({c})" for v, c in variants.most_common()) if variants else "—"
        print(f"  {code}: {v_str}")

    # ── 6. Op-log event types immediately after process_started ─────────────
    _sub(f"6. Operation-Log Event Types in First {top_n} Events After process_started")
    print(f"  (shows heuristic signal for detecting a new process start)\n")
    for event_type, count in event_after_boundary_counter.most_common(top_n):
        bar = "█" * min(count // 5, 40)
        print(f"  {event_type:<35} {count:>6}  {bar}")

    _sub("7. Active App Immediately After process_started Boundary")
    for app, count in app_after_boundary_counter.most_common(top_n):
        bar = "█" * min(count // 5, 40)
        print(f"  {app:<35} {count:>6}  {bar}")

    # ── 8. Inter-event gap statistics ────────────────────────────────────────
    _sub("8. Inter-Event Idle Gap Statistics (operation log)")
    if gap_stats:
        _row("Median gap (ms)", gap_stats["median_ms"])
        _row("p90 gap (ms)", gap_stats["p90_ms"])
        _row("p95 gap (ms)", gap_stats["p95_ms"])
        _row("p99 gap (ms)", gap_stats["p99_ms"])
        _row(
            f"Gaps ≥ {gap_stats['large_gap_threshold_ms']} ms (potential idle markers)",
            gap_stats["large_gap_count"],
        )
        _row("Median of large gaps (ms)", gap_stats["large_gap_median_ms"])
        _row("Largest gap (ms)", gap_stats["large_gap_max_ms"])
    else:
        print("    No gap data available.")

    print()
    print("═" * 72)
    print("  EDA complete. See above for segmentation heuristic insights.")
    print("═" * 72)
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA for Dataset A operation logs with ground truth."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("dataset_a"),
        help="Path to the dataset_a directory (default: dataset_a)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top items to display in frequency lists (default: 10)",
    )
    parser.add_argument(
        "--skip-gaps",
        action="store_true",
        help="Skip expensive inter-event gap computation (faster run)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {args.dataset_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading sessions from: {args.dataset_dir.resolve()}")
    sessions = load_all_sessions(args.dataset_dir)
    print(f"  → {len(sessions)} sessions with ground truth loaded.")

    print("Computing execution statistics...")
    stats = compute_execution_stats(sessions)

    print("Computing operation-log context after boundaries (may take a moment)...")
    event_counter, app_counter = compute_event_context_after_boundary(sessions, lookahead=5)

    gap_stats = {}
    if not args.skip_gaps:
        print("Computing inter-event gap statistics (may take a moment)...")
        gap_stats = compute_idle_gap_stats(sessions)

    print_report(stats, event_counter, app_counter, gap_stats, top_n=args.top)


if __name__ == "__main__":
    main()
