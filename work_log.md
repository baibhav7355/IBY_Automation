# Process Mining & Automation — Work Log

**Scope:** Corporate Back-Office Operations (HR, Finance, Procurement & Supply Chain)  
**Project:** PC Operation Log Analysis, Process Mining & Automation  
**Duration:** 7-Day Sprint  
**Author:** Baibhav Gond  
**Email:** baibhav0019@gmail.com  
**Institute:** Indian Institute of Technology Bhubaneswar

---

## Daily Work Diary

---

### Day 1: Data Pipeline & Environment Setup

**Objective:** Understand the data schema and domain, set up version control, and build a working data loader.

**What I did:**

Read through the project requirements and `DATA_SCHEMA.md` in detail. The back-office covers three departments — HR (ports `5122`/`5132`), Financial Accounting (`5123`/`5133`), and Supply Chain (`5124`/`5134`) — and the desktop logs capture keystrokes, mouse clicks, window title changes, app switches, clipboard events, and browser navigation.

Two things stood out from the data spec:
1. The recording agent splits sessions into separate time-windowed chunk subdirectories (`chunk_<timestamp>-<machine>/`). These need to be loaded and stitched in chronological order.
2. The `text_input_complete` event was flagged as unreliable — it frequently fires with empty payloads or out-of-order text during Japanese IME input conversions.

Set up the repo with module structure: `src/pipeline/`, `src/segmentation/`, `src/analytics/`, `src/automation/`, and `tests/`.

Built `src/pipeline/loader.py` — implemented `find_session_chunks`, `find_session_event_files`, and `load_session_events` with explicit UTF-8 decoding for Japanese character handling (`Shift_JIS` / `CP932` vs `UTF-8` compatibility). Added unit tests in `tests/test_loader.py` covering multi-chunk ordering, deduplication, and quirk filtering.

**What didn't work:**

Initially considered parsing `text_input_complete` events to reconstruct what operators were typing in forms. After inspecting raw logs, it was clear this was a dead end — the event fires with empty payloads or scrambled text during rapid Japanese IME conversions. Dropped it entirely and designed the pipeline to rely on deterministic clipboard changes, navigation events, and UI element attributes instead.

---

### Day 2: Evaluation Harness & Ground Truth Analysis

**Objective:** Build a rigorous evaluation benchmark before writing any segmentation algorithm, so there's an objective measure to work against.

**What I did:**

Analyzed Dataset A ground truth — 63 sessions, ~162,000 events, 2,009 verified process executions across 15 business process codes A through O. Ran `scripts/eda_dataset_a.py` to explore the data.

Key findings:
- **100% of business processes start inside a web browser portal** (Chrome in Dataset A, Edge in Dataset B).
- Processes follow a consistent 3-app signature: Web Portal ↔ Desktop document app (Excel or Word) ↔ Reference tool (Notepad or Explorer).
- Mean process duration across all 2,009 executions: ~42.3 seconds (IQR: 24s to 58s).

Built `scripts/evaluate_dataset_a.py` with three metrics:
- **Temporal Boundary Matching** with a ±5-second tolerance window (Precision, Recall, F1).
- **Segment-level IoU** (Intersection-over-Union ≥0.5) for execution overlap scoring.
- **Label Consistency Purity** to measure whether predicted labels map to the correct ground truth process families.

Also built `tests/test_evaluator.py` verifying precision, recall, duplicate penalty, and edge-case handling.

**What didn't work:**

First tried exact timestamp matching (±0 seconds). Results were terrible — valid boundaries got penalized because operators naturally have latency between reading a screen and executing their first click. Exact matching penalized valid boundaries by ~85%. Switched to a ±5-second tolerance window that reflects human task initiation cadences.

---

### Day 3: Heuristic Segmentation State Machine

**Objective:** Build the first version of the segmentation engine — split continuous event streams into discrete work units without any supervision.

**What I did:**

Came up with what I called the **"Golden Thread"** hypothesis: every back-office business process revolves around a single data entity — an Employee ID, Invoice Number (`INV-...`), Purchase Order (`PO-...`), or RMA Number (`RMA-...`). The operator copies this entity to the clipboard and carries it across application boundaries as they do their work.

Pre-processing first: wrote `filter_events` in `src/segmentation/segmenter.py` to drop high-frequency noise (mouse scrolls, raw keystrokes) while keeping state-changing events — app switches, clipboard changes, browser navigation, window title changes, `Ctrl+C`/`Ctrl+V` shortcuts, and form submit clicks.

