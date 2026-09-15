"""
Convert raw vision boundary detections into evaluated segments JSONL.
Formats timestamps to ISO-8601 UTC for evaluation by scripts/evaluate_dataset_a.py.
"""

import json
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone


def convert_boundaries_to_segments(input_jsonl: str, output_jsonl: str):
    sessions = {}

    # 1. Read raw boundaries and group by session extracted from the file path
    with open(input_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            path_str = data["boundary_detected_at"]
            path = PurePosixPath(path_str)

            # Extract session_id from parent directory name (e.g., ses_20260630-135201-LAPTOP-R36BQBTE)
            session_id = None
            for parent in path.parents:
                if parent.name.startswith("ses_"):
                    session_id = parent.name
                    break
            if not session_id:
                session_id = "default_session"

            # Extract timestamp from filename (e.g., scr_smart_1782822011732_monitor_1_post)
            # parts: ['scr', 'smart', '1782822011732', 'monitor', '1', 'post']
            filename = path.stem
            parts = filename.split("_")
            timestamp = None
            for part in parts:
                if part.isdigit() and len(part) >= 10:
                    timestamp = int(part)
                    break

            if timestamp is not None:
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(timestamp)

    # 2. Convert timestamps into explicit start-end segments in ISO-8601 UTC
    segment_records = []
    for session_id, timestamps in sessions.items():
        sorted_ts = sorted(list(set(timestamps)))
        for i in range(len(sorted_ts) - 1):
            start_iso = datetime.fromtimestamp(sorted_ts[i] / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_iso = datetime.fromtimestamp(sorted_ts[i + 1] / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            segment_records.append({
                "session_id": session_id,
                "start": start_iso,
                "end": end_iso,
                "label": "Automated Vision Segment"
            })

    # 3. Write out the valid evaluation contract
    with open(output_jsonl, "w", encoding="utf-8") as out_f:
        for seg in segment_records:
            out_f.write(json.dumps(seg) + "\n")

    print(f"Converted {len(segment_records)} valid segments across {len(sessions)} sessions into {output_jsonl}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert vision boundary detections to JSONL segments.")
    parser.add_argument(
        "--input",
        "-i",
        default="dataset_a/vision_boundaries_multiframe.jsonl",
        help="Input vision boundaries JSONL file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="dataset_a/evaluated_segments.jsonl",
        help="Output evaluation segments JSONL file",
    )
    args = parser.parse_args()

    convert_boundaries_to_segments(
        input_jsonl=args.input,
        output_jsonl=args.output,
    )

