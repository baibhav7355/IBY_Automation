# Process Mining & Intelligent Automation Engine
### Telemetry Ingestion, Segmentation & Automation

[![Submission Status](https://img.shields.io/badge/Submission-Completed-brightgreen.svg?style=flat-square)](#-project-deliverables)
[![Live Demo](https://img.shields.io/badge/Live%20App-Render-blue.svg?style=flat-square)](https://iby-automation.onrender.com/)
[![Test Suite](https://img.shields.io/badge/Pytest-46%2F46%20Passed-success.svg?style=flat-square)](#-how-to-run)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg?style=flat-square)](#-how-to-run)
[![Boundary F1](https://img.shields.io/badge/Boundary%20F1-81.4%25%20(ML)-orange.svg?style=flat-square)](#-dataset-a-evaluation--accuracy-benchmarks)
[![Label Consistency](https://img.shields.io/badge/Label%20Purity-93.9%25%20(ML)-blueviolet.svg?style=flat-square)](#-dataset-a-evaluation--accuracy-benchmarks)
[![Dataset B Segments](https://img.shields.io/badge/Dataset%20B-279%20Segments-informational.svg?style=flat-square)](#-step-2-process-mining--roi-candidate-prioritization)

---

> **Author:** Baibhav Gond  
> **University:** Indian Institute of Technology Bhubaneswar  
> **Department:** Department of Civil Engineering  
> **Email:** [baibhav0019@gmail.com](mailto:baibhav0019@gmail.com)  
> **Live Web Application:** [Process Mining & Automation](https://iby-automation.onrender.com/)  

---

## 📌 Executive Summary

### The Challenge
In the company's back-office departments (HR, Finance, Logistics), staff spend their days moving back and forth between internal web systems and desktop applications like Excel and Word, processing routine paperwork. 

The company ran a desktop agent that recorded every keystroke, mouse click, and application switch in chronological order. However, these logs only captured raw actions—nothing indicated when an expense claim or onboarding task actually started or finished. The logs were piling up untouched because nobody knew what tasks were being performed, how long they took, or where people were getting slowed down.

Management had one core request:
> *"Use these logs to tell us where automation would have the greatest impact on our operations. And show us something that actually works."*

My goal for this task was to turn these raw event streams into distinct business processes, identify the biggest bottlenecks eating up staff time, and build a working automation prototype that delivers tangible ROI.

### The Solution
To tackle this, I built a modular Python pipeline:
1. **Data Ingestion & Cleaning:** Handled multi-chunk session logs, enforced UTF-8 Japanese character decoding, and filtered out corrupted event records (such as malformed `text_input_complete` events per `DATA_SCHEMA.md`).
2. **Process Segmentation Approaches:**
   - **v1 Heuristic State Machine:** Built a rule-based segmenter tracking entity clipboard transfers (`Ctrl+C`/`Ctrl+V`) and portal navigation hubs. This produced the 279 clean segments submitted in `segments.jsonl` (Deliverable 1).
   - **v2 Computer Vision PoC:** Tested a lightweight `MobileNet_V3_Small` vision model across 34,563 screenshots using a 4-frame rolling window to catch silent UI changes that text logs miss.
   - **v3 Supervised ML Pipeline:** Trained a two-stage classifier (`HistGradientBoosting` for boundaries and `TF-IDF + LogisticRegression` for process labels) on Dataset A, reaching **81.4% Boundary F1** and **93.9% Label Consistency**.
3. **Process Mining (Dataset B):** Mined the 15 production sessions across 4 workstations to rank processes by volume and manual friction (app switches and copy-paste frequency). Two tasks account for **57.7% of all back-office volume**: `supplier_communication` (Rank #1) and `expense_processing` (Rank #2).
4. **Step 3 Working Prototypes:** Built deterministic, rule-based automation engines for both top bottlenecks with Japanese business correspondence dispatch, spending checks, and manager escalation for exceptions, accompanied by an interactive Streamlit dashboard.

---

## 🗂️ Project Deliverables

Here is a quick summary of all deliverables submitted in this repository:

| Deliverable | File / Location | Description |
| :--- | :--- | :--- |
| **Deliverable 1: Step 1 Output** | [`segments.jsonl`](file:///c:/IBY_Japan/segments.jsonl) | 279 recovered units of work from Dataset B, formatted in JSONL with ISO-8601 UTC timestamps across all 15 sessions. |
| **Deliverable 2: Code & History** | Root Git Repository (`master`) | Modular source code in `src/`, reproduction CLI scripts in `scripts/`, and 46 automated unit tests. |
| **Deliverable 3: Final Report** | [`final_report.md`](file:///c:/IBY_Japan/final_report.md) | Complete proposal: Step 2 process inventory, ROI ranking, prototype design choices, human-in-the-loop residual work, and risk analysis. |
| **Deliverable 4: Work Log** | [`work_log.md`](file:///c:/IBY_Japan/work_log.md) | Day-by-day engineering diary documenting what was tried each day, what worked, what failed, and GenAI disclosure. |
| **Step 3 Primary Prototype** | [`src/automation/supplier_automation.py`](file:///c:/IBY_Japan/src/automation/supplier_automation.py) | Working deterministic automation engine for the Rank #1 bottleneck (`supplier_communication`) with Japanese email/EDI dispatch. |
| **Step 3 Secondary Prototype** | [`src/automation/expense_automation.py`](file:///c:/IBY_Japan/src/automation/expense_automation.py) | Accounting reimbursement engine for Rank #2 (`expense_processing`) with spending caps and receipt verification. |
| **Interactive Dashboard** | [`app.py`](file:///c:/IBY_Japan/app.py) | Streamlit web application to visually explore the process mining results, telemetry data, and run the prototypes interactively. |

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
│   • Deliverable 1 Output (279 segs)      • Captures silent DOM updates     • 93.9% Label Consistency   │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     STAGE 3: PROCESS MINING & AUTOMATION ROI PRIORITIZATION                      │
│                                (src/analytics/process_miner.py)                                  │
│  • Quantitative Metrics: Volume (N), Cumulative Time, Average Duration, Active Staff Count       │
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

### 2. Tier 2: Multi-Frame Context-Aware Computer Vision Engine (v2 Vision PoC)
* **Motivation:** Text-based telemetry cannot observe "silent" UI state updates (e.g., asynchronous AJAX data table reloads, modal dialog popups, and tab switches without keystrokes).
* **Implementation ([`src/experiments/vision_poc.py`](file:///c:/IBY_Japan/src/experiments/vision_poc.py)):**
  - Compressed all 34,563 1080p desktop screenshots from Dataset A into 1,000-dimensional semantic vectors using `MobileNet_V3_Small` on Google Colab T4 GPUs.
  - Engineered a **4-frame relational rolling window** ($f_1, f_2, f_3, f_4$) to evaluate transition drop magnitude against surrounding visual stability:

$$
\text{Drop Magnitude} = \frac{\text{Stability}_{\text{before}} + \text{Stability}_{\text{after}}}{2} - \text{Transition Similarity}
$$

  - Cut false-positive visual cuts by **38.1%** (from 9,418 to 5,831 segments) and more than doubled Segment IoU F1 from 7.3% to **15.7%**.

### 3. Tier 3: Two-Stage Supervised Machine Learning Pipeline (v3 Supervised ML)
* **Stage 1: Temporal & Interaction Boundary Detector ([`scripts/train_boundary_model.py`](file:///c:/IBY_Japan/scripts/train_boundary_model.py)):**
  - Extracts 18 tabular temporal and interaction features per event (`dt_prev`, `dt_next`, `is_app_sw`, `is_clip`, `clip_delta`, `has_id`, `hub`, `url_depth`, `app_cat`, `idle_10s`, `idle_30s`, etc.) across 162,650 event samples from Dataset A.
  - Trained a `HistGradientBoostingClassifier` with balanced class weights, achieving **0.9274 ROC-AUC** and **0.7674 PR-AUC** on validation sets.
* **Stage 2: Calibrated Semantic Process Classifier ([`scripts/train_label_classifier.py`](file:///c:/IBY_Japan/scripts/train_label_classifier.py)):**
  - Tokenizes system port signatures (`SYS_HR_5122`, `SYS_FIN_5123`, `SYS_OPS_5124`), route hashes, native window titles, form input labels, and OCR text across 1,734 ground truth executions.
  - Trained a calibrated `TF-IDF + LogisticRegression` pipeline, achieving **95.1% validation accuracy** and **0.952 Macro F1** across all 15 business processes.
* **Inference Engine ([`src/segmentation/ml_segmenter.py`](file:///c:/IBY_Japan/src/segmentation/ml_segmenter.py)):**
  - **Adaptive Refractory Peak Suppression (12s):** Suppresses micro-jitter cuts by retaining only the highest-probability boundary candidate within a 12-second rolling gap.
  - **Idle Pause Pruning:** Discards non-operational idle gaps ($<10$ events over $>15$s).
  - **Semantic Post-Processing & Merging:** Merges adjacent split fragments sharing identical labels within a 35-second temporal window, unifying multi-app alt-tab loops into complete business processes.
  - **Graceful Heuristic Fallback:** Automatically switches to the v1 state machine if ML model weights are absent.
* **Why Accuracy Jumped to 81.4% F1 & 93.9% Consistency:**
  - *Zero Cross-Portal Leakage:* Tokenizing port IDs mathematically isolates HR (`:5122`), Finance (`:5123`), and Ops (`:5124`), boosting label purity from 65.8% to 93.9%.
  - *Jitter Suppression:* 12s refractory peak suppression elevated Boundary Precision from 45.4% to 79.7% (+34.3%).
  - *End-to-End Overlap:* 35s semantic merging boosted Segment IoU F1 ($\ge 0.5$) from 55.5% to 77.3% (+21.8%) with **99.0% volume fidelity (1,989 predicted vs. 2,009 true executions)**.

### Why Deliverable 1 Relies on v1 Heuristics
* **Cross-Department Distributional Shift:** Telemetry in Dataset A was generated by specific operators (`Marcos`, `yuvraj`, `R36BQBTE`, `JAYESH`) working in Google Chrome on portal ports `5122–5124`. Dataset B introduces unseen operators (`CHAITANYA0BCF`, `LAPTOP-76QMG9DE`, `NEELA9BAF`), operating in **Microsoft Edge (Profile 1)** across new departments and portal ports `5132–5134`.
* **Overfitting Immunity:** An aggressive supervised model trained exclusively on Dataset A is prone to memorizing operator keystroke cadences and portal ports. The v1 heuristic relies strictly on universal human work patterns, ensuring robust out-of-domain transfer.
* **Empirical Ground-Truth Validation:** Yielded **279 segments** with an average duration of **35.8 seconds**—an almost exact mirror of Dataset A's verified ground truth (**37.1 seconds**).

---

## 📈 Dataset A Evaluation & Accuracy Benchmarks

Evaluating predictions against the ground-truth execution manifests of all 63 sessions in Dataset A using [`scripts/evaluate_dataset_a.py`](file:///c:/IBY_Japan/scripts/evaluate_dataset_a.py) reveals the full engineering progression:

### Comprehensive Scorecard Comparison

| Metric | Raw Heuristic Baseline | v1 Golden Thread (LLM + Merging) | v2 Vision Anomaly PoC | v3 Two-Stage Supervised ML | Net Delta (v3 vs. Raw) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Predicted Segments** | 2,456 | **2,010** *(True: 2,009)* | 5,831 | **1,989** *(True: 2,009)* | **-467 (Resolved Over-segmentation)** |
| **Boundary Precision** | 41.5% | 45.4% | 13.9% | **79.7%** | **+38.2%** |
| **Boundary Recall** | 53.5% | 48.1% | 43.8% | **83.9%** | **+30.4%** |
| **Boundary F1-Score** | 46.5% | 46.4% | 20.9% | **81.4%** | **+34.9%** |
| **Segment Precision** | 49.1% | 52.4% | 10.4% | **73.1%** | **+24.0%** |
| **Segment Recall** | 56.2% | 59.6% | 33.8% | **82.7%** | **+26.5%** |
| **Segment IoU F1 ($\ge 0.5$)** | 34.2% | 55.5% | 15.7% | **77.3%** | **+43.1%** |
| **Label Consistency (Purity)**| 9.2% | **65.8%** | 16.8% | **93.9%** | **+84.7%** |

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

Running the process mining script ([`src/analytics/process_miner.py`](file:///c:/IBY_Japan/src/analytics/process_miner.py)) on the 15 production sessions in Dataset B gives the following process breakdown:

$$\text{ROI Score} = \frac{\text{Volume} \times \text{Friction}}{\text{Average Duration}}$$
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
| — | *Total across all sessions* | *279* | *166.3 min* | *35.8s avg* | *5.9 avg* | *3.1 avg* | *9.00 avg* | *15 sessions* | *4 staff* | *—* |

> **Key Takeaway:**  
> **`supplier_communication`** and **`expense_processing`** account for **57.7% of all operational volume** (161 of 279 executions) and involve heavy context switching (averaging over 9 app switches and clipboard actions per task). Automating `supplier_communication` alone saves **over 410 hours of manual labor per year** across the team.

---

## ⚡ Step 3 Working Automation Prototypes

### Prototype 1: Supplier Communication Workflow Engine
* **Source:** [`src/automation/supplier_automation.py`](file:///c:/IBY_Japan/src/automation/supplier_automation.py)
* **Target:** Rank #1 Bottleneck (`supplier_communication`)
* **Logic & Policy Rules:**
  - **Quantity Variance:** $\le 25\%$ change $\to$ `AUTO_APPROVED`
  - **Price Variance:** $\le 5\%$ change $\to$ `AUTO_APPROVED`
  - **Delivery Schedule Shift:** $\le 5$ days $\to$ `AUTO_APPROVED`
  - **Non-Standard Exceptions:** Breaching any threshold escalates immediately to `ESCALATED_TO_MANAGER` with operational rationale.
* **Output Payload:** Generates complete business correspondence (supplier requests, confirm comments, change histories).

### Prototype 2: Expense Reimbursement Policy Engine
* **Source:** [`src/automation/expense_automation.py`](file:///c:/IBY_Japan/src/automation/expense_automation.py)
* **Target:** Rank #2 Bottleneck (`expense_processing`)
* **Logic & Accounting Rules:**
  - **Entertainment Expenses:** $\le ¥10,000$ per attendee $\to$ `AUTO_APPROVED`
  - **Domestic Transit:** $\le ¥30,000$ per claim $\to$ `AUTO_APPROVED`
  - **Office Supplies:** $\le ¥50,000$ per claim $\to$ `AUTO_APPROVED`
  - **Compliance Guardrail:** Missing receipts trigger mandatory escalation to Finance Directors.

### Interactive Streamlit Dashboard
* **Live Web Application:** [I'm beside you | FDE Process Mining & Automation](https://iby-automation.onrender.com/)
* **Source:** [`app.py`](file:///c:/IBY_Japan/app.py)
* **Framework:** Streamlit web application
* **Features:**
  - Visual summary cards and process ranking charts.
  - Interactive event trace explorer.
  - Live simulation of the automation prototypes with rule checks and message generation.

---

## 📂 Repository Directory Layout

```
c:/IBY_Japan/
├── .gitignore                          # Clean exclusions (pycache, temporary files)
├── README.md                           # Master architectural & usage guide
├── DATA_SCHEMA.md                      # Telemetry specifications & recording quirk notes
├── final_report.md                     # Deliverable 3: Executive proposal & strategy
├── work_log.md                         # Deliverable 4: 7-day chronological diary + GenAI disclosure
├── segments.jsonl                      # Deliverable 1: 279 production segments (Dataset B)
├── process_mining_results.json         # Step 2: Mined metrics & ROI rankings
├── app.py                              # Live Streamlit dashboard (Procurement & Finance)
│
├── experiments/                        # Computer Vision Experimentation & Colab Pipeline
│   ├── README.md                       # Vision anomaly detection documentation & methodology
│   ├── vision_boundary.ipynb           # Full executed Colab notebook on T4 GPU (34,563 screenshots)
│   ├── colab_notebook.ipynb            # Standalone portable Colab template notebook
│   ├── vision_boundaries_multiframe.jsonl # Raw 4-frame relational anomaly detection boundaries
│   ├── evaluated_segments.jsonl        # Converted ISO-8601 session segments (5,831 segments)
│   └── convert_vision_boundaries.py    # Boundary-to-segment conversion utility script
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
├── scripts/                            # Reproduction and utility scripts
│   ├── run_segmentation.py             # Dual-mode runner (--mode [heuristic|ml])
│   ├── evaluate_dataset_a.py           # Ground-truth evaluation harness (F1, IoU, Purity)
│   ├── mine_dataset_b.py               # Dataset B process mining CLI
│   ├── train_boundary_model.py         # Boundary model training script (HistGradientBoosting)
│   ├── train_label_classifier.py       # Label classifier training script (TF-IDF + LogReg)
│   ├── convert_vision_boundaries.py    # Vision boundary to segment converter
│   └── eda_dataset_a.py                # Exploratory telemetry analysis
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
    ├── evaluated_segments_ml.jsonl       # v3 Two-Stage ML predictions (1,989 segments)
    ├── evaluated_segments_multiframe.jsonl # Multi-frame vision evaluated segments
    ├── evaluated_segments_single.jsonl   # Single-frame vision evaluated segments
    └── vision_boundaries_multiframe.jsonl # Multi-frame vision raw boundary detections
```

---

## 🚀 How to Run

> 🌐 **Live Cloud Demo:** [Process Mining & Automation](https://iby-automation.onrender.com/)  
> Access the fully interactive Streamlit analytics platform directly in the browser without local setup.

Requirements: Python 3.10+ with dependencies installed (`pip install -r requirements.txt`).

### 1. Run Automated Tests
Verify environment setup, data ingestion, segmentation logic, and prototype engines:
```bash
python -m pytest -v
```
*Runs all 46 unit and integration tests covering data loading, segmentation, evaluation, and automation prototypes.*

### 2. Run Process Mining on Dataset B (Step 1 & 2)
Process raw workstation telemetry across all 15 sessions, extract the 279 task segments (`segments.jsonl`), and compute process ROI rankings:
```bash
python scripts/mine_dataset_b.py
```
*Runs segmentation on Dataset B to generate `segments.jsonl` (Deliverable 1) and recalculate process rankings in `process_mining_results.json`.*

### 3. Test the Automation Prototype (Step 3)
Run the deterministic PO change approval engine against sample test cases (auto-approval vs. manager escalation):
```bash
python src/automation/supplier_automation.py --demo
```
*Processes sample purchase order change requests to demonstrate automatic rule approvals and manager escalation.*

### 4. Launch the Interactive Dashboard
Explore mined processes, inspect telemetry event traces, and test both automation prototypes in the browser:
```bash
python -m streamlit run app.py
```
*Opens the web dashboard to visually inspect mined processes, view event traces, and test prototypes.*

### 5. Benchmark & Evaluate Accuracy (Dataset A)
Evaluate segmentation predictions against Dataset A ground truth (63 sessions, 2,009 verified executions):
```bash
# Baseline heuristic state machine
python scripts/evaluate_dataset_a.py --predictions dataset_a/evaluated_segments_baseline.jsonl --dataset-dir dataset_a

# Two-stage supervised ML pipeline
python scripts/evaluate_dataset_a.py --predictions dataset_a/evaluated_segments_ml.jsonl --dataset-dir dataset_a
```

### 6. Retrain ML Models (Optional)
Re-train the boundary detector and semantic process classifier from Dataset A features:
```bash
python scripts/train_boundary_model.py --dataset-dir dataset_a
python scripts/train_label_classifier.py --dataset-dir dataset_a
```