Then built `GoldenThreadSegmenter`:
- **The Anchor:** Captures clipboard payloads (or length fingerprints when content is masked) as the active entity being worked on.
- **The Thread:** Tracks cross-application focus switches and browser navigation events.
- **Boundary Detection:** Emits a segment end when the operator returns to the portal hub (`/dashboard`, `/index`) after working in external apps, when a new conflicting entity is copied (switching cases), when the portal system changes (e.g. HR → Finance), or when inactivity exceeds 60 seconds (`IDLE_TIMEOUT_MS`).

**What didn't work:**

Tried pure idle-gap segmentation — split whenever the user paused for >15 seconds. This caused massive over-segmentation. Any time an employee paused to read a complex document or consult a colleague, the system split the segment. Boundary Precision dropped below 25%. The fix was grounding boundaries in portal hub returns and clipboard entity transitions rather than raw time gaps.

---

### Day 4: Baseline Evaluation, LLM Labeling & Semantic Merging

**Objective:** Evaluate the baseline segmenter on Dataset A, diagnose failure modes, and add semantic post-processing to fix over-segmentation.

**What I did:**

Ran the baseline `GoldenThreadSegmenter` across all 63 Dataset A sessions:
- **46.5% Boundary F1** (Precision: 41.5%, Recall: 53.5%) and **9.2% Label Consistency**
- 2,456 predicted segments vs. 2,009 true executions (+447 spurious fragments)

The over-segmentation was happening for a clear reason: when operators briefly navigated back to the portal to paste more data before continuing in Word/Excel, the state machine prematurely closed the segment and started a new one — splitting a single business case into multiple micro-fragments.

Two fixes:

**LLM Semantic Labeling (`src/segmentation/llm_labeler.py`):**  
Built `LABELING_PROMPT_TEMPLATE` instructing an LLM to analyze Japanese workstation context — window titles, URLs, OCR extracted text — and output a standardized 2–3 word English `snake_case` process label (e.g. `expense_processing`, `supplier_communication`). Built a high-precision keyword/regex token dictionary from the Day 2 EDA findings as a fallback.

**Semantic Merging (`merge_segments`):**  
Implemented in `src/segmentation/segmenter.py`: adjacent segments sharing the same label with a temporal gap ≤30 seconds are merged — as long as they don't have conflicting entity anchors. This consolidates natural multi-application alt-tab loops (portal → Excel → Notepad → portal) into a single coherent business transaction.

After both fixes:
- Predicted segments: **2,010** (vs. 2,009 true — within 1 segment!)
- **Boundary F1: 46.4%** (Precision: 45.4%, Recall: 48.1%)
- **Segment IoU F1: 55.5%**
- **Label Consistency: 65.8%** (up from 9.2% — a +56.6% jump)
- Key processes: `onboarding_verification` at 91.3%, `bank_reconciliation` at 86.2%

Identified the remaining gap: text heuristics cannot detect silent UI state changes — background async table loads, modal popups, SPA layout shifts. This accounts for an unobserved **33.4% variance gap**.

**Decision made: freeze segmentation here.** The remaining gap requires either visual data or a supervised model — neither of which can be fully resolved through more heuristic tuning. Pivoting to process mining would deliver higher value to the business than chasing marginal F1 improvements.

**What didn't work:**

Tried naive regex matching on window titles without any temporal smoothing. Incidental window title flickers during Alt-Tab transitions caused chaotic label instability. The 30-second temporal merging fixed it.

---

### Day 5: Computer Vision POC + Two-Stage ML Breakthrough

**Objective:** Investigate whether visual embeddings or supervised ML could close the 33.4% unobserved variance gap and push past the heuristic ceiling.

---

#### Part A — Computer Vision Anomaly Engine (Google Colab T4 GPU)

**The reasoning:**

Text-based heuristics are blind to silent visual UI transitions — asynchronous tables loading, modal confirmations appearing, error banners rendering inside SPAs where the URL never changes. A human operator sees these immediately. The hypothesis: dense visual embeddings of desktop screenshots could capture structural UI transitions without needing text cues.

The constraint: sending 34,563 full-HD screenshots to a commercial cloud vision API would cost thousands of dollars. Solution — run everything offline on Google Colab T4 GPU for free.

**What I built:**

Full pipeline in `experiments/Colab_vision_boundary.ipynb`:
- Mounted Google Drive, unzipped 34,563 screenshots to Colab's local NVMe disk (`/content/dataset_a`).
- Built a custom `ScreenshotDataset` + PyTorch `DataLoader(batch_size=128, num_workers=2)` with CUDA GPU acceleration.
- Vectorized all frames using `MobileNet_V3_Small` into 1,000-dimensional feature vectors.

**Experiment 1 — Single-frame consecutive thresholding:**  
Compared adjacent frame pairs, flagged a boundary whenever cosine similarity < 0.85.  
Generated `experiments/vision_boundaries.jsonl` — **9,481 predicted cuts** vs. 2,009 ground truth.  
Boundary Precision: **12.5%** — completely unusable.  
Root cause: cursor blinks, hover tooltips, individual keystrokes, tiny scrollbar movements all triggered false drops.

