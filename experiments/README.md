# Computer Vision Desktop Anomaly Detection Pipeline
### Offline Batch Processing on Google Colab (T4 GPU) with MobileNet_V3_Small

This directory contains the computer vision research pipeline engineered to detect **silent visual UI state transitions** across desktop workstation telemetry without incurring commercial Vision API costs.

---

## 📋 Background & Motivation

While text- and event-based telemetry captures keystrokes and window focus changes, it misses **silent UI state transitions**:
- Asynchronous data tables re-rendering in the background.
- Modal dialogs, confirmation popups, and error alert banners appearing without keystroke events.
- In-place tab changes within complex single-page applications (SPAs).

To bridge this gap across **34,563 1080p desktop screenshots** in Dataset A, we engineered an offline computer vision feature extraction and anomaly detection pipeline executed on **Google Colab (T4 GPU)**.

---

## 🛠️ End-to-End Workflow

```
1. Zip Dataset A Screenshots
   (Local machine: zip -r dataset_a.zip dataset_a/)
          │
          ▼
2. Upload to Google Drive
   (/content/drive/MyDrive/dataset_a.zip)
          │
          ▼
3. Execute Colab Notebook (experiments/Colab_vision_boundary.ipynb)
   - Mount Google Drive & unzip dataset to Colab local fast disk (/content/dataset_a)
   - Initialize PyTorch MobileNet_V3_Small on CUDA GPU (Nvidia T4)
   - Batch vectorize 34,563 screenshots into 1,000-dimensional semantic embeddings
   - Compute pairwise cosine similarity & 4-frame dynamic rolling window anomaly detection
          │
          ▼
4. Export Detected Boundaries to Google Drive
   - Single-Frame naive thresholding: vision_boundaries.jsonl (9,481 state changes)
   - Multi-Frame context-aware rolling window: vision_boundaries_multiframe.jsonl (5,894 state changes)
          │
          ▼
5. Download Boundary Files Locally to experiments/
   - experiments/vision_boundaries.jsonl
   - experiments/vision_boundaries_multiframe.jsonl
          │
          ▼
6. Convert Boundaries into ISO-8601 UTC Session Segments
   (python experiments/convert_vision_boundaries.py)
   → Generates:
     - experiments/evaluated_vision_boundaries.jsonl (single-frame)
     - experiments/evaluated_vision_boundaries_multiframe.jsonl (multi-frame)
          │
          ▼
7. Evaluate Against Dataset A Ground Truth
   (python scripts/evaluate_dataset_a.py --predictions experiments/evaluated_vision_boundaries_multiframe.jsonl)
```

---

## 📁 Directory Structure & File Inventory

| File | Type | Description |
| :--- | :---: | :--- |
| [`Colab_vision_boundary.ipynb`](file:///c:/IBY_Japan/experiments/Colab_vision_boundary.ipynb) | Jupyter Notebook | Complete Google Colab notebook executed on Nvidia T4 GPU with full cell outputs, logging the processing of 34,563 screenshots, single-frame cosine thresholding, and multi-frame anomaly detection. |
| [`colab_notebook.ipynb`](file:///c:/IBY_Japan/experiments/colab_notebook.ipynb) | Jupyter Notebook | Standalone portable Colab template for isolated single-cell execution. |
| [`vision_boundaries.jsonl`](file:///c:/IBY_Japan/experiments/vision_boundaries.jsonl) | JSONL Data | Raw single-frame boundary detections exported from Colab (9,481 state changes). |
| [`vision_boundaries_multiframe.jsonl`](file:///c:/IBY_Japan/experiments/vision_boundaries_multiframe.jsonl) | JSONL Data | Raw multi-frame anomaly detections exported from Colab (5,894 verified state changes). |
| [`convert_vision_boundaries.py`](file:///c:/IBY_Japan/experiments/convert_vision_boundaries.py) | Python Script | Parses screenshot timestamps from boundary detections and formats consecutive timestamps into start/end ISO-8601 UTC session segments. |
| [`evaluated_vision_boundaries.jsonl`](file:///c:/IBY_Japan/experiments/evaluated_vision_boundaries.jsonl) | JSONL Deliverable | Converted single-frame vision segment records (also mirrored as `evaluated_segments_single.jsonl`). |
| [`evaluated_vision_boundaries_multiframe.jsonl`](file:///c:/IBY_Japan/experiments/evaluated_vision_boundaries_multiframe.jsonl) | JSONL Deliverable | Converted 4-frame rolling window segment records (also mirrored as `evaluated_segments_multiframe.jsonl`). |
| [`src/experiments/vision_poc.py`](file:///c:/IBY_Japan/src/experiments/vision_poc.py) | Python Script | Modular local reference implementation and CLI replicating the Colab pipeline logic. |

---

## 🔬 Algorithms: Single-Frame vs. Multi-Frame Rolling Window

### 1. Single-Frame Naive Cosine Thresholding
* **Logic:** Evaluates consecutive frames $(f_t, f_{t+1})$ and flags a boundary when $\text{Cosine Similarity} < 0.85$.
* **Output:** `experiments/vision_boundaries.jsonl` $\to$ converted to `experiments/evaluated_vision_boundaries.jsonl`.
* **Limitation:** High recall (63.8%), but excessive false-positive cuts (9,481 segments vs. 2,009 ground truth executions) caused by micro-visual noise (blinking cursor, hover tooltips, scrollbar shifts).

### 2. Multi-Frame Context-Aware Rolling Window
* **Logic:** Maintains a 4-frame FIFO buffer ($f_1, f_2, f_3, f_4$) to compute relational divergence:

$$
\text{Drop Magnitude} = \frac{\text{Similarity}(f_1, f_2) + \text{Similarity}(f_3, f_4)}{2} - \text{Similarity}(f_2, f_3)
$$

* **Output:** `experiments/vision_boundaries_multiframe.jsonl` $\to$ converted to `experiments/evaluated_vision_boundaries_multiframe.jsonl`.
* **Advantage:** Triggers a boundary only when a sharp state transition occurs between two visually stable plateaus ($\text{Drop Magnitude} > 0.15$), filtering out transient visual flickers.
* **Impact:** Eliminated **3,587 false-positive jitter cuts** (-38.1%) and doubled Segment IoU F1 from 7.3% to **15.7%**.

---

## 🚀 Execution Commands

```powershell
# Step 1: Convert raw vision boundaries into evaluated ISO-8601 segments
python experiments/convert_vision_boundaries.py `
    --input experiments/vision_boundaries_multiframe.jsonl `
    --output experiments/evaluated_vision_boundaries_multiframe.jsonl

# Step 2: Evaluate vision segments against Dataset A ground truth
python scripts/evaluate_dataset_a.py `
    --predictions experiments/evaluated_vision_boundaries_multiframe.jsonl `
    --dataset-dir dataset_a
```
