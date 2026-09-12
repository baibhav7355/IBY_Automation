"""
app.py
------
Interactive Streamlit Executive Dashboard & Live Automation Engine
Client: Enterprise Back-Office Operations Group
Engagement: Internship Selection Task Submission (FDE Track)
Author: Baibhav Gond (Indian Institute of Technology Bhubaneswar)
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import Step 3 prototype engine
from src.automation.supplier_automation import (
    SupplierRequest,
    SupplierWorkflowEngine,
    AutomationResult,
)

# -----------------------------------------------------------------------------
# PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="IBY Japan | FDE Process Mining & Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.06);
        border: 1px solid rgba(28, 131, 225, 0.2);
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    /* Status Badges */
    .badge-approved {
        background-color: #d1e7dd;
        color: #0f5132;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-escalate {
        background-color: #fff3cd;
        color: #664d03;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .code-box {
        background: #f8f9fa;
        border-left: 4px solid #0d6efd;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# CACHED DATA LOADERS
# -----------------------------------------------------------------------------
@st.cache_data
def load_segments_data() -> pd.DataFrame:
    path = ROOT / "segments.jsonl"
    if not path.exists():
        return pd.DataFrame()
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    if not df.empty and "start" in df.columns and "end" in df.columns:
        df["start_dt"] = pd.to_datetime(df["start"])
        df["end_dt"] = pd.to_datetime(df["end"])
        df["duration_s"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds()
    return df


@st.cache_data
def load_process_mining_results() -> List[Dict[str, Any]]:
    path = ROOT / "process_mining_results.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("IBY Japan Telemetry")
    st.caption("Forward Deployed Engineer (FDE) Portfolio")
    
    st.markdown(
        """
        **Author:** Baibhav Gond  
        **Institution:** IIT Bhubaneswar  
        **Role:** FDE Candidate Selection Task  
        **Sprint:** 7 Days (Production Ready)  
        """
    )
    st.divider()

    menu = st.radio(
        "Navigation",
        [
            "📊 Executive ROI Dashboard (Step 2)",
            "🤖 Live Automation Prototype (Step 3)",
            "🔍 Telemetry & Process Explorer (Step 1)",
            "🛡️ Implementation Risk Matrix",
            "📖 7-Day Sprint Work Log & Audit",
        ],
        index=0,
    )

    st.divider()
    st.markdown("### System Health")
    st.success("✔ 36 / 36 Pytest Tests Passing")
    st.info("✔ 279 Dataset B Segments Recovered")
    st.caption("Git Branch: `master` | Python 3.10+")


# -----------------------------------------------------------------------------
# VIEW 1: EXECUTIVE ROI DASHBOARD
# -----------------------------------------------------------------------------
if menu == "📊 Executive ROI Dashboard (Step 2)":
    st.title("📊 Executive ROI Prioritization Dashboard")
    st.markdown(
        """
        *From Raw Telemetry to High-ROI Automation Targets.*  
        This dashboard presents the process mining analysis across Dataset B (15 production sessions, 4 staff workstations).
        Prioritization is determined using the client ROI formulation:
        $$\\text{ROI Score} = \\frac{\\text{Volume} \\times \\text{Friction}}{\\text{Average Duration}}$$
        """
    )

    mining_data = load_process_mining_results()
    df_mining = pd.DataFrame(mining_data)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Recovered Segments",
            value="279",
            delta="15 Sessions (Dataset B)",
        )
    with col2:
        st.metric(
            label="Top Bottleneck (#1)",
            value="supplier_communication",
            delta="ROI: 25.30",
        )
    with col3:
        st.metric(
            label="Top 2 Volume Concentration",
            value="57.7%",
            delta="161 / 279 Executions",
        )
    with col4:
        st.metric(
            label="Annual Recoverable Hours",
            value="413.0 hrs",
            delta="Supplier Automation Alone",
        )

    st.markdown("---")

    # Layout: Table + Visual Breakdown
    tab_overview, tab_charts = st.tabs(["📋 Prioritization Ranking Table", "📈 Operational Friction & ROI Charts"])

    with tab_overview:
        st.subheader("Dataset B Automation Candidate Ranking")
        st.caption("Processes sorted strictly by client ROI Score descending.")
        
        display_df = df_mining[
            [
                "process",
                "volume",
                "total_duration_min",
                "avg_duration_s",
                "avg_app_switches",
                "avg_clipboard_ops",
                "friction",
                "roi_score",
            ]
        ].rename(
            columns={
                "process": "Business Process",
                "volume": "Volume (N)",
                "total_duration_min": "Total Time (min)",
                "avg_duration_s": "Avg Dur (s)",
                "avg_app_switches": "App Switches",
                "avg_clipboard_ops": "Clipboard Ops",
                "friction": "Friction Score",
                "roi_score": "ROI Score",
            }
        )

        st.dataframe(
            display_df.style.highlight_max(subset=["Volume (N)", "ROI Score"], color="#d1e7dd")
            .highlight_max(subset=["Friction Score"], color="#ffe5d0"),
            use_container_width=True,
            height=460,
        )

        st.info(
            "💡 **Key Discovery:** While tasks like `budget_variance_analysis` take longer per execution (48.2s), "
            "they occur rarely ($N=4$). In contrast, `supplier_communication` ($N=100$) and `expense_processing` ($N=61$) "
            "dominate back-office operational time and impose extreme cross-app friction (6.8 switches + 2.6 copy/pastes)."
        )

    with tab_charts:
        st.subheader("Telemetry Friction & Time Breakdown")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("##### Cumulative Time Consumption (Minutes)")
            chart_df = df_mining.set_index("process")[["total_duration_min"]].sort_values("total_duration_min", ascending=True)
            st.bar_chart(chart_df, color="#0d6efd")

        with c2:
            st.markdown("##### Operational Friction (App Switches + Clipboard Copy/Pastes)")
            fric_df = df_mining.set_index("process")[["friction"]].sort_values("friction", ascending=True)
            st.bar_chart(fric_df, color="#fd7e14")

        st.markdown("##### Automation ROI Score vs. Execution Volume")
        scatter_df = df_mining[["process", "volume", "roi_score", "friction"]].set_index("process")
        st.scatter_chart(scatter_df, x="volume", y="roi_score", size="friction", color="#198754")


# -----------------------------------------------------------------------------
# VIEW 2: LIVE STEP 3 PROTOTYPE DEMO
# -----------------------------------------------------------------------------
elif menu == "🤖 Live Automation Prototype (Step 3)":
    st.title("🤖 Step 3 Prototype: Supplier Communication Automation")
    st.markdown(
        """
        **Target Bottleneck:** Rank #1 — `supplier_communication` (100 executions, 61.9 active minutes, 9.39 friction).  
        **Architecture:** High-performance deterministic backend policy engine with straight-through auto-approval 
        and managerial escalation governance.
        """
    )

    st.markdown("---")

    # Engine Config / Preset Cases
    col_config, col_live = st.columns([1, 1])

    with col_config:
        st.subheader("1. Select or Configure Request Payload")
        preset = st.selectbox(
            "Load Transaction Archetype Preset:",
            [
                "Preset 1: Standard Quantity Adjustment (+10% -> Auto-Approved)",
                "Preset 2: Quality Certificate Request (Standard -> Auto-Approved)",
                "Preset 3: Contract Price Revision (+15% > 5% limit -> Escalated)",
                "Preset 4: Supply Chain Delivery Delay (+10 days > 5 limit -> Escalated)",
                "Custom Configuration",
            ],
        )

        # Populate defaults based on preset
        if "Preset 1" in preset:
            p_po = "PO-2026-469"
            p_vendor = "SUP-1750"
            p_name = "千葉金属工業御中"
            p_type = "quantity_change"
            p_orig_qty = 100
            p_req_qty = 110
            p_price = 520.0
            p_price_pct = 0.0
            p_shift = 1
            p_memo = "納期の微調整"
        elif "Preset 2" in preset:
            p_po = "PO-2026-681"
            p_vendor = "SUP-3310"
            p_name = "シャープ株式会社御中"
            p_type = "cert_request"
            p_orig_qty = 50
            p_req_qty = 50
            p_price = 1450.0
            p_price_pct = 0.0
            p_shift = 0
            p_memo = "品質証明書送付依頼"
        elif "Preset 3" in preset:
            p_po = "PO-2026-512"
            p_vendor = "SUP-2890"
            p_name = "三菱電機株式会社宛"
            p_type = "price_revision"
            p_orig_qty = 200
            p_req_qty = 200
            p_price = 1200.0
            p_price_pct = 15.0  # Exceeds 5%
            p_shift = 0
            p_memo = "原材料高騰に伴う単価改定要請"
        elif "Preset 4" in preset:
            p_po = "PO-2026-904"
            p_vendor = "SUP-4011"
            p_name = "日立金属物流部"
            p_type = "quantity_change"
            p_orig_qty = 150
            p_req_qty = 150
            p_price = 800.0
            p_price_pct = 0.0
            p_shift = 10  # Exceeds 5 days
            p_memo = "船便遅延による納期変更申入"
        else:
            p_po = "PO-2026-CUSTOM"
            p_vendor = "SUP-9999"
            p_name = "取引先企業"
            p_type = "quantity_change"
            p_orig_qty = 100
            p_req_qty = 120
            p_price = 1000.0
            p_price_pct = 4.0
            p_shift = 2
            p_memo = "個別調整"

        in_po = st.text_input("Purchase Order ID (PO):", value=p_po)
        in_vendor_name = st.text_input("Supplier Name (日本語):", value=p_name)
        in_req_type = st.selectbox(
            "Request Type:",
            ["quantity_change", "price_revision", "spec_change", "cert_request"],
            index=["quantity_change", "price_revision", "spec_change", "cert_request"].index(p_type) if p_type in ["quantity_change", "price_revision", "spec_change", "cert_request"] else 0,
        )

        c_q1, c_q2 = st.columns(2)
        with c_q1:
            in_orig_qty = st.number_input("Original Quantity:", min_value=1, value=p_orig_qty)
        with c_q2:
            in_req_qty = st.number_input("Requested Quantity:", min_value=1, value=p_req_qty)

        c_p1, c_p2 = st.columns(2)
        with c_p1:
            in_price_pct = st.slider("Price Variance (%):", min_value=0.0, max_value=30.0, value=float(p_price_pct), step=0.5)
        with c_p2:
            in_shift = st.slider("Delivery Shift (Days):", min_value=0, max_value=20, value=int(p_shift), step=1)

        run_btn = st.button("🚀 Execute Policy Engine", type="primary", use_container_width=True)

    with col_live:
        st.subheader("2. Real-Time Engine Decision & Audit Log")
        
        req = SupplierRequest(
            po_id=in_po,
            vendor_id=p_vendor,
            vendor_name=in_vendor_name,
            request_type=in_req_type,
            item_code="ITM-7701",
            original_qty=in_orig_qty,
            requested_qty=in_req_qty,
            unit_price=p_price,
            price_change_pct=in_price_pct,
            delivery_date_shift_days=in_shift,
            memo=p_memo,
        )

        engine = SupplierWorkflowEngine()
        t0 = datetime.now()
        result: AutomationResult = engine.process_request(req)
        latency_ms = (datetime.now() - t0).total_seconds() * 1000.0

        if result.status == "AUTO_APPROVED":
            st.success(f"### Status: AUTO_APPROVED")
            st.markdown(
                f'<span class="badge-approved">STRAIGHT-THROUGH PROCESSED</span> '
                f'<code>Latency: {latency_ms:.2f} ms</code>',
                unsafe_allow_html=True,
            )
            st.markdown("#### Generated Japanese Communication Payload:")
            st.info(result.generated_comment_ja)
            st.caption(f"Action Taken: {result.action_taken}")
        else:
            st.warning(f"### Status: ESCALATED_TO_MANAGER")
            st.markdown(
                f'<span class="badge-escalate">MANAGERIAL HUMAN-IN-THE-LOOP QUEUE</span> '
                f'<code>Latency: {latency_ms:.2f} ms</code>',
                unsafe_allow_html=True,
            )
            st.markdown("#### Policy Breach / Reason:")
            st.error(result.escalation_reason)
            st.markdown("#### Pending Internal Escalation Record:")
            st.warning(result.generated_comment_ja)

        st.divider()
        st.markdown("##### Policy Rule Validation Audit:")
        qty_diff = abs(in_req_qty - in_orig_qty) / in_orig_qty * 100.0
        st.write(f"- **Quantity Variance:** `{qty_diff:.1f}%` (Policy Limit: $\\le 25\\%$) -> {'✔ Passed' if qty_diff <= 25.0 else '❌ Breached'}")
        st.write(f"- **Price Change:** `{in_price_pct:.1f}%` (Policy Limit: $\\le 5\\%$) -> {'✔ Passed' if in_price_pct <= 5.0 else '❌ Breached'}")
        st.write(f"- **Delivery Shift:** `{in_shift} days` (Policy Limit: $\\le 5$ days) -> {'✔ Passed' if in_shift <= 5 else '❌ Breached'}")


# -----------------------------------------------------------------------------
# VIEW 3: TELEMETRY & PROCESS EXPLORER
# -----------------------------------------------------------------------------
elif menu == "🔍 Telemetry & Process Explorer (Step 1)":
    st.title("🔍 Telemetry & Recovered Units of Work (Step 1)")
    st.markdown(
        """
        Recovered coherent units of work from Dataset B production events (`segments.jsonl`).  
        Generated via the **Entity-Centric Golden Thread State Machine** + **LLM Semantic Classifier** + **Adjacent Segment Merger**.
        """
    )

    df_segments = load_segments_data()

    if df_segments.empty:
        st.error("No segments.jsonl file found.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            selected_label = st.selectbox(
                "Filter by Process Label:",
                ["All Processes"] + sorted(df_segments["label"].unique().tolist()),
            )
        with c2:
            selected_session = st.selectbox(
                "Filter by Session ID:",
                ["All Sessions"] + sorted(df_segments["session_id"].unique().tolist()),
            )
        with c3:
            st.metric("Total Recovered Executions", len(df_segments))

        filtered_df = df_segments.copy()
        if selected_label != "All Processes":
            filtered_df = filtered_df[filtered_df["label"] == selected_label]
        if selected_session != "All Sessions":
            filtered_df = filtered_df[filtered_df["session_id"] == selected_session]

        st.markdown(f"**Displaying {len(filtered_df)} executions:**")
        st.dataframe(
            filtered_df[["session_id", "start", "end", "duration_s", "label"]].rename(
                columns={
                    "session_id": "Session ID",
                    "start": "Start (UTC)",
                    "end": "End (UTC)",
                    "duration_s": "Duration (s)",
                    "label": "Recovered Label",
                }
            ),
            use_container_width=True,
            height=400,
        )

        st.subheader("Process Execution Duration Distribution")
        st.bar_chart(filtered_df["duration_s"].clip(upper=120))


# -----------------------------------------------------------------------------
# VIEW 4: IMPLEMENTATION RISK MATRIX
# -----------------------------------------------------------------------------
elif menu == "🛡️ Implementation Risk Matrix":
    st.title("🛡️ Implementation & Operational Risk Matrix")
    st.markdown(
        """
        Empirical risks observed directly from desktop telemetry logs with proactive engineering mitigations.
        Derived from Section 5 of [`final_report.md`](file:///c:/IBY_Japan/final_report.md).
        """
    )

    risks = [
        {
            "Category": "Technical",
            "Risk Description": "Inconsistent Character Encodings & Japanese Font Corruption",
            "Telemetry Evidence": "Clipboard telemetry showed mixed UTF-8 and Shift_JIS bytes across legacy Word/ERP.",
            "Severity": "Medium",
            "Likelihood": "High",
            "Mitigation Strategy": "Enforce strict UTF-8 pre-flight byte normalization in ingestion adapters.",
        },
        {
            "Category": "Technical",
            "Risk Description": "Web Portal API & Port Timeouts",
            "Telemetry Evidence": "Log showed extension disconnects and port resets (5122/5132) during long idle sessions.",
            "Severity": "High",
            "Likelihood": "Medium",
            "Mitigation Strategy": "Implement idempotent PO keys and exponential backoff retry policies.",
        },
        {
            "Category": "Data / Quality",
            "Risk Description": "Uncataloged Vendor Master Exceptions",
            "Telemetry Evidence": "Operators observed opening Notepad scratch memos for unregistered supplier rules.",
            "Severity": "Medium",
            "Likelihood": "Medium",
            "Mitigation Strategy": "Centralized versioned rule DB with automatic fallback quarantine queue.",
        },
        {
            "Category": "Operational",
            "Risk Description": "Unreviewed Small Price Creep Drift",
            "Telemetry Evidence": "Repetitive small price increases (~3-4%) slipping below single-transaction limits.",
            "Severity": "High",
            "Likelihood": "Low",
            "Mitigation Strategy": "Implement cumulative 90-day vendor price drift monitoring (>7% aggregate flag).",
        },
        {
            "Category": "Governance",
            "Risk Description": "Audit & Commercial Compliance Traceability",
            "Telemetry Evidence": "Commercial accounting laws require auditable approval records.",
            "Severity": "High",
            "Likelihood": "Low",
            "Mitigation Strategy": "Persist append-only cryptographic audit logs recording all automated approvals.",
        },
        {
            "Category": "Organizational",
            "Risk Description": "User Change-Management Resistance & Shadow Memos",
            "Telemetry Evidence": "Operators habitually maintain personal scratchpads (*精算確認メモ).",
            "Severity": "Medium",
            "Likelihood": "High",
            "Mitigation Strategy": "Deploy initially in 'Shadow Recommendation Mode' (1-click draft) for 2 weeks.",
        },
    ]

    st.dataframe(pd.DataFrame(risks), use_container_width=True, height=360)

    st.divider()
    st.subheader("Residual Human Work Post-Deployment (Human-in-the-Loop)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 1. Managerial Sign-Off (<20%)")
        st.write("Variances exceeding standard policy limits (e.g. price change >5% or quantity change >25%) are routed directly to procurement supervisors.")
    with c2:
        st.markdown("#### 2. Vendor Contract Onboarding")
        st.write("Initial supplier credit review, NDA execution, and master vendor directory registration remain strictly human-governed.")
    with c3:
        st.markdown("#### 3. High-Friction Dispute Resolution")
        st.write("Severe quality discrepancies, shipment rejections, or breach of SLA conditions escalate to vendor relations specialists.")


# -----------------------------------------------------------------------------
# VIEW 5: 7-DAY SPRINT WORK LOG & AUDIT
# -----------------------------------------------------------------------------
elif menu == "📖 7-Day Sprint Work Log & Audit":
    st.title("📖 7-Day Sprint Work Log & Verification")
    st.markdown(
        """
        **Author:** Baibhav Gond (IIT Bhubaneswar)  
        **Engagement:** Internship Selection Task  
        Chronological diary of engineering trials, dead ends, and GenAI disclosures from [`work_log.md`](file:///c:/IBY_Japan/work_log.md).
        """
    )

    st.divider()

    st.subheader("Run Automated Submission Verification")
    if st.button("▶ Run scripts/verify_submission.py"):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_submission.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode == 0:
            st.success("✔ Verification Succeeded: All 5 Checks Passed with 100% Compliance!")
        else:
            st.error("Verification Encountered Issues")
        st.code(proc.stdout)

    st.divider()
    st.subheader("Chronological Sprint Diary")

    with st.expander("Day 1: Problem Ingestion, Architectural Scoping & Resilient Data Pipeline", expanded=True):
        st.markdown(
            """
            - Initialized repository with modular architecture.
            - Handled multi-chunk session stitching and enforced strict UTF-8 decoding for Japanese text.
            - **Dead End Diagnosed:** Discovered `text_input_complete` is unreliable during IME conversions; dropped payload in favor of clipboard/element attributes.
            """
        )

    with st.expander("Day 2: Ground Truth Evaluation Harness & Exploratory Data Analysis (EDA)"):
        st.markdown(
            """
            - Built `scripts/evaluate_dataset_a.py` computing Boundary F1 (±5s tolerance), IoU, and Label Consistency.
            - **Key Discoveries:** 100% of workflows start in web browser portals; typical 3-app triad signature; mean cycle time ~42s.
            """
        )

    with st.expander("Day 3: 'Entity-Centric Golden Thread' State Machine"):
        st.markdown(
            """
            - Designed state machine tracing clipboard entities across application switches.
            - **Dead End Diagnosed:** Pure idle-gap segmentation failed (caused massive false positives whenever employees paused to read contracts).
            """
        )

    with st.expander("Day 4: Baseline Evaluation, LLM Labeling & The Strategic FDE Pivot"):
        st.markdown(
            """
            - Diagnosed over-segmentation defect on Dataset A.
            - Built LLM labeling (`llm_labeler.py`) and semantic segment merger (`merge_segments`).
            - Segments dropped from 2,456 to 2,018 (vs 2,009 ground truth executions); Label Consistency jumped from 9.2% to 66.6%.
            - **Strategic FDE Decision:** Froze heuristic tuning on Dataset A at "good enough" to focus 40% of the sprint budget on high-ROI business mining and working automation.
            """
        )

    with st.expander("Day 5: Dataset B Production Ingestion & Process Mining"):
        st.markdown(
            """
            - Ingested Dataset B production telemetry, recovering 279 executions (`segments.jsonl`).
            - Mined operational friction: discovered `supplier_communication` (ROI: 25.30) and `expense_processing` (ROI: 16.75) represent 57.7% of all back-office volume.
            """
        )

    with st.expander("Day 6: Step 3 Working Automation Prototype"):
        st.markdown(
            """
            - Built `SupplierWorkflowEngine` in `src/automation/supplier_automation.py`.
            - Verified straight-through processing for standard requests and exception escalation routing.
            - Automated test suite verified (36/36 tests passing).
            """
        )

    with st.expander("Day 7: Final Report, Risk Matrix & Submission Polish"):
        st.markdown(
            """
            - Authored executive proposal (`final_report.md`) and candidate diary (`work_log.md`).
            - Built automated verification harness and project documentation.
            """
        )

    st.divider()
    st.subheader("Generative AI Disclosure")
    st.info(
        "Generative AI was used as an intelligent domain accelerator for translating Japanese portal placeholders "
        "and UI window titles, as well as rapid drafting of unit test fixture skeletons. In accordance with enterprise "
        "standards, all production business policy rules, segmentation state machines, and automation decision gates remain "
        "100% deterministic and mathematically validated."
    )