**Experiment 2 — 4-frame rolling relational buffer:**  
Upgraded to a `deque(maxlen=4)` buffer ($f_1, f_2, f_3, f_4$). Instead of comparing adjacent frames, the buffer checks whether a similarity drop is sustained relative to before and after:

$$\text{Drop Magnitude} = \frac{\text{Similarity}(f_1, f_2) + \text{Similarity}(f_3, f_4)}{2} - \text{Similarity}(f_2, f_3)$$

With `drop_tolerance = 0.15`, generated `experiments/vision_boundaries_multiframe.jsonl` — **5,894 detections** (down from 9,481).  
This eliminated **3,587 false-positive jitter cuts (-38.1%)** and more than doubled **Segment IoU F1 from 7.3% to 15.7%**.

Ported the full pipeline into `src/experiments/vision_poc.py` as a modular, reproducible offline reference implementation.

**Why not deployed for Dataset B:**  
Dataset B logs don't include screenshot archives (privacy + bandwidth constraints), and real-time 1080p vision processing needs GPU acceleration not available in production. This POC proved commercial feasibility of visual anomaly detection for future on-premise deployments.

---

#### Part B — Two-Stage Supervised ML Pipeline

**The reasoning:**

Two v1 failure modes were clearly solvable with supervised learning:
1. **Cross-portal label leakage:** Code L `inventory_adjustment` (port 5124) was frequently colliding with `payroll_adjustment` (port 5122) because the labeler matched URL regexes without conditioning on port signatures.
2. **Boundary granularity:** Pure DOM/window heuristics struggled to detect process starts when operators did not immediately copy an entity to the clipboard.

Trained on Dataset A's 162,650 event samples with ground truth labels.

**Stage 1 — Boundary Classifier (`scripts/train_boundary_model.py`):**  
`HistGradientBoostingClassifier` on 18 tabular features (`dt_prev`, `dt_next`, `is_app_sw`, `is_clip`, `clip_delta`, `has_id`, `hub`, `url_depth`, `app_cat`, `idle_10s`, `idle_30s`, and others) with a 12-second adaptive refractory peak suppression window.  
Result: **ROC-AUC: 0.9274**

**Stage 2 — Semantic Classifier (`scripts/train_label_classifier.py`):**  
TF-IDF + Logistic Regression conditioned on system port signatures (`:5122`, `:5123`, `:5124`), route hashes, window titles, and OCR text.  
Result: **95.1% accuracy, 0.952 Macro F1**

**Dataset A benchmark:**
- Boundary F1: **81.4%** (+35.0% absolute over v1; Precision: 79.7%, Recall: 83.9%)
- Segment IoU F1: **77.3%** (+21.8%; Precision: 73.1%, Recall: 82.7%)
- Label Consistency: **93.9%** (+28.1%; 100% on `inventory_adjustment`, >97% across 9 major workflows)
- Volume: **1,989 segments** vs. 2,009 ground truth (99.0% fidelity)

**Why v3 wasn't used for the Dataset B deliverable:**  
Dataset A and Dataset B use completely different operators, browsers (Chrome vs. Edge), and portal ports (`5122–5124` vs. `5132–5134`). A model trained on Dataset A will overfit to operator-specific keyboard rhythms and portal DOM quirks — failing on Dataset B. The v1 heuristic relies on universal invariants. Segmentation frozen; the ML engine saved for future in-domain deployment.

---

### Day 6: Production Ingestion (Dataset B), Process Mining & Bottleneck Discovery

**Objective:** Run the pipeline on Dataset B, generate the `segments.jsonl` deliverable, and identify the highest-value automation candidates.

**What I did:**

Extended the pipeline for Dataset B:
- Added Microsoft Edge (Profile 1) alongside Google Chrome.
- Configured Dataset B portal ports: `5132` (HR), `5133` (Finance), `5134` (Operations).
- Mapped production document templates: vendor registration procedures, monthly contract supplier lists, expense calculator (`expense_calc.xlsx`), and corporate entertainment regulations.

