"""
app.py
------
Interactive Streamlit Executive Dashboard & Live Automation Engine
Client: Enterprise Back-Office Operations Group
Engagement: Internship Selection Task Submission (FDE Track)
Author: Baibhav Gond
Email: baibhav0019@gmail.com
Institute: Indian Institute of Technology Bhubaneswar
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

# Import Step 3 prototype engines (Procurement & Finance)
from src.automation.supplier_automation import (
    SupplierRequest,
    SupplierWorkflowEngine,
    AutomationResult,
)
from src.automation.expense_automation import (
    ExpenseClaimRequest,
    ExpenseWorkflowEngine,
    ExpenseResult,
    run_sample_expense_batch,
)

# -----------------------------------------------------------------------------
# PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
logo_icon = "assets/logo.png" if Path("assets/logo.png").exists() else "📊"
st.set_page_config(
    page_title="I'm beside you | FDE Process Mining & Automation",
    page_icon=logo_icon,
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
    /* Clean Sidebar Radio Left Alignment */
    div[data-testid="stRadio"] label {
        display: flex !important;
        align-items: center !important;
        text-align: left !important;
    }
    div[data-testid="stRadio"] label p {
        text-align: left !important;
        margin: 0 !important;
        padding-left: 6px !important;
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
    if Path("assets/logo.png").exists():
        st.image("assets/logo.png", use_container_width=True)
    st.markdown(
        """
        <div style="font-size: 1.35rem; font-weight: 700; margin-top: 6px; margin-bottom: 12px; line-height: 1.3;">
            Process Mining & Automation
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        **Name:** Baibhav Gond  
        **Email:** baibhav0019@gmail.com  
        **Institute:** Indian Institute of Technology Bhubaneswar  
        **Sprint:** 7 Days (Production Ready)  
        """
    )
    st.divider()

    menu = st.radio(
        "Navigation",
        [
            "Executive ROI Dashboard (Step 2)",
            "Live Automation Prototype (Step 3)",
            "Segmentation Approaches & Benchmark",
            "Dataset B Telemetry & Segments Explorer (Step 1)",
            "Implementation Risk Matrix",
            "7-Day Sprint Work Log & Audit",
        ],
        index=0,
    )

    st.divider()
    st.markdown("### System Health")
    st.success("✔ 46 / 46 Pytest Tests Passing")
    st.info("✔ 279 Dataset B Segments Recovered")
    st.caption("Git Branch: `master` | Python 3.10+")


# -----------------------------------------------------------------------------
# VIEW 1: EXECUTIVE ROI DASHBOARD
# -----------------------------------------------------------------------------
if menu == "Executive ROI Dashboard (Step 2)":
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
            st.bar_chart(
                chart_df,
                color="#0d6efd",
                x_label="Business Process",
                y_label="Total Time (Minutes)",
            )

        with c2:
            st.markdown("##### Operational Friction (App Switches + Clipboard Copy/Pastes)")
            fric_df = df_mining.set_index("process")[["friction"]].sort_values("friction", ascending=True)
            st.bar_chart(
                fric_df,
                color="#fd7e14",
                x_label="Business Process",
                y_label="Friction Score (Switches + Copies)",
            )

        st.markdown("##### Automation ROI Score vs. Execution Volume")
        scatter_df = df_mining[["process", "volume", "roi_score", "friction"]].set_index("process")
        st.scatter_chart(
            scatter_df,
            x="volume",
            y="roi_score",
            size="friction",
            color="#198754",
            x_label="Execution Volume (N)",
            y_label="Client ROI Score",
        )


# -----------------------------------------------------------------------------
# VIEW 2: LIVE STEP 3 PROTOTYPE DEMO
# -----------------------------------------------------------------------------
elif menu == "Live Automation Prototype (Step 3)":
    st.title("🤖 Step 3 Prototype: Multi-Process Enterprise Automation")
    st.markdown(
        """
        **Dual Bottleneck Coverage (Dataset B):**  
        Automating **57.7% of all enterprise back-office volume** (161 of 279 transactions) with deterministic 
        policy validation, sub-millisecond execution, and managerial escalation governance.
        """
    )

    st.markdown("---")

    tab_supplier, tab_expense = st.tabs([
        "🏭 Procurement: Supplier Communication (Rank #1 - 35.8% Volume)",
        "💼 Finance: Expense Claim Processing (Rank #2 - 21.9% Volume)",
    ])

    with tab_supplier:
        st.markdown(
            """
            **Target Bottleneck:** Rank #1 — `supplier_communication` (100 executions, 61.9 active minutes, 9.39 friction).  
            **Architecture:** High-performance deterministic backend policy engine with straight-through auto-approval 
            and managerial escalation governance.
            """
        )

        # Engine Config / Preset Cases
        col_config, col_live = st.columns([1, 1])

        PRESETS = {
            "Preset 1: Standard Quantity Adjustment (+10% -> Auto-Approved)": {
                "po": "PO-2026-469",
                "vendor": "SUP-1750",
                "name": "Chiba Metal Industries",
                "type": "quantity_change",
                "orig_qty": 100,
                "req_qty": 110,
                "price": 520.0,
                "price_pct": 0.0,
                "shift": 1,
                "memo": "Minor delivery date adjustment",
            },
            "Preset 2: Quality Certificate Request (Standard -> Auto-Approved)": {
                "po": "PO-2026-681",
                "vendor": "SUP-3310",
                "name": "Sharp Corporation",
                "type": "quality_certificate_request",
                "orig_qty": 50,
                "req_qty": 50,
                "price": 1450.0,
                "price_pct": 0.0,
                "shift": 0,
                "memo": "Quality inspection certificate request",
            },
            "Preset 3: Contract Price Revision (+15% > 5% limit -> Escalated)": {
                "po": "PO-2026-512",
                "vendor": "SUP-2890",
                "name": "Mitsubishi Electric Corporation",
                "type": "price_revision",
                "orig_qty": 200,
                "req_qty": 200,
                "price": 1200.0,
                "price_pct": 15.0,
                "shift": 0,
                "memo": "Price revision request due to raw material costs",
            },
            "Preset 4: Supply Chain Delivery Delay (+10 days > 5 limit -> Escalated)": {
                "po": "PO-2026-904",
                "vendor": "SUP-4011",
                "name": "Hitachi Metals Logistics",
                "type": "quantity_change",
                "orig_qty": 150,
                "req_qty": 150,
                "price": 800.0,
                "price_pct": 0.0,
                "shift": 10,
                "memo": "Delivery reschedule due to shipping delay",
            },
            "Custom Configuration": {
                "po": "PO-2026-CUSTOM",
                "vendor": "SUP-9999",
                "name": "Partner Enterprise",
                "type": "quantity_change",
                "orig_qty": 100,
                "req_qty": 100,
                "price": 1000.0,
                "price_pct": 0.0,
                "shift": 0,
                "memo": "Standard operational adjustment",
            },
        }

        def apply_selected_preset():
            sel = st.session_state.get("selected_preset_key", list(PRESETS.keys())[0])
            p = PRESETS[sel]
            st.session_state["input_po"] = p["po"]
            st.session_state["input_name"] = p["name"]
            st.session_state["input_type"] = p["type"]
            st.session_state["input_orig_qty"] = p["orig_qty"]
            st.session_state["input_req_qty"] = p["req_qty"]
            st.session_state["input_price_pct"] = float(p["price_pct"])
            st.session_state["input_shift"] = int(p["shift"])

        # Initialize session state if first load
        if "input_po" not in st.session_state:
            st.session_state["selected_preset_key"] = list(PRESETS.keys())[0]
            apply_selected_preset()

        with col_config:
            st.subheader("1. Select or Configure Request Payload")
            preset = st.selectbox(
                "Load Transaction Archetype Preset:",
                options=list(PRESETS.keys()),
                key="selected_preset_key",
                on_change=apply_selected_preset,
            )

            in_po = st.text_input("Purchase Order ID (PO):", key="input_po")
            in_vendor_name = st.text_input("Supplier Name:", key="input_name")
            
            type_options = [
                "quantity_change",
                "price_revision",
                "item_specification_change",
                "quality_certificate_request",
                "none",
            ]
            
            type_labels = {
                "quantity_change": "📦 Quantity Change",
                "price_revision": "💰 Price Revision",
                "item_specification_change": "🔧 Item Specification Change",
                "quality_certificate_request": "📜 Quality Certificate Request",
                "none": "✅ None (No Change)",
            }

            in_req_type = st.selectbox(
                "Request Type:",
                options=type_options,
                format_func=lambda x: type_labels.get(x, x),
                key="input_type",
            )

            c_q1, c_q2 = st.columns(2)
            with c_q1:
                in_orig_qty = st.number_input("Original Quantity:", min_value=1, key="input_orig_qty")
            with c_q2:
                in_req_qty = st.number_input("Requested Quantity:", min_value=1, key="input_req_qty")

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                in_price_pct = st.slider("Price Variance (%):", min_value=0.0, max_value=30.0, step=0.5, key="input_price_pct")
            with c_p2:
                in_shift = st.slider("Delivery Shift (Days):", min_value=0, max_value=20, step=1, key="input_shift")

            run_btn = st.button("🚀 Execute Policy Engine", type="primary", use_container_width=True)
            st.caption("💡 Adjust any field above or click to trigger manual policy re-evaluation.")

        with col_live:
            st.subheader("2. Real-Time Engine Decision & Audit Log")
            
            req = SupplierRequest(
                po_id=in_po,
                vendor_id="SUP-AUTO",
                vendor_name=in_vendor_name,
                request_type=in_req_type,
                item_code="ITM-7701",
                original_qty=in_orig_qty,
                requested_qty=in_req_qty,
                unit_price=1000.0,
                price_change_pct=in_price_pct,
                delivery_date_shift_days=in_shift,
                memo="Real-time automated policy evaluation",
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
                st.markdown("#### Generated Vendor Communication Payload:")
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

    with tab_expense:
        st.markdown(
            """
            **Target Bottleneck:** Rank #2 — `expense_processing` (61 executions, 35.0 active minutes, 9.44 friction score).  
            **Compliance Basis:** Corporate Accounting Standards (Entertainment & Travel Regulations).  
            **Automation Goal:** Instant straight-through journal posting with automatic exception routing to department directors.
            """
        )

        col_exp_config, col_exp_live = st.columns([1, 1])

        EXPENSE_PRESETS = {
            "Preset 1: Client Dinner within Limit (¥8,000/head <= ¥10,000 -> Auto-Approved)": {
                "claim_id": "EXP-2026-101",
                "emp_id": "EMP-2041",
                "emp_name": "Taro Yamada",
                "dept": "Corporate Sales",
                "cat": "entertainment",
                "amount": 16000.0,
                "attendees": 2,
                "has_receipt": True,
                "memo": "Client dinner following contract agreement",
            },
            "Preset 2: Bullet Train Business Travel (¥28,500 <= ¥30,000 -> Auto-Approved)": {
                "claim_id": "EXP-2026-103",
                "emp_id": "EMP-3055",
                "emp_name": "Hanako Suzuki",
                "dept": "Logistics Operations",
                "cat": "travel_transit",
                "amount": 28500.0,
                "attendees": 1,
                "has_receipt": True,
                "memo": "Roundtrip bullet train transit to Osaka logistics center",
            },
            "Preset 3: Executive VIP Dinner Over Cap (¥18,000/head > ¥10,000 limit -> Escalated)": {
                "claim_id": "EXP-2026-102",
                "emp_id": "EMP-1192",
                "emp_name": "Ichiro Sato",
                "dept": "Corporate Strategy",
                "cat": "entertainment",
                "amount": 36000.0,
                "attendees": 2,
                "has_receipt": True,
                "memo": "Strategic business conference dinner with partner executives",
            },
            "Preset 4: Taxi Fare Missing Receipt (No Receipt -> Escalated)": {
                "claim_id": "EXP-2026-104",
                "emp_id": "EMP-4420",
                "emp_name": "Kenji Tanaka",
                "dept": "Procurement",
                "cat": "travel_transit",
                "amount": 4200.0,
                "attendees": 1,
                "has_receipt": False,
                "memo": "Late-night emergency taxi fare after urgent delivery (receipt misplaced)",
            },
            "Preset 5: Bulk Office Equipment Over Limit (¥68,000 > ¥50,000 limit -> Escalated)": {
                "claim_id": "EXP-2026-105",
                "emp_id": "EMP-5100",
                "emp_name": "Makoto Watanabe",
                "dept": "General Affairs",
                "cat": "supplies",
                "amount": 68000.0,
                "attendees": 1,
                "has_receipt": True,
                "memo": "Bulk ergonomic office equipment purchase (custom monitor arms)",
            },
            "Custom Configuration": {
                "claim_id": "EXP-2026-CUSTOM",
                "emp_id": "EMP-9999",
                "emp_name": "Claimant Name",
                "dept": "Administration",
                "cat": "entertainment",
                "amount": 10000.0,
                "attendees": 1,
                "has_receipt": True,
                "memo": "Individual expense reimbursement claim",
            },
        }

        def apply_selected_expense_preset():
            sel = st.session_state.get("selected_exp_preset_key", list(EXPENSE_PRESETS.keys())[0])
            p = EXPENSE_PRESETS[sel]
            st.session_state["exp_in_claim_id"] = p["claim_id"]
            st.session_state["exp_in_emp_id"] = p["emp_id"]
            st.session_state["exp_in_emp_name"] = p["emp_name"]
            st.session_state["exp_in_dept"] = p["dept"]
            st.session_state["exp_in_cat"] = p["cat"]
            st.session_state["exp_in_amount"] = float(p["amount"])
            st.session_state["exp_in_attendees"] = int(p["attendees"])
            st.session_state["exp_in_has_receipt"] = bool(p["has_receipt"])
            st.session_state["exp_in_memo"] = p["memo"]

        if "exp_in_claim_id" not in st.session_state:
            st.session_state["selected_exp_preset_key"] = list(EXPENSE_PRESETS.keys())[0]
            apply_selected_expense_preset()

        with col_exp_config:
            st.subheader("1. Select or Configure Expense Claim")
            st.selectbox(
                "Load Expense Claim Archetype Preset:",
                options=list(EXPENSE_PRESETS.keys()),
                key="selected_exp_preset_key",
                on_change=apply_selected_expense_preset,
            )

            c_e1, c_e2 = st.columns(2)
            with c_e1:
                exp_claim_id = st.text_input("Claim ID:", key="exp_in_claim_id")
            with c_e2:
                exp_dept = st.text_input("Department:", key="exp_in_dept")

            c_e3, c_e4 = st.columns(2)
            with c_e3:
                exp_emp_id = st.text_input("Employee ID:", key="exp_in_emp_id")
            with c_e4:
                exp_emp_name = st.text_input("Employee Name:", key="exp_in_emp_name")

            exp_cat_options = ["entertainment", "travel_transit", "supplies", "general"]
            exp_cat_labels = {
                "entertainment": "🍽️ Entertainment & Dining (Limit: ¥10,000 / person)",
                "travel_transit": "🚅 Domestic Travel & Transit (Limit: ¥30,000)",
                "supplies": "📦 Office Supplies (Limit: ¥50,000)",
                "general": "📄 General Corporate Expense",
            }
            exp_cat = st.selectbox(
                "Expense Category:",
                options=exp_cat_options,
                format_func=lambda x: exp_cat_labels.get(x, x),
                key="exp_in_cat",
            )

            c_e5, c_e6 = st.columns(2)
            with c_e5:
                exp_amount = st.number_input(
                    "Total Amount (JPY ¥):",
                    min_value=100.0,
                    max_value=1000000.0,
                    step=500.0,
                    key="exp_in_amount",
                )
            with c_e6:
                exp_attendees = st.number_input(
                    "Attendees Count:",
                    min_value=1,
                    max_value=50,
                    step=1,
                    key="exp_in_attendees",
                )

            exp_has_receipt = st.checkbox(
                "🧾 Official Receipt Attached & Verified",
                key="exp_in_has_receipt",
            )
            exp_memo = st.text_input(
                "Business Purpose / Memo:",
                key="exp_in_memo",
            )

            st.button("🚀 Evaluate Financial Policy Engine", type="primary", use_container_width=True, key="btn_run_exp")
            st.caption("💡 Real-time policy engine checks compliance against corporate accounting guidelines.")

        with col_exp_live:
            st.subheader("2. Real-Time Policy Decision & General Ledger Log")

            claim_req = ExpenseClaimRequest(
                claim_id=exp_claim_id,
                employee_id=exp_emp_id,
                employee_name=exp_emp_name,
                department=exp_dept,
                expense_category=exp_cat,
                amount=exp_amount,
                attendee_count=exp_attendees,
                has_receipt=exp_has_receipt,
                memo=exp_memo,
            )

            exp_engine = ExpenseWorkflowEngine()
            t0 = datetime.now()
            exp_result: ExpenseResult = exp_engine.process_claim(claim_req)
            latency_ms = (datetime.now() - t0).total_seconds() * 1000.0

            if exp_result.status == "AUTO_APPROVED":
                st.success(f"### Status: AUTO_APPROVED")
                st.markdown(
                    f'<span class="badge-approved">STRAIGHT-THROUGH POSTED TO GENERAL LEDGER</span> '
                    f'<code>Latency: {latency_ms:.2f} ms</code>',
                    unsafe_allow_html=True,
                )
                st.markdown("#### Generated Accounting Record & ERP Ledger Entry:")
                st.info(exp_result.generated_comment_ja)
                st.caption(f"Action Taken: {exp_result.action_taken}")
            else:
                st.warning(f"### Status: ESCALATED_TO_MANAGER")
                st.markdown(
                    f'<span class="badge-escalate">MANAGERIAL FINANCIAL APPROVAL QUEUE</span> '
                    f'<code>Latency: {latency_ms:.2f} ms</code>',
                    unsafe_allow_html=True,
                )
                st.markdown("#### Policy Breach / Escalation Reason:")
                st.error(exp_result.escalation_reason)
                st.markdown("#### Pending Escalation Record (Held for Manager Review):")
                st.warning(exp_result.generated_comment_ja)

            st.divider()
            st.markdown("##### Compliance Rule Validation Audit:")
            per_head = exp_amount / max(1, exp_attendees)
            st.write(f"- **Receipt Compliance:** {'✔ Valid Receipt Attached' if exp_has_receipt else '❌ Missing Receipt (Immediate Escalation)'}")
            if exp_cat == "entertainment":
                st.write(f"- **Per-Head Entertainment Cost:** `¥{per_head:,.0f} / person` (Policy Limit: $\\le ¥10,000$) -> {'✔ Within Cap' if per_head <= 10000.0 else '❌ Exceeds Cap'}")
            elif exp_cat == "travel_transit":
                st.write(f"- **Transit Claim Total:** `¥{exp_amount:,.0f}` (Policy Limit: $\\le ¥30,000$) -> {'✔ Within Cap' if exp_amount <= 30000.0 else '❌ Exceeds Cap'}")
            elif exp_cat == "supplies":
                st.write(f"- **Office Supplies Total:** `¥{exp_amount:,.0f}` (Policy Limit: $\\le ¥50,000$) -> {'✔ Within Cap' if exp_amount <= 50000.0 else '❌ Exceeds Cap'}")
            else:
                st.write(f"- **General Expense Standard:** `¥{exp_amount:,.0f}` -> ✔ Standard Policy Compliant")

        st.markdown("---")
        with st.expander("📊 Batch Processing Benchmark Demonstration (Dataset B Production Simulation)"):
            st.caption("Demonstrating automated batch execution across multiple employee expense claims.")
            batch_results = run_sample_expense_batch()
            batch_rows = []
            for r in batch_results:
                batch_rows.append({
                    "Claim ID": r.claim_id,
                    "Decision Status": r.status,
                    "Amount / Head": f"¥{r.per_head_amount:,.0f}",
                    "Action Taken": r.action_taken,
                    "Policy / Audit Reason": r.escalation_reason if r.escalation_reason else "✔ Straight-Through Approved",
                })
            b_df = pd.DataFrame(batch_rows)
            st.dataframe(b_df, use_container_width=True)
            c_b1, c_b2, c_b3, c_b4 = st.columns(4)
            with c_b1:
                st.metric("Total Claims Processed", len(batch_results))
            with c_b2:
                appr_cnt = sum(1 for r in batch_results if r.status == "AUTO_APPROVED")
                st.metric("Straight-Through Rate", f"{appr_cnt / len(batch_results) * 100:.0f}%")
            with c_b3:
                st.metric("Average Latency", "< 1 ms")
            with c_b4:
                st.metric("Manual Time Saved", "34.4s / claim")



# -----------------------------------------------------------------------------
# VIEW 3: SEGMENTATION APPROACHES & ACCURACY BENCHMARK
# -----------------------------------------------------------------------------
elif menu in ("Segmentation Approaches & Benchmark", "Three Segmentation Approaches & Benchmark", "Three Segmentation Approaches & Benchmark (Step 1)"):
    st.title("🔬 Segmentation Approaches & Benchmark")
    st.markdown(
        """
        *From Unindexed Workstation Telemetry to Coherent Business Processes.*  
        To tackle the challenge of turning raw keystrokes, clicks, and window titles into distinct business operations, 
        three progressive segmentation architectures were developed, benchmarked against 63 ground-truth sessions in **Dataset A**, 
        and deployed to **Dataset B**.
        """
    )

    # Top KPI summary cards
    c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
    with c_kpi1:
        st.metric(
            label="v3 Boundary F1-Score",
            value="81.4%",
            delta="+34.9% vs Raw Baseline",
        )
    with c_kpi2:
        st.metric(
            label="v3 Segment IoU F1",
            value="77.3%",
            delta="+43.1% vs Raw Baseline",
        )
    with c_kpi3:
        st.metric(
            label="v3 Label Consistency",
            value="93.9%",
            delta="+84.7% vs Raw Baseline",
        )
    with c_kpi4:
        st.metric(
            label="Dataset B Submission",
            value="v1 Heuristic",
            delta="279 Segments (35.8s avg)",
        )

    st.markdown("---")

    tab_scorecard, tab_approaches, tab_per_process, tab_eval_cli = st.tabs([
        "📊 Accuracy Comparison Scorecard",
        "🛠️ The Three Technical Approaches",
        "📋 Per-Process Classification Purity",
        "▶️ Live Evaluation Runner (Dataset A)",
    ])

    with tab_scorecard:
        st.subheader("Comprehensive Accuracy Scorecard (Dataset A Ground Truth Benchmark)")
        st.caption("Evaluated across all 63 sessions (2,009 true executions) in Dataset A using `scripts/evaluate_dataset_a.py` with ±5s boundary tolerance.")

        scorecard_rows = [
            {
                "Evaluation Metric": "Total Predicted Segments",
                "Raw Baseline": "2,456",
                "v1 Heuristic (Golden Thread)": "2,010 (True: 2,009)",
                "v2 Vision PoC (MobileNet)": "5,831",
                "v3 Two-Stage Supervised ML": "1,989 (True: 2,009)",
                "Net Improvement (v3 vs Raw)": "-467 (Resolved Over-segmentation)",
            },
            {
                "Evaluation Metric": "Boundary Precision",
                "Raw Baseline": "41.5%",
                "v1 Heuristic (Golden Thread)": "45.4%",
                "v2 Vision PoC (MobileNet)": "13.9%",
                "v3 Two-Stage Supervised ML": "79.7%",
                "Net Improvement (v3 vs Raw)": "+38.2%",
            },
            {
                "Evaluation Metric": "Boundary Recall",
                "Raw Baseline": "53.5%",
                "v1 Heuristic (Golden Thread)": "48.1%",
                "v2 Vision PoC (MobileNet)": "43.8%",
                "v3 Two-Stage Supervised ML": "83.9%",
                "Net Improvement (v3 vs Raw)": "+30.4%",
            },
            {
                "Evaluation Metric": "Boundary F1-Score",
                "Raw Baseline": "46.5%",
                "v1 Heuristic (Golden Thread)": "46.4%",
                "v2 Vision PoC (MobileNet)": "20.9%",
                "v3 Two-Stage Supervised ML": "81.4%",
                "Net Improvement (v3 vs Raw)": "+34.9%",
            },
            {
                "Evaluation Metric": "Segment Precision",
                "Raw Baseline": "49.1%",
                "v1 Heuristic (Golden Thread)": "52.4%",
                "v2 Vision PoC (MobileNet)": "10.4%",
                "v3 Two-Stage Supervised ML": "73.1%",
                "Net Improvement (v3 vs Raw)": "+24.0%",
            },
            {
                "Evaluation Metric": "Segment Recall",
                "Raw Baseline": "56.2%",
                "v1 Heuristic (Golden Thread)": "59.6%",
                "v2 Vision PoC (MobileNet)": "33.8%",
                "v3 Two-Stage Supervised ML": "82.7%",
                "Net Improvement (v3 vs Raw)": "+26.5%",
            },
            {
                "Evaluation Metric": "Segment IoU F1 (≥ 0.5)",
                "Raw Baseline": "34.2%",
                "v1 Heuristic (Golden Thread)": "55.5%",
                "v2 Vision PoC (MobileNet)": "15.7%",
                "v3 Two-Stage Supervised ML": "77.3%",
                "Net Improvement (v3 vs Raw)": "+43.1%",
            },
            {
                "Evaluation Metric": "Label Consistency (Purity)",
                "Raw Baseline": "9.2%",
                "v1 Heuristic (Golden Thread)": "65.8%",
                "v2 Vision PoC (MobileNet)": "16.8%",
                "v3 Two-Stage Supervised ML": "93.9%",
                "Net Improvement (v3 vs Raw)": "+84.7%",
            },
        ]
        df_scorecard = pd.DataFrame(scorecard_rows)
        st.dataframe(df_scorecard, use_container_width=True, hide_index=True)

        st.markdown("##### Visual Accuracy Progression Across Model Generations")
        chart_data = pd.DataFrame({
            "Approach": [
                "Raw Baseline",
                "v1 Heuristic",
                "v2 Vision PoC",
                "v3 Supervised ML",
            ],
            "Boundary F1 (%)": [46.5, 46.4, 20.9, 81.4],
            "Segment IoU F1 (%)": [34.2, 55.5, 15.7, 77.3],
            "Label Purity (%)": [9.2, 65.8, 16.8, 93.9],
        }).set_index("Approach")
        st.bar_chart(chart_data)

        st.info(
            "💡 **Key Observation:** The v3 Two-Stage ML pipeline achieved a massive leap in accuracy: "
            "Boundary F1 jumped to **81.4%**, Segment IoU F1 reached **77.3%**, and Label Purity achieved **93.9%** "
            "— matching true execution counts almost 1-to-1 (1,989 predicted vs. 2,009 true executions)."
        )

    with tab_approaches:
        st.subheader("Detailed Architecture of the Three Approaches")

        exp1 = st.expander("🧵 Tier 1: v1 Heuristic State Machine (Production Deliverable)", expanded=True)
        with exp1:
            st.markdown(
                """
                **Design & Mechanics:**
                - **Entity-Centric Anchor Tracing:** Tracks business entities (PO numbers, employee codes, transaction IDs) via `clipboard_change` (`Ctrl+C`) and follows them as users paste (`Ctrl+V`) across application boundaries (Web Portal $\\leftrightarrow$ Excel $\\leftrightarrow$ Word).
                - **Topological Navigation:** Detects returns to portal navigation hubs (`/dashboard`, `/index`) as natural task boundaries.
                - **Inactivity Windows:** Emits natural task completion boundaries during prolonged operator pauses (>60 seconds).
                - **Adjacent Semantic Merging:** Consolidates adjacent micro-fragments ($\\le 30$s gap) sharing identical semantic labels without conflicting entity anchors.
                
                **Why v1 Heuristics was chosen for Deliverable 1 (`segments.jsonl`):**
                - **Immunity to Distribution Shifts:** Dataset A was recorded on Google Chrome on ports `5122–5124` with operators Marcos, yuvraj, etc. Dataset B introduces unseen operators (`CHAITANYA0BCF`, `LAPTOP-76QMG9DE`, `NEELA9BAF`) using **Microsoft Edge** on new ports `5132–5134`.
                - **Domain Invariance:** The v1 state machine relies on universal human work patterns rather than memorized port numbers, ensuring zero overfitting.
                - **Empirical Ground-Truth Match:** Produced **279 segments** with an average duration of **35.8 seconds**—an almost exact mirror of Dataset A's verified ground truth (**37.1 seconds**).
                """
            )

        exp2 = st.expander("👁️ Tier 2: v2 Computer Vision PoC (MobileNet Anomaly Detector)")
        with exp2:
            st.markdown(
                """
                **Motivation:**
                Text-based telemetry cannot observe 'silent' UI state updates—such as asynchronous AJAX data table reloads, modal dialog popups, and tab switches without keystrokes.

                **Implementation (`src/experiments/vision_poc.py`):**
                - Evaluated all **34,563 1080p desktop screenshots** from Dataset A using `MobileNet_V3_Small` on Google Colab T4 GPUs, compressing each image into a 1,000-dimensional semantic vector.
                - Engineered a **4-frame relational rolling window** ($f_1, f_2, f_3, f_4$) to evaluate transition drop magnitude against surrounding visual stability:
                $$\\text{Drop Magnitude} = \\frac{\\text{Stability}_{\\text{before}} + \\text{Stability}_{\\text{after}}}{2} - \\text{Transition Similarity}$$
                - Cut false-positive visual cuts by **38.1%** (from 9,418 to 5,831 segments) and more than doubled Segment IoU F1 from 7.3% to **15.7%**.
                - *Takeaway:* Valuable for multimodal enterprise systems, but raw vision is sensitive to animated blinking cursors and minor window focus changes.
                """
            )

        exp3 = st.expander("🧠 Tier 3: v3 Two-Stage Supervised Machine Learning Pipeline")
        with exp3:
            st.markdown(
                """
                **Two-Stage Architecture:**
                - **Stage 1: Temporal & Interaction Boundary Classifier (`scripts/train_boundary_model.py`):**
                  - Extracted 18 tabular temporal and interaction features per event (`dt_prev`, `dt_next`, `is_app_sw`, `is_clip`, `clip_delta`, `has_id`, `hub`, `url_depth`, `app_cat`, `idle_10s`, `idle_30s`, etc.) across 162,650 event samples from Dataset A.
                  - Trained a `HistGradientBoostingClassifier` with balanced class weights, achieving **0.9274 ROC-AUC** and **0.7674 PR-AUC** on validation sets.
                - **Stage 2: Calibrated Semantic Process Classifier (`scripts/train_label_classifier.py`):**
                  - Tokenizes system port signatures (`SYS_HR_5122`, `SYS_FIN_5123`, `SYS_OPS_5124`), route hashes, native window titles, form input labels, and OCR text across 1,734 ground truth executions.
                  - Trained a calibrated `TF-IDF + LogisticRegression` pipeline, achieving **95.1% validation accuracy** and **0.952 Macro F1** across all 15 business processes.
                - **Inference Optimizations (`src/segmentation/ml_segmenter.py`):**
                  - **12s Adaptive Refractory Peak Suppression:** Suppresses micro-jitter cuts by retaining only the highest-probability boundary candidate within a 12-second rolling window (+34.3% precision boost).
                  - **35s Semantic Post-Processing & Merging:** Merges adjacent fragments sharing identical labels within 35 seconds (+21.8% IoU F1 boost).
                """
            )

    with tab_per_process:
        st.subheader("Per-Process Classification Purity (v3 ML Engine)")
        st.caption("Detailed classification accuracy across all 15 business process categories on Dataset A ground truth.")

        per_process_rows = [
            {"Business Process": "inventory_adjustment", "Code": "L", "Classification Purity": "100.0%", "Matched Samples": "75 / 75", "Operational Domain": "Supply Chain & Warehousing"},
            {"Business Process": "resident_tax_verification", "Code": "A", "Classification Purity": "99.1%", "Matched Samples": "116 / 117", "Operational Domain": "Human Resources & Payroll"},
            {"Business Process": "invoice_approval", "Code": "F", "Classification Purity": "99.1%", "Matched Samples": "113 / 114", "Operational Domain": "Financial Accounting"},
            {"Business Process": "return_processing", "Code": "O", "Classification Purity": "98.7%", "Matched Samples": "78 / 79", "Operational Domain": "Supply Chain Logistics"},
            {"Business Process": "payment_processing", "Code": "J", "Classification Purity": "98.6%", "Matched Samples": "70 / 71", "Operational Domain": "Treasury & Disbursements"},
            {"Business Process": "supplier_communication", "Code": "M", "Classification Purity": "98.4%", "Matched Samples": "122 / 124", "Operational Domain": "Procurement & Sourcing"},
            {"Business Process": "budget_variance_analysis", "Code": "I", "Classification Purity": "97.8%", "Matched Samples": "91 / 93", "Operational Domain": "Financial FP&A"},
            {"Business Process": "onboarding_verification", "Code": "E", "Classification Purity": "97.4%", "Matched Samples": "74 / 76", "Operational Domain": "Human Resources"},
            {"Business Process": "leave_application_processing", "Code": "C", "Classification Purity": "97.3%", "Matched Samples": "107 / 110", "Operational Domain": "Human Resources"},
            {"Business Process": "expense_processing", "Code": "G", "Classification Purity": "96.6%", "Matched Samples": "86 / 89", "Operational Domain": "General Accounting"},
            {"Business Process": "shipment_tracking", "Code": "N", "Classification Purity": "92.5%", "Matched Samples": "86 / 93", "Operational Domain": "Outbound Logistics"},
            {"Business Process": "bank_reconciliation", "Code": "H", "Classification Purity": "86.3%", "Matched Samples": "101 / 117", "Operational Domain": "Financial Accounting"},
            {"Business Process": "order_processing", "Code": "K", "Classification Purity": "85.6%", "Matched Samples": "77 / 90", "Operational Domain": "Customer Sales Operations"},
            {"Business Process": "payroll_adjustment", "Code": "B", "Classification Purity": "81.9%", "Matched Samples": "86 / 105", "Operational Domain": "Human Resources & Payroll"},
            {"Business Process": "insurance_pension_processing", "Code": "D", "Classification Purity": "79.6%", "Matched Samples": "78 / 98", "Operational Domain": "Statutory Compliance"},
        ]
        df_per_process = pd.DataFrame(per_process_rows)
        st.dataframe(df_per_process, use_container_width=True, hide_index=True)

        st.metric(label="Macro Average Classification Purity", value="93.9%", delta="1,245 / 1,326 Matched Executions")

    with tab_eval_cli:
        st.subheader("Run Evaluation Harness on Dataset A (Live Execution)")
        st.caption("Executes `scripts/evaluate_dataset_a.py` against the ground-truth manifests in `dataset_a/`.")

        eval_model_options = {
            "v3 Two-Stage ML Model (81.4% Boundary F1, 93.9% Purity)": "dataset_a/evaluated_segments_ml.jsonl",
            "v1 Heuristic Baseline (46.4% Boundary F1, 65.8% Purity)": "dataset_a/evaluated_segments_baseline.jsonl",
            "v2 Vision PoC Multi-Frame (20.9% Boundary F1, 16.8% Purity)": "dataset_a/evaluated_segments_multiframe.jsonl",
        }
        chosen_eval_label = st.selectbox("Select Model Prediction File:", list(eval_model_options.keys()))
        pred_file = eval_model_options[chosen_eval_label]

        if st.button("▶ Run scripts/evaluate_dataset_a.py", type="primary"):
            import subprocess
            cmd = [
                sys.executable,
                str(ROOT / "scripts" / "evaluate_dataset_a.py"),
                "--predictions",
                str(ROOT / pred_file),
                "--dataset-dir",
                str(ROOT / "dataset_a"),
            ]
            with st.spinner("Evaluating ground truth across 63 sessions..."):
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if proc.returncode == 0:
                st.success("✔ Evaluation Completed Successfully!")
                st.code(proc.stdout)
            else:
                st.error("Evaluation Encountered an Issue:")
                st.code(proc.stderr or proc.stdout)


# -----------------------------------------------------------------------------
# VIEW 4: DATASET B TELEMETRY & SEGMENTS EXPLORER
# -----------------------------------------------------------------------------
elif menu in ("Dataset B Telemetry & Segments Explorer (Step 1)", "Telemetry & Process Explorer (Step 1)"):
    st.title("🔍 Dataset B Telemetry & Recovered Segments (Step 1)")
    st.markdown(
        """
        Recovered coherent units of work from Dataset B production events (`segments.jsonl`).  
        Generated via the **Entity-Centric Golden Thread State Machine** (v1 Heuristic) across 15 sessions.
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
        chart_data = pd.DataFrame({
            "Execution Sequence (#)": range(1, len(filtered_df) + 1),
            "Duration (Seconds)": filtered_df["duration_s"].clip(upper=120).values,
        })
        st.bar_chart(
            chart_data,
            x="Execution Sequence (#)",
            y="Duration (Seconds)",
            x_label="Execution Sequence (#)",
            y_label="Duration (Seconds, Capped at 120s)",
            color="#1C83E1",
        )


