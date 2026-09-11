"""Run segmentation on Dataset B, generate segments.jsonl deliverable,
and mine operational metrics for Step 2 ROI candidate prioritization.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.loader import load_session_events
from src.segmentation.segmenter import GoldenThreadSegmenter
from src.analytics.process_miner import mine_process_metrics, calculate_roi_prioritization


def main() -> None:
    dataset_dir = Path("dataset_b")
    output_path = Path("segments.jsonl")

    if not dataset_dir.exists():
        print(f"ERROR: {dataset_dir} not found.", file=sys.stderr)
        sys.exit(1)

    session_dirs = sorted([p for p in dataset_dir.glob("ses_*") if p.is_dir()])
    print(f"Mining {len(session_dirs)} production sessions from {dataset_dir}...")

    all_segments = []
    session_events_map = {}

    t0 = time.perf_counter()
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, ses_dir in enumerate(session_dirs, 1):
            events = load_session_events(ses_dir, text_input_policy="drop")
            session_events_map[ses_dir.name] = events

            segger = GoldenThreadSegmenter(session_id=ses_dir.name)
            segs = list(segger.segment(events))
            all_segments.extend([s.__dict__ for s in segs])

            for s in segs:
                f.write(json.dumps(s.to_deliverable(), ensure_ascii=False) + "\n")

            print(f"  [{idx:>2}/{len(session_dirs)}] {ses_dir.name}: {len(segs)} segments")

    elapsed = time.perf_counter() - t0
    print(f"\nGenerated {len(all_segments)} segments written to {output_path.resolve()} ({elapsed:.2f}s)")

    # Run Process Mining Analytics
    metrics = mine_process_metrics(all_segments, session_events_map)
    rankings = calculate_roi_prioritization(metrics)

    print("\n" + "=" * 100)
    print("  DATASET B PROCESS MINING & AUTOMATION ROI PRIORITIZATION SCORECARD")
    print("=" * 100)
    header = (
        f"{'Rank':<5} {'Process':<30} {'Volume':<8} {'Avg Dur(s)':<12} "
        f"{'Total(min)':<12} {'AppSwitches':<13} {'Staff':<7} {'Feasibility':<12} {'ROI Score':<10}"
    )
    print(header)
    print("-" * 100)

    for rank, r in enumerate(rankings, 1):
        print(
            f"#{rank:<4} {r['process']:<30} {r['volume']:<8} {r['avg_duration_s']:<12.1f} "
            f"{r['total_time_min']:<12.1f} {r['app_switches_per_exec']:<13.1f} "
            f"{r['staff_count']:<7} {r['feasibility']:<12.2f} {r['roi_score']:<10.1f}"
        )
    print("=" * 100)

    # Save summary report artifact
    report_json = Path("process_mining_results.json")
    report_json.write_text(json.dumps(rankings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Detailed mining metrics saved to: {report_json.resolve()}")


if __name__ == "__main__":
    main()
