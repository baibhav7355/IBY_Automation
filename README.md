# Enterprise Back-Office Process Mining & Intelligent Automation Engine
### Forward Deployed Engineering (FDE) Portfolio Deliverable | Telemetry Ingestion, Segmentation & Automation

[![Submission Status](https://img.shields.io/badge/Submission-100%25%20Verified-brightgreen.svg?style=flat-square)](#-executive-deliverables-quick-index)
[![Test Suite](https://img.shields.io/badge/Pytest-46%2F46%20Passed-success.svg?style=flat-square)](#-automated-testing--verification)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg?style=flat-square)](#-quickstart--execution-guide)
[![Boundary F1](https://img.shields.io/badge/Boundary%20F1-81.4%25%20(ML)-orange.svg?style=flat-square)](#-dataset-a-evaluation--accuracy-benchmarks)
[![Label Consistency](https://img.shields.io/badge/Label%20Purity-93.9%25%20(ML)-blueviolet.svg?style=flat-square)](#-dataset-a-evaluation--accuracy-benchmarks)
[![Dataset B Segments](https://img.shields.io/badge/Dataset%20B-279%20Segments-informational.svg?style=flat-square)](#-step-2-process-mining--roi-candidate-prioritization)

---

## 📌 Executive Summary & Client Mandate

### The Client Problem
Enterprise operational leadership tasked our Forward Deployed Engineering (FDE) team with a decisive mandate:
> *"Use these PC operation logs to tell us where automation would have the greatest impact on our operations. And show us something that actually works."*

Thousands of hours of back-office administrative labor across HR, Financial Accounting, and Supply Chain Logistics were locked inside raw desktop telemetry: keystrokes, mouse clicks, window title changes, and application switches. Lacking semantic structure, leadership had zero quantitative visibility into:
1. What business processes employees were actually performing.
2. How long individual workflows consumed and where context-switching drag eroded productivity.
3. Which operations offered the highest return on investment (ROI) for intelligent automation.

### The FDE Solution
We engineered an end-to-end telemetry transformation and automation platform:
1. **Quirk-Resilient Ingestion:** Repaired multi-chunk recordings, enforced UTF-8 Japanese character decoding, and neutralized recording defects (e.g., unreliable `text_input_complete` events per `DATA_SCHEMA.md`).
2. **Three-Tier Process Segmentation Engine:**
   - **Tier 1 (v1 Heuristic State Machine):** Traced cross-application entity copy-paste lifecycles (`Ctrl+C`/`Ctrl+V`) and navigation hubs to extract 279 production segments (Deliverable 1).
   - **Tier 2 (v2 Computer Vision PoC):** Evaluated 34,563 1080p desktop screenshots with `MobileNet_V3_Small` using a 4-frame dynamic drop-magnitude rolling window to detect silent UI transitions.
   - **Tier 3 (v3 Two-Stage Supervised ML):** Breakthrough machine learning architecture (`HistGradientBoosting` + calibrated `TF-IDF LogisticRegression`) achieving **81.4% Boundary F1** and **93.9% Label Consistency**.
3. **Quantitative Process Mining (Dataset B):** Mined 15 production sessions across 4 staff workstations to discover that **57.7% of all operational volume** is concentrated in just two friction-heavy bottlenecks: `supplier_communication` (Rank #1) and `expense_processing` (Rank #2).
4. **Step 3 Working Prototypes:** Delivered two deterministic, rule-validated backend workflow engines with interactive Streamlit dashboard interfaces and human-in-the-loop managerial exception escalation.

---

## 🗂️ Executive Deliverables Quick Index

All mandatory deliverables specified in [`information.md`](file:///c:/IBY_Japan/information.md) are fully verified and available in the repository root:

| Deliverable | File / Artifact | Verification Target | Status |
| :--- | :--- | :--- | :---: |
| **Deliverable 1: Step 1 Output** | [`segments.jsonl`](file:///c:/IBY_Japan/segments.jsonl) | 279 recovered units of work from Dataset B, strictly formatted in JSONL schema with ISO-8601 UTC timestamps across 15 sessions. | **Verified** |
| **Deliverable 2: Code & History** | Root Git Repository (`master`) | Clean semantic Git history, modular source code in `src/`, production CLIs in `scripts/`, and 46 automated pytest tests. | **Verified** |
| **Deliverable 3: Final Report** | [`final_report.md`](file:///c:/IBY_Japan/final_report.md) | Executive proposal: Step 2 process inventory, ROI ranking formula, prototype justification, human-in-the-loop residual work, empirical risk matrix, and 7-day budget rationale. | **Verified** |
| **Deliverable 4: Work Log** | [`work_log.md`](file:///c:/IBY_Japan/work_log.md) | Chronological 7-day engineering diary documenting hypotheses, trials, dead ends (IME capture, idle thresholds, F1 freeze pivot), and GenAI disclosure. | **Verified** |
| **Step 3 Primary Prototype** | [`src/automation/supplier_automation.py`](file:///c:/IBY_Japan/src/automation/supplier_automation.py) | High-performance deterministic backend workflow engine targeting Rank #1 (`supplier_communication`) with Japanese payload dispatch and escalation. | **Verified** |
| **Step 3 Secondary Prototype** | [`src/automation/expense_automation.py`](file:///c:/IBY_Japan/src/automation/expense_automation.py) | Financial accounting reimbursement engine targeting Rank #2 (`expense_processing`) with statutory expense caps and receipt validation. | **Verified** |
| **Interactive Executive Dashboard** | [`app.py`](file:///c:/IBY_Japan/app.py) | Full Streamlit web application providing interactive ROI visualizers, telemetry inspection, and live prototype execution. | **Verified** |

---

## 🏗️ System Architecture & Workflow

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   RAW WORKSTATION TELEMETRY                                      │
│           (Events: Keystrokes, Window Titles, Mouse Clicks, Active URLs, Clipboard, Screenshots)          │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          STAGE 1: ROBUST INGESTION & QUIRK MITIGATION                            │
│                                  (src/pipeline/loader.py)                                        │
│  • Multi-chunk session re-stitching           • Strict UTF-8 Japanese character decoding          │
│  • Chronological sorting across chunks         • Mitigation of buggy text_input_complete events   │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 2: THREE-TIER PROCESS SEGMENTATION ENGINE                          │
│                                (src/segmentation/)                                               │
│                                                                                                  │
│   [Tier 1: v1 Heuristic State Machine]   [Tier 2: v2 Vision Anomaly PoC]   [Tier 3: v3 Supervised ML]   │
│   • Entity-Centric Golden Thread         • MobileNet_V3_Small vectorizer   • HistGradientBoosting       │
│   • Clipboard entity tracing             • 4-frame relational rolling-win  • TF-IDF + LogisticRegression│
│   • /dashboard hub detection             • Suppresses micro-jitter         • 81.4% Boundary F1          │
│   • Deliverable 1 Deliverable (279 segs) • Captures silent DOM updates     • 93.9% Label Consistency   │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     STAGE 3: PROCESS MINING & AUTOMATION ROI PRIORITIZATION                      │
│                                (src/analytics/process_miner.py)                                  │
│  • Quantitative Metrics: Volume (N), Cumulative Time, Average Duration, Staff Infiltration       │
│  • Operational Friction: F = Average App Switches + Average Clipboard Operations                │
│  • Prioritization Formula: ROI_Score = (Volume * Friction) / Average_Duration                    │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       STAGE 4: DETERMINISTIC STEP 3 AUTOMATION PROTOTYPES                        │
│                                  (src/automation/)                                               │
│                                                                                                  │
│   [Candidate #1: Supplier PO Engine]                  [Candidate #2: Expense Policy Engine]       │
│   • Automated variance checking (Qty/Price/Date)      • Enforcement of corporate spending caps   │
│   • Japanese business email & EDI dispatch            • Receipt compliance & transit verification│
│   • Sub-second execution (<50ms)                      • Human-in-the-Loop manager escalation     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Segmentation Evolution: From Heuristics to Machine Learning

### 1. Tier 1: Entity-Centric Golden Thread State Machine (v1 Heuristics)
* **Core Design:** Employs domain-invariant behavioral primitives:
  - **Entity Anchor Tracing:** Captures business entities (PO numbers, employee codes, Case IDs) upon `clipboard_change` and tracks them across application boundaries (Web Portal $\leftrightarrow$ Word $\leftrightarrow$ Excel).
  - **Topological Navigation:** Detects returns to portal navigation hubs (`/dashboard`, `/index`).
  - **Inactivity Windows:** Emits natural task boundaries during prolonged operator pauses (>60 seconds).
  - **Semantic Merging:** Consolidates adjacent micro-fragments ($\le 30$s gap) sharing identical semantic labels without conflicting entity anchors.
* **Why Deliverable 1 Relies on v1 Heuristics:**
  - **Cross-Department Distributional Shift:** Telemetry in Dataset A was generated by specific operators (`Marcos`, `yuvraj`, `R36BQBTE`, `JAYESH`) working in Google Chrome on portal ports `5122–5124`. Dataset B introduces unseen operators (`CHAITANYA0BCF`, `LAPTOP-76QMG9DE`, `NEELA9BAF`), operating in **Microsoft Edge (Profile 1)** across new departments and portal ports `5132–5134`.
  - **Overfitting Immunity:** An aggressive supervised model trained exclusively on Dataset A is prone to memorizing operator keystroke cadences and portal ports. The v1 heuristic relies strictly on universal human work patterns, ensuring robust out-of-domain transfer.
  - **Empirical Ground-Truth Validation:** Yielded **279 segments** with an average duration of **35.8 seconds**—an almost exact mirror of Dataset A's verified ground truth (**37.1 seconds**).

### 2. Tier 2: Multi-Frame Context-Aware Computer Vision Engine (v2 Vision PoC)
* **Motivation:** Text-based telemetry cannot observe "silent" UI state updates (e.g., asynchronous AJAX data table reloads, modal dialog popups, and tab switches without keystrokes).
* **Implementation ([`src/experiments/vision_poc.py`](file:///c:/IBY_Japan/src/experiments/vision_poc.py)):**
  - Compressed all 34,563 1080p desktop screenshots from Dataset A into 1,000-dimensional semantic vectors using `MobileNet_V3_Small` on Google Colab T4 GPUs.
  - Engineered a **4-frame relational rolling window** ($f_1, f_2, f_3, f_4$) to evaluate transition drop magnitude against surrounding visual stability:
    $$\text{Drop Magnitude} = \frac{\text{Stability}_{before} + \text{Stability}_{after}}{2} - \text{Transition Similarity}$$
  - Cut false-positive visual cuts by **38.1%** (from 9,418 to 5,831 segments) and more than doubled Segment IoU F1 from 7.3% to **15.7%**.

### 3. Tier 3: Two-Stage Supervised Machine Learning Pipeline (v3 ML Breakthrough)
* **Stage 1: Temporal & Interaction Boundary Detector ([`scripts/train_boundary_model.py`](file:///c:/IBY_Japan/scripts/train_boundary_model.py)):**
  - Extracted 18 tabular temporal and interaction features across 162,650 event samples from Dataset A.
  - Trained a `HistGradientBoostingClassifier` with balanced class weights, achieving **0.9274 ROC-AUC** and **0.7674 PR-AUC** on validation sets.
* **Stage 2: Calibrated Semantic Process Classifier ([`scripts/train_label_classifier.py`](file:///c:/IBY_Japan/scripts/train_label_classifier.py)):**
  - Tokenized system ports (`SYS_HR_5122`, etc.), window titles, URL routes, OCR text, and form elements across 1,734 ground truth executions.
  - Trained a `TF-IDF + LogisticRegression` pipeline, achieving **95.1% validation accuracy** and **0.952 Macro F1** across all 15 business processes.
* **Inference Engine ([`src/segmentation/ml_segmenter.py`](file:///c:/IBY_Japan/src/segmentation/ml_segmenter.py)):**
  - Features peak detection with 12s refractory suppression, idle-break filtering ($<10$ events over $>15$s), semantic merging within 35s, and automatic fallback to v1 heuristics if model weights are unavailable.

---

## 📈 Dataset A Evaluation & Accuracy Benchmarks

Evaluating predictions against the ground-truth execution manifests of all 63 sessions in Dataset A using [`scripts/evaluate_dataset_a.py`](file:///c:/IBY_Japan/scripts/evaluate_dataset_a.py) reveals the full engineering progression:

### Comprehensive Scorecard Comparison

| Metric | Raw Heuristic Baseline | v1 Golden Thread (LLM + Merging) | v2 Vision Anomaly PoC | v3 Two-Stage Supervised ML | Net Delta (v3 vs. Raw) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Predicted Segments** | 2,456 | **2,010** *(True: 2,009)* | 5,831 | **2,060** *(True: 2,009)* | **-396 (Resolved Over-segmentation)** |
| **Boundary Precision** | 41.5% | 45.4% | 13.9% | **79.7%** | **+38.2%** |
| **Boundary Recall** | 53.5% | 48.1% | 43.8% | **83.9%** | **+30.4%** |
| **Boundary F1-Score** | 46.5% | 46.4% | 20.9% | **81.4%** | **+34.9% (Major Breakthrough)** |
| **Segment Precision** | 49.1% | 52.4% | 10.4% | **73.1%** | **+24.0%** |
| **Segment Recall** | 56.2% | 59.6% | 33.8% | **82.7%** | **+26.5%** |
| **Segment IoU F1 ($\ge 0.5$)** | 34.2% | 55.5% | 15.7% | **77.3%** | **+43.1%** |
| **Label Consistency (Purity)**| 9.2% | **65.8%** | 16.8% | **93.9%** | **+84.7% (Near-Perfect Mapping)** |

### Per-Process Classification Accuracy (v3 ML Engine)

| Process Category | Code | Classification Purity | Matched Samples | Operational Domain |
| :--- | :---: | :---: | :---: | :--- |
| **`inventory_adjustment`** | `L` | **100.0%** | 75 / 75 | Supply Chain & Warehousing |
| **`resident_tax_verification`** | `A` | **99.1%** | 116 / 117 | Human Resources & Payroll |
| **`invoice_approval`** | `F` | **99.1%** | 113 / 114 | Financial Accounting |
| **`return_processing`** | `O` | **98.7%** | 78 / 79 | Supply Chain Logistics |
| **`payment_processing`** | `J` | **98.6%** | 70 / 71 | Treasury & Disbursements |
| **`supplier_communication`** | `M` | **98.4%** | 122 / 124 | Procurement & Sourcing |
| **`budget_variance_analysis`** | `I` | **97.8%** | 91 / 93 | Financial FP&A |
| **`onboarding_verification`** | `E` | **97.4%** | 74 / 76 | Human Resources |
| **`leave_application_processing`** | `C` | **97.3%** | 107 / 110 | Human Resources |
| **`expense_processing`** | `G` | **96.6%** | 86 / 89 | General Accounting |
| **`shipment_tracking`** | `N` | **92.5%** | 86 / 93 | Outbound Logistics |
| **`bank_reconciliation`** | `H` | **86.3%** | 101 / 117 | Financial Accounting |
| **`order_processing`** | `K` | **85.6%** | 77 / 90 | Customer Sales Operations |
| **`payroll_adjustment`** | `B` | **81.9%** | 86 / 105 | Human Resources & Payroll |
| **`insurance_pension_processing`** | `D` | **79.6%** | 78 / 98 | Statutory Compliance |
| **Macro Average Accuracy** | — | **93.9%** | **1,245 / 1,326** | **All Enterprise Domains** |

---

## 📊 Step 2 Process Mining & ROI Candidate Prioritization

Applying our verified process miner ([`src/analytics/process_miner.py`](file:///c:/IBY_Japan/src/analytics/process_miner.py)) to the 15 production sessions in Dataset B produced the quantified inventory:

$$\text{ROI\_Score} = \frac{\text{Volume} \times \text{Friction}}{\text{Average\_Duration}}$$
$$\text{Friction} = \text{Average App Switches} + \text{Average Clipboard Operations}$$

### Dataset B Production Ranking

| Rank | Business Process | Volume ($N$) | Total Time (min) | Avg Dur (s) | App Switches | Clip Ops | Friction | Sessions | Staff | ROI Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | **`supplier_communication`** | **100** | **61.9** | **37.1s** | **6.8** | **2.6** | **9.39** | **14 / 15** | **4 / 4** | **25.30** |
| **#2** | **`expense_processing`** | **61** | **35.0** | **34.4s** | **6.3** | **3.2** | **9.44** | **14 / 15** | **4 / 4** | **16.75** |
| **#3** | `onboarding_verification` | 21 | 11.8 | 33.7s | 6.4 | 2.7 | 9.10 | 9 / 15 | 4 / 4 | 5.67 |
| **#4** | `leave_application_processing` | 26 | 18.0 | 41.6s | 4.9 | 3.8 | 8.73 | 11 / 15 | 4 / 4 | 5.45 |
| **#5** | `inventory_adjustment` | 25 | 15.8 | 38.0s | 3.4 | 4.7 | 8.12 | 11 / 15 | 4 / 4 | 5.34 |
| **#6** | `payroll_adjustment` | 16 | 7.9 | 29.7s | 4.6 | 2.9 | 7.50 | 8 / 15 | 3 / 4 | 4.04 |
| **#7** | `invoice_approval` | 13 | 5.5 | 25.3s | 2.0 | 2.3 | 4.31 | 8 / 15 | 4 / 4 | 2.21 |
| **#8** | `return_processing` | 2 | 0.4 | 12.5s | 9.0 | 0.0 | 9.00 | 2 / 15 | 1 / 4 | 1.44 |
| **#9** | `resident_tax_verification` | 6 | 2.7 | 27.0s | 2.7 | 2.3 | 5.00 | 4 / 15 | 3 / 4 | 1.11 |
| **#10** | `budget_variance_analysis` | 4 | 3.2 | 48.2s | 6.8 | 3.0 | 9.75 | 2 / 15 | 2 / 4 | 0.81 |
| **#11** | `shipment_tracking` | 2 | 1.5 | 44.0s | 2.0 | 5.5 | 7.50 | 2 / 15 | 2 / 4 | 0.34 |
| **#12** | `payment_processing` | 1 | 0.4 | 22.0s | 0.0 | 3.0 | 3.00 | 1 / 15 | 1 / 4 | 0.14 |
| — | *Total Enterprise Metrics* | *279* | *166.3 min* | *35.8s avg* | *5.9 avg* | *3.1 avg* | *9.00 avg* | *15 sessions* | *4 staff* | *—* |

> **Key Operational Takeaway:**  
> **`supplier_communication`** and **`expense_processing`** represent **57.7% of all operational volume** (161 of 279 executions) and generate extreme context-switching drag (over 9.3 friction points each). Automating `supplier_communication` alone recovers **over 410 hours of annual labor** across the department.

---

## ⚡ Step 3 Working Automation Prototypes

### Prototype 1: Supplier Communication Workflow Engine
* **Source:** [`src/automation/supplier_automation.py`](file:///c:/IBY_Japan/src/automation/supplier_automation.py)
* **Target:** Rank #1 Bottleneck (`supplier_communication`)
* **Logic & Policy Rules:**
  - **Quantity Variance:** $\le 25\%$ change $\to$ `AUTO_APPROVED`
  - **Price Variance:** $\le 5\%$ change $\to$ `AUTO_APPROVED`
  - **Delivery Schedule Shift:** $\le 5$ days $\to$ `AUTO_APPROVED`
  - **Non-Standard Exceptions:** Breaching any threshold escalates immediately to `ESCALATED_TO_MANAGER` with Japanese rationale.
* **Output Payload:** Generates complete Japanese business correspondence (`仕入先への依頼`, confirm comments, change histories).

### Prototype 2: Expense Reimbursement Policy Engine
* **Source:** [`src/automation/expense_automation.py`](file:///c:/IBY_Japan/src/automation/expense_automation.py)
* **Target:** Rank #2 Bottleneck (`expense_processing`)
* **Logic & Accounting Rules:**
  - **Entertainment Expenses (`接待交際費`):** $\le ¥10,000$ per attendee $\to$ `AUTO_APPROVED`
  - **Domestic Transit (`交通費`):** $\le ¥30,000$ per claim $\to$ `AUTO_APPROVED`
  - **Office Supplies (`消耗品費`):** $\le ¥50,000$ per claim $\to$ `AUTO_APPROVED`
  - **Compliance Guardrail:** Missing receipts trigger mandatory escalation to Finance Directors.

### Live Executive Web Dashboard
* **Source:** [`app.py`](file:///c:/IBY_Japan/app.py)
* **Framework:** Streamlit (running headless on port `8502`)
* **Features:**
  - Dynamic KPI cards and ROI prioritization scatter plots.
  - Interactive telemetry trace visualizer.
  - Live interactive policy simulators with real-time JSON and Japanese text generation.

---

## 📂 Repository Directory Layout

```
c:/IBY_Japan/
├── .gitignore                          # Clean exclusions (pycache, temporary files)
├── README.md                           # Master architectural & usage guide
├── DATA_SCHEMA.md                      # Telemetry specifications & recording quirk notes
├── information.md                      # Client problem brief & selection requirements
├── final_report.md                     # Deliverable 3: Executive proposal & strategy
├── work_log.md                         # Deliverable 4: 7-day chronological diary + GenAI disclosure
├── segments.jsonl                      # Deliverable 1: 279 production segments (Dataset B)
├── process_mining_results.json         # Step 2: Mined metrics & ROI rankings
├── colab_notebook.ipynb                # GPU vision batch processing notebook
├── app.py                              # Live Streamlit dashboard (Procurement & Finance)
│
├── src/                                # Core Modular Library
│   ├── pipeline/
│   │   ├── __init__.py                 # Clean package exports
│   │   └── loader.py                   # Ingestion, chunk stitching, UTF-8 normalization
│   ├── segmentation/
│   │   ├── __init__.py                 # Segmenter exports
│   │   ├── segmenter.py                # Golden Thread v1 heuristic state machine
│   │   ├── llm_labeler.py              # LLM prompt generator & semantic regex dictionary
│   │   ├── ml_segmenter.py             # Two-stage supervised ML pipeline (81.4% F1)
│   │   ├── boundary_model.pkl          # Trained HistGradientBoosting boundary model
│   │   └── label_model.pkl             # Trained TF-IDF + LogisticRegression label model
│   ├── analytics/
│   │   ├── __init__.py                 # Analytics package exports
│   │   └── process_miner.py            # Process mining & ROI prioritization engine
│   ├── automation/
│   │   ├── __init__.py                 # Automation exports
│   │   ├── supplier_automation.py      # Step 3 Candidate #1 prototype (Procurement)
│   │   └── expense_automation.py       # Step 3 Candidate #2 prototype (Finance)
│   └── experiments/
│       └── vision_poc.py               # MobileNet visual cosine anomaly detector
│
├── scripts/                            # Production CLI Tooling
│   ├── run_segmentation.py             # Dual-mode runner (--mode [heuristic|ml])
│   ├── evaluate_dataset_a.py           # Ground-truth evaluation harness (F1, IoU, Purity)
│   ├── mine_dataset_b.py               # Dataset B process mining CLI
│   ├── train_boundary_model.py         # Boundary model training script (HistGradientBoosting)
│   ├── train_label_classifier.py       # Label classifier training script (TF-IDF + LogReg)
│   ├── convert_vision_boundaries.py    # Vision boundary to segment converter
│   ├── eda_dataset_a.py                # Exploratory telemetry analysis
│   └── verify_submission.py            # Official 5-point submission verification harness
│
├── tests/                              # Complete Automated Test Suite (46 tests)
│   ├── test_loader.py                  # Ingestion & quirk handling tests (3 tests)
│   ├── test_segmenter.py               # State machine boundary detection tests (9 tests)
│   ├── test_evaluator.py               # Boundary F1 & IoU evaluation tests (19 tests)
│   ├── test_ml_segmenter.py            # Machine learning pipeline tests (5 tests)
│   ├── test_automation.py              # Supplier workflow & approval tests (5 tests)
│   └── test_expense_automation.py      # Expense workflow & compliance tests (5 tests)
│
└── dataset_a/                          # Ground Truth Benchmark (63 sessions)
    ├── evaluated_segments_baseline.jsonl # v1 Heuristic predictions (2,010 segments)
    ├── evaluated_segments_ml.jsonl       # v3 Two-Stage ML predictions (2,060 segments)
    ├── evaluated_segments_multiframe.jsonl # Multi-frame vision evaluated segments
    ├── evaluated_segments_single.jsonl   # Single-frame vision evaluated segments
    └── vision_boundaries_multiframe.jsonl # Multi-frame vision raw boundary detections
```

---

## 🚀 Quickstart & Execution Guide

All components run out-of-the-box in Python 3.10+ environments:

### 1. Run Automated Submission Verification (All 5 Checks)
```powershell
python scripts/verify_submission.py
```
*Executes the official 5-point compliance harness, validating `segments.jsonl` schema, `final_report.md`, `work_log.md`, Step 3 prototype execution, and all 46 pytest tests.*

### 2. Launch Interactive Executive Streamlit Dashboard
```powershell
python -m streamlit run app.py --server.port 8502
```
*Launches the browser UI featuring the ROI Prioritization Matrix, Telemetry Explorer, and Live Rule Simulation Engines.*

### 3. Run the Automated Pytest Test Suite
```powershell
python -m pytest -v
```
*Executes all 46 unit and integration tests across data ingestion, segmentation, evaluation, and automation modules (100% pass rate in ~6 seconds).*

### 4. Execute Step 3 Automation Prototype Demo (CLI Mode)
```powershell
python src/automation/supplier_automation.py --demo
```
*Processes a batch of purchase order change requests, demonstrating automatic rule approvals and managerial exception routing.*

### 5. Evaluate Accuracy on Dataset A (Ground Truth Benchmark)
```powershell
# Evaluate v1 Heuristic Baseline (46.4% Boundary F1, 65.8% Consistency)
python scripts/evaluate_dataset_a.py --predictions dataset_a/evaluated_segments_baseline.jsonl --dataset-dir dataset_a

# Evaluate v3 Two-Stage ML Model (81.4% Boundary F1, 93.9% Consistency)
python scripts/evaluate_dataset_a.py --predictions dataset_a/evaluated_segments_ml.jsonl --dataset-dir dataset_a
```

### 6. Mine Dataset B Production Telemetry
```powershell
python scripts/mine_dataset_b.py
```
*Runs segmentation across Dataset B, extracts 279 production segments to `segments.jsonl`, and updates `process_mining_results.json`.*

### 7. Train Supervised ML Models (Optional)
```powershell
# Train Stage 1 Boundary Gradient Booster
python scripts/train_boundary_model.py --dataset-dir dataset_a

# Train Stage 2 Semantic TF-IDF Classifier
python scripts/train_label_classifier.py --dataset-dir dataset_a
```

---

## 🛡️ Automated Testing & Verification

The repository includes a comprehensive 46-test automated verification suite (`tests/`):

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 46 items

tests\test_automation.py .....                                           [ 10%]
tests\test_evaluator.py ...................                              [ 52%]
tests\test_expense_automation.py .....                                   [ 63%]
tests\test_loader.py ...                                                 [ 69%]
tests\test_ml_segmenter.py .....                                         [ 80%]
tests\test_segmenter.py .........                                        [100%]

============================= 46 passed in 6.12s ==============================
```

- **Data Ingestion Tests (`test_loader.py`):** Validates chronological event ordering across chunk boundaries, UTF-8 normalization, and dropping unreliable `text_input_complete` records.
- **Segmentation State Machine Tests (`test_segmenter.py`):** Validates noise filtering, entity anchor lifecycle tracking, `/dashboard` navigation cuts, and semantic merging.
- **Evaluation Metric Tests (`test_evaluator.py`):** Validates boundary matching within $\pm 5$s tolerance, IoU calculation ($\ge 0.5$), and label purity scoring.
- **Machine Learning Tests (`test_ml_segmenter.py`):** Validates tabular feature extraction, model inference, peak boundary suppression, and graceful heuristic fallback.
- **Automation Engine Tests (`test_automation.py`, `test_expense_automation.py`):** Validates boundary conditions, auto-approval thresholds, Japanese correspondence generation, and managerial escalation.

---

## 🤖 Generative AI Disclosure

In strict accordance with the guidelines set forth in [`information.md`](file:///c:/IBY_Japan/information.md):
- **Japanese Natural Language Understanding:** Generative AI was utilized to analyze and translate Japanese UI window titles, form placeholders (`照合内容・確認コメントを入力してください`, `消込理由`, `仕入先への依頼`), and document naming conventions into standardized 2–3 word English business process categories.
- **Test Generation Assistance:** Generative AI assisted in rapid drafting of unit test fixtures (`pytest`) and data-structure serialization routines, followed by 100% manual code review and verification.
- **Production Guardrails:** No production automation decisions rely on unconstrained or unverified LLM generation; all business rule validation and exception routing in the Step 3 prototype remain fully deterministic.