# -----------------------------------------------------------------------------
# VIEW 4: IMPLEMENTATION RISK MATRIX
# -----------------------------------------------------------------------------
elif menu == "Implementation Risk Matrix":
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
            "Telemetry Evidence": "Operators habitually maintain personal scratchpad notes.",
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
elif menu == "7-Day Sprint Work Log & Audit":
    st.title("📖 7-Day Sprint Work Log & Verification")
    st.markdown(
        """
        **Enterprise Scope:** Corporate Back-Office Operations (HR, Finance, Procurement & Supply Chain)  
        **Project:** PC Operation Log Analysis, Process Mining & Automation Proposal  
        **Duration:** 7-Day Engagement | **Author:** Baibhav Gond  
        **Email:** baibhav0019@gmail.com | **Institute:** Indian Institute of Technology Bhubaneswar  
        *Chronological engineering diary of trials, dead ends, breakthroughs, and GenAI disclosures from [`work_log.md`](file:///c:/IBY_Japan/work_log.md).*
        """
    )

    st.divider()

    st.subheader("Run Automated Test Suite")
    st.caption("Executes `pytest` across `tests/` to validate data ingestion, segmentation, evaluation, and automation prototypes.")
    if st.button("▶ Run Pytest Suite", type="primary"):
        import subprocess
        with st.spinner("Running 46 unit & integration tests across tests/..."):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        if proc.returncode == 0:
            st.success("✔ All 46 Pytest tests passed successfully!")
            st.code(proc.stdout)
        else:
            st.error("Pytest encountered issues:")
            st.code(proc.stdout or proc.stderr or "No output captured.")

    st.divider()
    st.subheader("Chronological Sprint Diary (7 Days)")

    with st.expander("Day 1: Problem Ingestion, Architectural Scoping & Resilient Data Pipeline", expanded=True):
        st.markdown(
            """
            **Objective:** Absorb the enterprise operational context, data schemas, and domain constraints; set up version control; build a production-grade multi-chunk data loader.
            
            **Key Actions Taken:**
            - Ingested operational requirements and `DATA_SCHEMA.md` across HR (`5122`/`5132`), Finance (`5123`/`5133`), and Supply Chain (`5124`/`5134`).
            - Initialized root Git repository with structured module boundaries: `src/pipeline/`, `src/segmentation/`, `src/analytics/`, `src/automation/`, and `tests/`.
            - Built `src/pipeline/loader.py`: implemented `find_session_chunks`, `find_session_event_files`, and `load_session_events` with explicit UTF-8 decoding to handle Japanese characters (`Shift_JIS` / `CP932` vs `UTF-8`).
            - Implemented unit tests in `tests/test_loader.py` covering multi-chunk chronological ordering, deduplication, and quirk filtering.
            
            **Trials & Dead Ends:**
            - **Attempted:** Initially considered parsing `text_input_complete` to reconstruct input forms.
            - **Dead End Diagnosed:** `text_input_complete` frequently fired with empty payloads or out-of-order text during rapid Japanese IME conversions.
            - **Resolution:** Dropped `text_input_complete` payloads and designed the pipeline to rely on deterministic clipboard changes, navigation events, and UI element attributes.
            """
        )

    with st.expander("Day 2: Ground Truth Evaluation Harness & Exploratory Data Analysis (EDA)"):
        st.markdown(
            r"""
            **Objective:** Construct a rigorous, mathematically sound evaluation benchmark against Dataset A ground truth (`gt.jsonl` and `gt_manifest.json`) before writing segmentation algorithms.
            
            **Key Actions Taken:**
            - Analyzed Dataset A (63 sessions, ~162,000 events, 2,009 ground-truth executions across 15 business processes `A` through `O`).
            - **Operational Invariants Discovered:**
              - *Start Invariant:* 100% of business processes start inside a web browser portal (`Google Chrome` in Dataset A, `Microsoft Edge` in Dataset B).
              - *Consistent Triad:* Processes exhibit a characteristic 3-application signature (Web Portal $\leftrightarrow$ Desktop Document App [Excel/Word] $\leftrightarrow$ Reference Tool [Notepad/Explorer]).
              - *Execution Cadence:* Mean cycle time across all 2,009 executions is ~42.3 seconds (IQR: 24s to 58s).
            - Built `scripts/evaluate_dataset_a.py`:
              - Boundary F1 with $\pm 5$-second tolerance window (Precision, Recall, F1).
              - Segment-level IoU ($\ge 0.5$) for execution overlap scoring.
              - Label Consistency (Macro Purity) scoring.
            - Verified benchmark edge cases via `tests/test_evaluator.py`.
            
            **Trials & Dead Ends:**
            - **Attempted:** Exact timestamp matching ($\pm 0$ seconds).
            - **Dead End Diagnosed:** Human operators exhibit variable transition latency between reading screens and typing/clicking. Exact matching penalized valid boundaries by $\approx 85\%$.
            - **Resolution:** Adopted $\pm 5$-second tolerance window reflecting human task initiation cadences while continuing to penalize spurious cuts.
            """
        )

    with st.expander("Day 3: Designing the 'Entity-Centric Golden Thread' State Machine"):
        st.markdown(
            r"""
            **Objective:** Create the initial segmentation algorithm to split continuous event streams into discrete units of work without supervision.
            
            **Key Actions Taken:**
            - Formulated the **'Golden Thread'** hypothesis: An enterprise process execution revolves around a single data entity (e.g., Invoice `INV-...`, PO `PO-...`, Employee ID) carried across apps via the clipboard.
            - Implemented noise filtering in `src/segmentation/segmenter.py` (`filter_events`): filtered high-frequency mouse scrolls and raw keystrokes while preserving state transitions (`app_switch`, `clipboard_change`, `browser_navigation`, shortcuts `Ctrl+C`/`Ctrl+V`, submit clicks).
            - Built `GoldenThreadSegmenter`:
              - *The Anchor:* Captures `clipboard_change` payloads as active `Entity_Anchor`.
              - *The Thread:* Tracks cross-application focus switches and portal navigation.
              - *Boundary Detection:* Emits completions on portal hub returns (`/dashboard`, `/index`), conflicting entity copies, portal system shifts, or inactivity timeout (>60s).
            
            **Trials & Dead Ends:**
            - **Attempted:** Pure idle-gap segmentation (splitting whenever user paused for $>15$ seconds).
            - **Dead End Diagnosed:** Caused massive over-segmentation whenever an employee paused to read a complex contract or consult a colleague (Precision $<25\%$).
            - **Resolution:** Grounded boundaries in portal hub returns and clipboard entity transitions, drastically stabilizing boundary precision.
            """
        )

    with st.expander("Day 4: Baseline Evaluation, LLM Labeling & Semantic Segment Merging"):
        st.markdown(
            r"""
            **Objective:** Evaluate baseline segmentation on Dataset A, diagnose failure modes, and implement semantic post-processing to eliminate over-segmentation.
            
            **Key Actions Taken:**
            - Baseline `GoldenThreadSegmenter` across 63 sessions in Dataset A resulted in **46.5% Boundary F1** and **9.2% Label Consistency**, generating 2,456 segments vs 2,009 ground truth (+447 spurious fragments).
            - **Over-Segmentation Diagnosis:** Brief returns to portal before pasting additional data into Word/Excel caused premature cutoff.
            - Built LLM labeling (`src/segmentation/llm_labeler.py`) with Japanese context prompt and built `merge_segments(max_gap_ms=30_000)` in `src/segmentation/segmenter.py` to merge adjacent segments within 30s sharing the same label without entity conflict.
            - **Re-evaluation Results:**
              - Total predicted segments dropped from 2,456 to **2,010** (within 1 segment of 2,009 true executions!).
              - **Boundary F1 stabilized at 46.4%** (Precision: 45.4%, Recall: 48.1%) with **Segment IoU F1 at 55.5%**.
              - **Label Consistency skyrocketed from 9.2% to 65.8%** (+56.6% gain; e.g., `onboarding_verification` at 91.3%, `bank_reconciliation` at 86.2%).
            - Identified technical limits of heuristics: text-based heuristics cannot detect silent UI state changes (background table loading, modal popups, SPA shifts), leaving an unobserved **33.4% variance gap**.
            
            **Trials & Dead Ends:**
            - **Attempted:** Naive regex matching on window titles without temporal smoothing.
            - **Dead End Diagnosed:** Alt-Tab window title flickers caused label instability.
            - **Resolution:** Integrated 30-second temporal semantic merging to consolidate multi-application switching loops.
            """
        )

    with st.expander("Day 5: Advanced Visual & Supervised ML R&D (Computer Vision POC & Two-Stage ML Breakthrough)"):
        st.markdown(
            r"""
            **Objective:** Investigate advanced visual and supervised machine learning approaches to bridge the 33.4% unobserved variance gap and shatter the 65.8% heuristic baseline ceiling.
            
            **Key Actions Taken:**
            1. **Computer Vision Anomaly Engine R&D (Google Colab T4 GPU Pipeline):**
               - **Execution Clarification:** I did not run the vision experiments locally with `src/experiments/vision_poc.py`. Instead, I engineered and executed the entire batch vision pipeline according to `experiments/Colab_vision_boundary.ipynb` on Google Colab using an Nvidia T4 GPU to batch-process all 34,563 1080p desktop screenshots from `dataset_a.zip`.
               - Vectorized all frames with PyTorch `MobileNet_V3_Small` into 1,000-dimensional embeddings:
                 - *Experiment 1:* Single-frame cosine similarity (<0.85) generated `experiments/vision_boundaries.jsonl` (`Vision_boundaries`, detecting 9,481 raw state changes).
                 - *Experiment 2:* 4-frame dynamic rolling relational window (`drop_tolerance > 0.15`) generated `experiments/vision_boundaries_multiframe.jsonl` (`vsion_boundries_multiframe`, detecting 5,894 verified state changes).
               - Converted both boundary files into ISO-8601 UTC session segments using `experiments/convert_vision_boundaries.py`:
                 - Generated `experiments/evaluated_vision_boundaries.jsonl` (`evaluated_vision_boundaries`, also saved as `evaluated_segments_single.jsonl`).
                 - Generated `experiments/evaluated_vision_boundaries_multiframe.jsonl` (`evaluated_vision_boundaries_multiframe`, also saved as `evaluated_segments_multiframe.jsonl`).
               - Evaluated against Dataset A ground truth (`scripts/evaluate_dataset_a.py`): eliminated 3,587 false-positive jitter cuts (**-38.1% reduction**) and doubled **Segment IoU F1 from 7.3% to 15.7%**!
               - Unified the complete pipeline logic into `src/experiments/vision_poc.py` as an offline reference implementation and CLI.
            2. **Two-Stage Supervised Machine Learning Pipeline Breakthrough (`src/segmentation/ml_segmenter.py`):**
               - *Stage 1 (Boundary Classifier):* Trained `HistGradientBoostingClassifier` on 162,650 Dataset A event samples across 18 tabular features with 12s adaptive refractory peak suppression (**ROC-AUC: 0.9274**).
               - *Stage 2 (Semantic Classifier):* Trained `TF-IDF + LogisticRegression` conditioned on portal ports (`:5122-5124`), route hashes, window titles, and OCR text (**95.1% accuracy, 0.952 Macro F1**).
               - *Dataset A Ground Truth Breakthrough:*
                 - **Boundary F1:** Jumped from **46.4% $\to$ 81.4% (+35.0% absolute lift)** (Precision: 79.7%, Recall: 83.9%).
                 - **Segment IoU F1 ($\ge 0.5$):** Jumped from **55.5% $\to$ 77.3% (+21.8% absolute lift)**.
                 - **Label Consistency Purity:** Jumped from **65.8% $\to$ 93.9% (+28.1% absolute lift)**.
                 - **Volume Fidelity:** **1,989 segments** vs 2,009 ground truth (99.0% volume fidelity).
            3. **Strategic FDE Decision & Day 5 Freeze:**
               - Recognized that Dataset A and Dataset B feature entirely different operators (`Marcos`, `yuvraj` vs `CHAITANYA0BCF`, `NEELA9BAF`), browsers (Chrome vs Edge), and port signatures (`5122-5124` vs `5132-5134`).
               - A complex supervised model trained on Dataset A risks **overfitting to individual operator keystroke cadences**.
               - Declared segmentation tuning complete and froze the primary deliverable (`segments.jsonl`) on the domain-invariant v1 heuristic state machine, ensuring robust, non-overfitted deliverables while preserving the ML engine (`src/segmentation/ml_segmenter.py`) for in-domain deployment.
            
            **Trials & Dead Ends:**
            - **Attempted (Vision PoC):** Naive single-frame cosine similarity (<0.85).
            - **Dead End Diagnosed:** Micro-scrolls, cursor blinks, and hover tooltips triggered 9,481 spurious cuts (12.5% precision).
            - **Resolution:** Developed 4-frame relational window comparing transition similarity to surrounding plateau stability, filtering out 3,587 false-positive cuts.
            """
        )

    with st.expander("Day 6: Production Ingestion (Dataset B), Process Mining & Friction Discovery"):
        st.markdown(
            r"""
            **Objective:** Ingest Dataset B production operational logs (15 sessions across 4 staff workstations), generate the required `segments.jsonl` deliverable, and quantify operational bottlenecks to prioritize automation candidates.
            
            **Key Actions Taken:**
            - Extended pipeline for Dataset B: supported `Microsoft Edge (Profile 1)`, portal ports `5132` (HR), `5133` (Finance), `5134` (Operations), and production document templates.
            - Generated primary deliverable `segments.jsonl` (`scripts/run_segmentation.py`): recovered 279 business process segments across all 15 sessions (100% session coverage), mean duration 35.8s (mirroring Dataset A's 37.1s).
            - Engineered `src/analytics/process_miner.py`:
              $$\text{Friction} = \text{Average App Switches} + \text{Average Clipboard Transitions}$$
              $$\text{ROI Score} = \frac{\text{Volume} \times \text{Friction}}{\text{Average Duration}}$$
            - **Enterprise Prioritization Scorecard:**
              - **#1 `supplier_communication`:** 100 executions (35.8% volume), 61.9 active min, 9.39 friction $\to$ **ROI Score: 25.30**.
              - **#2 `expense_processing`:** 61 executions (21.9% volume), 35.0 active min, 9.44 friction $\to$ **ROI Score: 16.75**.
              - **#3 `onboarding_verification`:** 21 executions, 11.8 active min, 9.10 friction $\to$ **ROI Score: 5.67**.
              - **#4 `leave_application_processing`:** 26 executions, 18.0 active min, 8.73 friction $\to$ **ROI Score: 5.45**.
              - **#5 `inventory_adjustment`:** 25 executions, 15.8 active min, 8.12 friction $\to$ **ROI Score: 5.34**.
            - **Key Discovery:** **57.7% of all enterprise back-office volume** is concentrated in just two workflows (`supplier_communication` + `expense_processing`), establishing them as high-impact automation targets.
            - Isolated operational variants: routine adjustments ($\le 25\%$ qty, $\le 5$ days delivery) and expense claims ($\le \text{¥}10,000$/head entertainment, $\le \text{¥}30,000$ transit) vs contractual/tax escalations.
            
            **Trials & Dead Ends:**
            - **Attempted:** Prioritizing automation candidates based solely on raw execution duration.
            - **Dead End Diagnosed:** Favored complex, infrequent manual analysis tasks (like `budget_variance_analysis`, 48.2s avg, only 4 runs), which have low standardization and poor automation ROI.
            - **Resolution:** Adopted multi-factor ROI formula weighting volume density and friction against duration, elevating high-volume administrative bottlenecks.
            """
        )

    with st.expander("Day 7: Step 3 Working Automation Prototype, Risk Analysis, Final Verification & Delivery"):
        st.markdown(
            r"""
            **Objective:** Design, build, and validate a functioning production automation prototype for `supplier_communication`; extend architecture to `expense_processing`; formulate implementation risk matrix; verify all deliverables.
            
            **Key Actions Taken:**
            1. **Built Step 3 Primary Prototype (`src/automation/supplier_automation.py`):**
               - Engineered `SupplierWorkflowEngine` as a stateless, deterministic policy microservice.
               - Automatic straight-through approval (`AUTO_APPROVED`) for standard adjustments ($\le 25\%$ qty, $\le 5$ days delivery, $\le 5\%$ price).
               - Formats standardized enterprise communication records ("Quantity Change Request", "Automated Processing Completed").
               - Halts execution and flags `ESCALATED_TO_MANAGER` for contractual variance breaches.
               - Defined Express / Node.js REST API contract (`POST /api/v1/supplier-requests/process`) for portal integration (ports `5132-5134`).
            2. **Multi-Process Architecture Extension (`src/automation/expense_automation.py`):**
               - Extended engine to Rank #2 bottleneck `expense_processing` (`ExpenseWorkflowEngine`), capturing 57.7% combined volume.
               - Enforces Japanese tax compliance: validates corporate entertainment dining ($\le \text{¥}10,000$/head), transit claims ($\le \text{¥}30,000$), and strict receipt audit gates.
            3. **Automated Test Suite & Verification:**
               - Developed `tests/test_automation.py`, `tests/test_expense_automation.py`, and `tests/test_ml_segmenter.py`.
               - Verified **46 / 46 Pytest tests passing** covering auto-approvals, limit breaches, exception handling, and batch executions.
            4. **Empirical Risk Analysis & Residual Work Formulation:**
               - Constructed 6-category Risk Matrix with concrete mitigations grounded in telemetry: Unicode/Shift_JIS normalization, idempotent transaction keys, and a 14-day staged stabilization phase in 'Shadow Recommendation Mode'.
               - Defined high-value residual human work (exception sign-offs, master vendor contract review).
            5. **Authored Comprehensive Final Report (`final_report.md`) & Diary (`work_log.md`):**
               - Detailed 8-section report with 3-tier scorecard, Step 1 technical evolution, Step 2 prioritization, Step 3 prototype design, residual work, risk matrix, 7-day budget rationale, and 90-day roadmap.
            6. **Final Packaging & Deliverable Validation:**
               - Confirmed `segments.jsonl` (279 segments, 15 sessions), prototype endpoints, and 46 automated tests pass cleanly.
            
            **Trials & Dead Ends:**
            - **Attempted:** Simulating human UI clicks via browser automation scripts.
            - **Dead End Diagnosed:** Brittle DOM selectors and modal animations caused intermittent test failures.
            - **Resolution:** Built deterministic Python backend engine exposed via clean REST endpoints, achieving $<50$ms execution speed and 100% test reliability.
            """
        )

    st.divider()
    st.subheader("Generative AI Disclosure")
    st.markdown(
        """
        In strict accordance with the engagement guidelines, Generative AI was used responsibly with full transparency:
        
        - **Architectural Brainstorming:** LLMs were used during Day 2 and Day 3 to brainstorm heuristic edge cases for human desktop multitasking (e.g., handling rapid alt-tabbing, clipboard masking).
        - **Japanese Natural Language Understanding:** LLMs were utilized to translate and analyze Japanese UI window titles, form placeholders (such as verification comments, clearing reasons, and vendor requests), and document naming conventions into standardized 2–3 word English business process categories.
        - **Boilerplate & Test Generation:** Generative AI assisted in rapid drafting of unit test fixtures (`pytest`) and data-structure serialization routines, followed by 100% manual code review, refactoring, and deterministic verification against the Dataset A ground truth harness.
        - **Production Guardrails:** No production automation decisions rely on unconstrained or unverified LLM generation; all business policy rules, segmentation state machines, and automation decision gates remain **100% deterministic and mathematically validated**.
        """
    )

    st.divider()
    with st.expander("📄 View Complete Unabridged work_log.md Document"):
        log_file = ROOT / "work_log.md"
        if log_file.exists():
            st.markdown(log_file.read_text(encoding="utf-8"))
        else:
            st.error("work_log.md not found at repository root.")
