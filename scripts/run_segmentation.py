"""Run the Golden Thread Segmenter with LLM Labeling and Semantic Merging
over all Dataset A sessions, write segments.jsonl, then automatically invoke
evaluate_dataset_a.py and print the scorecard.

Usage::

    python scripts/run_segmentation.py [--dataset dataset_a] [--output segments.jsonl]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.loader import load_session_events
from src.segmentation.segmenter import GoldenThreadSegmenter, merge_segments


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run segmentation with LLM labeling and semantic merging on a dataset and evaluate."
    )
    p.add_argument("--dataset", type=Path, default=Path("dataset_a"),
                   help="Dataset directory (default: dataset_a)")
    p.add_argument("--output", type=Path, default=Path("segments.jsonl"),
                   help="Output segments file (default: segments.jsonl)")
    p.add_argument("--no-eval", action="store_true",
                   help="Skip evaluation step")
    p.add_argument("--tolerance", type=int, default=5,
                   help="Boundary tolerance in seconds for evaluator (default: 5)")
    p.add_argument("--use-rules", action="store_true",
                   help="Use domain heuristic rules for labeling instead of mock fallback")
    p.add_argument("--max-gap-s", type=int, default=30,
                   help="Maximum gap in seconds between segments to allow semantic merging (default: 30)")
    return p.parse_args()



def main() -> None:
    args = parse_args()

    if not args.dataset.exists():
        print(f"ERROR: Dataset directory not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    session_dirs = sorted(
        [p for p in args.dataset.iterdir() if p.is_dir() and p.name.startswith("ses_")]
    )
    print(f"Found {len(session_dirs)} sessions in {args.dataset}")

    t0 = time.perf_counter()
    total_segments = 0
    total_events = 0

    with open(args.output, "w", encoding="utf-8") as out_f:
        for idx, ses_dir in enumerate(session_dirs, 1):
            session_id = ses_dir.name
            events = load_session_events(ses_dir, text_input_policy="drop")
            total_events += len(events)

            segmenter = GoldenThreadSegmenter(
                session_id=session_id,
                fallback_to_rules=args.use_rules,
            )
            segments = list(segmenter.segment(events))
            total_segments += len(segments)

            for seg in segments:
                out_f.write(json.dumps(seg.to_deliverable(), ensure_ascii=False) + "\n")

            if idx % 10 == 0 or idx == len(session_dirs):
                elapsed = time.perf_counter() - t0
                print(f"  [{idx:>3}/{len(session_dirs)}]  {session_id}  "
                      f"segments={len(segments)}  elapsed={elapsed:.1f}s")

    elapsed_total = time.perf_counter() - t0
    print(f"\nDone. {total_segments} segments from {len(session_dirs)} sessions "
          f"({total_events} events) in {elapsed_total:.1f}s")
    print(f"Output written to: {args.output.resolve()}")

    if not args.no_eval and args.dataset.name == "dataset_a":
        print("\n" + "="*60)
        print("Running evaluator...")
        print("="*60)
        eval_script = Path(__file__).parent / "evaluate_dataset_a.py"
        result = subprocess.run(
            [
                sys.executable,
                str(eval_script),
                "--predictions", str(args.output),
                "--dataset-dir", str(args.dataset),
                "--tolerance", str(args.tolerance),
            ],
            capture_output=False,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
