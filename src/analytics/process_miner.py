"""Process Mining and Automation ROI Candidate Prioritization Module.

Analyzes `segments.jsonl` and raw `events.jsonl` from Dataset B to compute:
  - Volume: Total execution count.
  - Time Consumption: Total cumulative duration and average duration.
  - Friction: Average number of application switches and clipboard transitions.
  - Staff Involvement: Unique sessions and machines.
  - ROI Score: (Volume * Friction) / Average_Duration.

Prints a clean Markdown ranking table of prioritized automation candidates.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class ProcessMetrics:
    """Aggregated operational telemetry metrics for a specific business process."""

    label: str
    execution_count: int = 0
    total_duration_s: float = 0.0
    total_app_switches: int = 0
    total_clipboard_ops: int = 0
    unique_apps: set = field(default_factory=set)
    unique_sessions: set = field(default_factory=set)
    unique_machines: set = field(default_factory=set)

    @property
    def avg_duration_s(self) -> float:
        return self.total_duration_s / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def total_duration_min(self) -> float:
        return self.total_duration_s / 60.0

    @property
    def total_duration_hours(self) -> float:
        return self.total_duration_s / 3600.0

    @property
    def avg_app_switches(self) -> float:
        return self.total_app_switches / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def avg_clipboard_ops(self) -> float:
        return self.total_clipboard_ops / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def friction(self) -> float:
        """Combined operational friction: application switches + clipboard copy/paste transitions."""
        return self.avg_app_switches + self.avg_clipboard_ops

    @property
    def roi_score(self) -> float:
        """Required scoring function: ROI_Score = (Volume * Friction) / Average_Duration."""
        if self.avg_duration_s <= 0:
            return 0.0
        return (self.execution_count * self.friction) / self.avg_duration_s

    @property
    def staff_count(self) -> int:
        return len(self.unique_machines)

    @property
    def session_count(self) -> int:
        return len(self.unique_sessions)


def extract_machine_from_session(session_id: str) -> str:
    """Extract distinct workstation/machine identifier from session naming."""
    parts = session_id.split("-")
    if len(parts) >= 3:
        return parts[-1]
    return session_id


def parse_iso_to_ms(ts_iso: str) -> int:
    """Convert ISO-8601 UTC timestamp string to epoch milliseconds."""
    dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def load_dataset_events(dataset_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load and index raw events from session chunk directories."""
    from src.pipeline.loader import load_session_events

    session_events: Dict[str, List[Dict[str, Any]]] = {}
    for ses_dir in sorted(dataset_dir.glob("ses_*")):
        if ses_dir.is_dir():
            events = load_session_events(ses_dir, text_input_policy="drop")
            session_events[ses_dir.name] = events
    return session_events


def analyze_dataset_b(
    segments_path: Path = Path("segments.jsonl"),
    dataset_dir: Path = Path("dataset_b"),
) -> Tuple[Dict[str, ProcessMetrics], List[Dict[str, Any]]]:
    """Mine metrics from segments.jsonl and Dataset B events.

    Returns:
        Tuple of (metrics_by_label, ranked_table_data).
    """
    if not segments_path.exists():
        raise FileNotFoundError(f"Missing {segments_path}. Run segmentation first.")
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Missing {dataset_dir} directory.")

    session_events = load_dataset_events(dataset_dir)

    metrics_by_label: Dict[str, ProcessMetrics] = {}

    with open(segments_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            session_id = rec["session_id"]
            label = rec.get("label", "process_unknown")
            start_ms = parse_iso_to_ms(rec["start"])
            end_ms = parse_iso_to_ms(rec["end"])
            dur_s = max(0.0, (end_ms - start_ms) / 1000.0)

            if label not in metrics_by_label:
                metrics_by_label[label] = ProcessMetrics(label=label)

            pm = metrics_by_label[label]
            pm.execution_count += 1
            pm.total_duration_s += dur_s
            pm.unique_sessions.add(session_id)
            pm.unique_machines.add(extract_machine_from_session(session_id))

            # Correlate with raw events within segment window
            evs = session_events.get(session_id, [])
            seg_evs = [e for e in evs if start_ms <= e.get("timestamp_ms", 0) <= end_ms]

            app_switches = 0
            clip_ops = 0
            for e in seg_evs:
                etype = e.get("event_type")
                if etype == "app_switch":
                    app_switches += 1
                    pl = e.get("payload") or {}
                    app = (pl.get("new_app") or {}).get("app_name")
                    if app:
                        pm.unique_apps.add(app)
                elif etype == "clipboard_change":
                    clip_ops += 1

            pm.total_app_switches += app_switches
            pm.total_clipboard_ops += clip_ops

    # Rank processes by required formula: ROI_Score = (Volume * Friction) / Average_Duration
    ranked = []
    for label, pm in metrics_by_label.items():
        if label == "process_unknown":
            continue
        ranked.append(
            {
                "process": label,
                "volume": pm.execution_count,
                "total_duration_min": round(pm.total_duration_min, 1),
                "avg_duration_s": round(pm.avg_duration_s, 1),
                "avg_app_switches": round(pm.avg_app_switches, 1),
                "avg_clipboard_ops": round(pm.avg_clipboard_ops, 1),
                "friction": round(pm.friction, 2),
                "sessions_count": pm.session_count,
                "staff_count": pm.staff_count,
                "roi_score": round(pm.roi_score, 2),
            }
        )

    ranked.sort(key=lambda x: x["roi_score"], reverse=True)
    return metrics_by_label, ranked


def print_markdown_table(ranked_data: List[Dict[str, Any]]) -> str:
    """Format and print a clean Markdown ranking table to console."""
    headers = [
        "Rank",
        "Business Process",
        "Volume (N)",
        "Total Time (min)",
        "Avg Dur (s)",
        "App Switches",
        "Clip Ops",
        "Friction",
        "Sessions",
        "Staff",
        "ROI Score",
    ]
    md_lines = []
    md_lines.append("| " + " | ".join(headers) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for rank, r in enumerate(ranked_data, 1):
        row = [
            f"**#{rank}**",
            f"`{r['process']}`",
            f"{r['volume']}",
            f"{r['total_duration_min']:.1f}",
            f"{r['avg_duration_s']:.1f}s",
            f"{r['avg_app_switches']:.1f}",
            f"{r['avg_clipboard_ops']:.1f}",
            f"**{r['friction']:.2f}**",
            f"{r['sessions_count']}/15",
            f"{r['staff_count']}/4",
            f"**{r['roi_score']:.2f}**",
        ]
        md_lines.append("| " + " | ".join(row) + " |")

    table_str = "\n".join(md_lines)
    print("\n" + "=" * 95)
    print("  DATASET B PROCESS MINING & AUTOMATION ROI RANKING (EXACT METRICS)")
    print("  Formula: ROI_Score = (Volume * Friction) / Average_Duration")
    print("=" * 95 + "\n")
    print(table_str)
    print("\n" + "=" * 95)
    return table_str


if __name__ == "__main__":
    _, ranked = analyze_dataset_b()
    print_markdown_table(ranked)
    output_path = Path("process_mining_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(ranked)} ranked process metrics to {output_path.name}")

