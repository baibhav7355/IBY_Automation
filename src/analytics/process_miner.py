"""Process Mining and Automation ROI Candidate Prioritization Module.

Quantifies execution volume, cumulative duration, application-switching friction,
and staff involvement across segmented workstation logs (Dataset B).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ProcessMetrics:
    """Aggregated operational metrics for a specific business process."""

    label: str
    execution_count: int = 0
    total_duration_s: float = 0.0
    total_events: int = 0
    total_app_switches: int = 0
    total_clipboard_ops: int = 0
    unique_apps: set = field(default_factory=set)
    unique_sessions: set = field(default_factory=set)
    unique_users: set = field(default_factory=set)

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
    def avg_app_switches_per_exec(self) -> float:
        return self.total_app_switches / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def avg_events_per_exec(self) -> float:
        return self.total_events / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def staff_count(self) -> int:
        return len(self.unique_users)


def extract_user_from_session_id(session_id: str) -> str:
    """Extract machine/user identifier from standard session directory naming."""
    parts = session_id.split("-")
    if len(parts) >= 3:
        return parts[-1]
    return session_id


def mine_process_metrics(
    segments: List[Dict[str, Any]],
    session_events_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, ProcessMetrics]:
    """Mine aggregated process metrics from segmented logs and raw events.

    Args:
        segments: List of segment dictionaries or Segment objects.
        session_events_map: Optional mapping of session_id -> list of raw events.

    Returns:
        Dict mapping process label -> ProcessMetrics.
    """
    metrics_by_label: Dict[str, ProcessMetrics] = {}

    for seg in segments:
        label = seg.get("label", "process_unknown")
        session_id = seg.get("session_id", "")
        start_ms = seg.get("start_ms", 0)
        end_ms = seg.get("end_ms", 0)

        # Fallback to duration calculation from start_ms/end_ms
        dur_s = (end_ms - start_ms) / 1000.0 if end_ms > start_ms else 0.0
        if dur_s == 0.0 and "duration_s" in seg:
            dur_s = seg["duration_s"]

        if label not in metrics_by_label:
            metrics_by_label[label] = ProcessMetrics(label=label)

        pm = metrics_by_label[label]
        pm.execution_count += 1
        pm.total_duration_s += dur_s
        pm.unique_sessions.add(session_id)
        pm.unique_users.add(extract_user_from_session_id(session_id))

        # Add apps seen
        apps = seg.get("apps_seen") or seg.get("apps") or []
        for a in apps:
            pm.unique_apps.add(a)

        pm.total_events += seg.get("event_count", 0)

        # Detailed event analysis if events are available
        if session_events_map and session_id in session_events_map:
            evs = session_events_map[session_id]
            seg_evs = [e for e in evs if start_ms <= e.get("timestamp_ms", 0) <= end_ms]
            app_switches = sum(1 for e in seg_evs if e.get("event_type") == "app_switch")
            clip_ops = sum(1 for e in seg_evs if e.get("event_type") == "clipboard_change")
            pm.total_app_switches += app_switches
            pm.total_clipboard_ops += clip_ops

    return metrics_by_label


# Feasibility and Rule-Based Automation Scores
# Higher feasibility score = cleaner API/database access, structured rules, lower compliance ambiguity
_FEASIBILITY_SCORES: Dict[str, float] = {
    "supplier_communication": 0.90,  # Highly structured PO / vendor status communication & registration
    "expense_processing": 0.95,      # High volume, strict receipt & policy rules, ERP expense ledger integration
    "inventory_adjustment": 0.85,    # Structured inventory catalog adjustments & stock reconciliations
    "leave_application_processing": 0.80,  # Standard policy checks with human sign-off
    "onboarding_verification": 0.75, # Checklist verification across HR items
    "payroll_adjustment": 0.70,      # High financial sensitivity, requires multi-level checks
    "invoice_approval": 0.85,        # 3-way matching, ERP submission
    "resident_tax_verification": 0.75,
    "budget_variance_analysis": 0.50, # High cognitive ad-hoc analysis in PowerPoint/Excel
    "return_processing": 0.80,
    "shipment_tracking": 0.85,
    "payment_processing": 0.65,      # Direct bank disbursement requires strict human authorization
}


def calculate_roi_prioritization(
    metrics_by_label: Dict[str, ProcessMetrics],
) -> List[Dict[str, Any]]:
    """Compute ROI Prioritization rankings for candidate automation processes.

    Formula:
        ROI Score = (Volume * Avg_Duration_Hours) * (1 + Friction_Penalty) * Feasibility_Weight
        where:
          - Friction_Penalty = log(1 + App_Switches) * 0.25
          - Feasibility_Weight represents implementation feasibility and rule structure (0.0 to 1.0)

    Returns:
        Sorted list of candidate summaries in descending order of ROI score.
    """
    ranked_candidates = []

    for label, pm in metrics_by_label.items():
        if label == "process_unknown" or pm.execution_count == 0:
            continue

        feasibility = _FEASIBILITY_SCORES.get(label, 0.70)
        # Friction index based on app-switch intensity and cross-app context fragmentation
        friction_factor = 1.0 + (pm.avg_app_switches_per_exec * 0.15)

        # Baseline time consumed (hours in sample dataset)
        time_consumed_h = pm.total_duration_hours

        # Annualized projection assuming 250 work days per year (sample represents ~1/2 day of operations)
        # Sample factor: 15 sessions = ~3 staff members over half day -> annual multiplier ~ 500x
        annual_projected_hours = time_consumed_h * 500.0

        # ROI Priority Score
        roi_score = annual_projected_hours * friction_factor * feasibility

        # Estimate savings: 80% automated execution for high-feasibility processes
        automated_saving_pct = 0.80 if feasibility >= 0.80 else 0.65
        net_hours_saved_annual = annual_projected_hours * automated_saving_pct

        ranked_candidates.append(
            {
                "process": label,
                "volume": pm.execution_count,
                "avg_duration_s": round(pm.avg_duration_s, 1),
                "total_time_min": round(pm.total_duration_min, 1),
                "total_time_hours": round(pm.total_duration_hours, 2),
                "app_switches_per_exec": round(pm.avg_app_switches_per_exec, 1),
                "staff_count": pm.staff_count,
                "unique_apps": sorted(list(pm.unique_apps)),
                "feasibility": feasibility,
                "roi_score": round(roi_score, 1),
                "net_hours_saved_annual": round(net_hours_saved_annual, 0),
            }
        )

    # Sort descending by ROI score
    ranked_candidates.sort(key=lambda x: x["roi_score"], reverse=True)
    return ranked_candidates