Ran `scripts/run_segmentation.py` on all 15 sessions — generated `segments.jsonl` with **279 business process segments**, 100% session coverage, average duration **35.8 seconds** (closely matching Dataset A's 37.1-second ground truth average).

Built `src/analytics/process_miner.py` to calculate comprehensive metrics per workflow: volume, cumulative time, mean duration, app switches, clipboard transitions, and the multi-factor ROI score:

$$\text{ROI Score} = \frac{\text{Volume} \times \text{Friction}}{\text{Average Duration}}$$

**Top findings:**
- **#1 `supplier_communication`:** 100 executions (35.8% of volume), 61.9 active minutes, 6.8 switches + 2.6 clipboard ops, friction 9.39 → **ROI Score: 25.30**
- **#2 `expense_processing`:** 61 executions (21.9% of volume), 35.0 active minutes, 6.3 switches + 3.2 clipboard ops, friction 9.44 → **ROI Score: 16.75**
- **Key finding: 57.7% of all back-office volume is in just these two workflows.**

Also dug into log payloads to identify specific handling patterns within each workflow — which cases are routine and rule-governed vs. which need human judgment. This distinction is what makes the automation design realistic.

**What didn't work:**

Initially tried ranking candidates by raw execution time alone. That incorrectly elevated `budget_variance_analysis` (48.2s average, only 4 runs) — an infrequent task with low standardization and poor ROI. Switched to the multi-factor formula weighting volume density and friction, which correctly surfaced the high-volume repetitive bottlenecks.

---

### Day 7: Automation Prototype, Risk Analysis & Final Delivery

**Objective:** Build and verify the automation engine for `supplier_communication`, extend it to `expense_processing`, complete the risk matrix, and package everything for submission.

**What I did:**

**1. Built the supplier automation engine (`src/automation/supplier_automation.py`):**

Designed as a stateless, deterministic policy microservice. Evaluates structured PO change requests in <50ms against business rules:
- Routine quantity adjustments (≤25% variance) → `AUTO_APPROVED`, generates automated PO confirmation comment
- Delivery buffer shifts (≤5 days) → `AUTO_APPROVED`
- Quality certificate chasing → automated dispatch
- Contractual breaches (>25% qty or >5% price) → `ESCALATED_TO_MANAGER`, transaction frozen with pre-calculated variance metrics

Defined the Express/Node.js REST API contract (`POST /api/v1/supplier-requests/process`) for web portal integration.

**2. Extended to expense processing (`src/automation/expense_automation.py`):**

Same `WorkflowEngineBase` pattern. Enforces Japanese corporate accounting rules:
- Entertainment: validates ≤¥10,000/head (corporate tax compliance). Over-budget dining flagged to department directors.
- Transit claims: auto-approves ≤¥30,000 bullet train and transport expenses.
- Missing receipts: zero-tolerance audit gate — no receipt, no posting.

Together these two engines cover **57.7% of all back-office transaction volume** (161/279).

**3. Full test suite:**

Wrote `tests/test_automation.py`, `tests/test_expense_automation.py`, and `tests/test_ml_segmenter.py`.  
Result: **46/46 Pytest tests passing** — auto-approvals, threshold breach escalations, exception handling, and batch execution all verified.

**4. Risk analysis:**

Built a 6-category risk matrix from evidence observed directly in the telemetry logs:
- Mixed UTF-8/Shift_JIS clipboard encodings (seen in raw events from Word/ERP interactions)
- Session timeout and port reset patterns (`extension_disconnected` events during long idles)
- Operators using Notepad scratchpads for uncatalogued exception procedures
- Potential cumulative price drift below per-transaction thresholds
- Japanese commercial law audit logging requirements
- Change management resistance (personal scratchpads despite portal input fields existing)

Each risk has a concrete, log-grounded mitigation — not generic IT boilerplate.

**5. Final delivery packaging:**

- Verified `segments.jsonl` schema and ISO-8601 UTC timestamps across all 279 segments and 15 sessions.
- Ran full test suite (46/46 passing).
- Cleaned up scripts, documentation, and repo structure.
- Authored `final_report.md` covering the full 8-section technical and operational strategy.

**What didn't work:**

Tried simulating human UI interactions through browser automation scripts for integration testing. Brittle DOM selectors and modal animation timing caused intermittent test failures. Switched to testing the Python backend logic directly via clean REST endpoints — achieved <50ms execution and 100% test reliability with zero UI dependency.

---

## Generative AI Disclosure

In line with the engagement guidelines:

- **Architectural brainstorming:** LLMs helped during Days 2 and 3 to think through heuristic edge cases for human desktop multitasking — rapid alt-tabbing, clipboard content masking, overlapping entity anchors.
- **Japanese text understanding:** LLMs were used to translate and interpret Japanese window titles, form placeholders (such as verification comments, clearing reasons, and vendor requests), and document naming conventions into standardized English process labels.
- **Synthetic test data & mock fixtures:** Used AI assistance to speed up generating repetitive dummy session payloads and JSON serialization boilerplate, while all test assertions, boundary edge cases, and business rule validations were designed and written manually.
- **Production guardrails:** No automation decisions rely on unverified LLM output. All business rule validation and exception routing in the prototype are fully deterministic.
