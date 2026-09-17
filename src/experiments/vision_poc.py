"""
src/experiments/vision_poc.py
------------------------------
Computer Vision Desktop Anomaly Detection Pipeline.

NOTE ON METHODOLOGY & EXECUTION:
The actual computer vision experimentation for this project was conducted in Google Colab
using an Nvidia T4 GPU (documented in `experiments/Colab_vision_boundary.ipynb`) due to the
sheer compute required to process 34,563 1080p full-HD desktop screenshots in Dataset A.

Execution Flow in Colab:
1. Extracted 34,563 screenshots from `dataset_a.zip` to Colab local high-speed disk (`/content/dataset_a`).
2. Vectorized all frames into 1,000-dimensional embeddings using PyTorch `MobileNet_V3_Small`.
3. Experiment 1 (Single-Frame): Consecutive cosine similarity (< 0.85) generated `vision_boundaries.jsonl`
   (9,481 raw state changes).
4. Experiment 2 (Multi-Frame): 4-frame dynamic rolling relational window (drop_tolerance > 0.15) generated
   `vision_boundaries_multiframe.jsonl` (5,894 verified state changes).
5. Conversion: Raw boundary detections were converted via timestamp parsing into:
   - `evaluated_vision_boundaries.jsonl` (from `vision_boundaries.jsonl`)
   - `evaluated_vision_boundaries_multiframe.jsonl` (from `vision_boundaries_multiframe.jsonl`)
   (also mirrored as `evaluated_segments_single.jsonl` and `evaluated_segments_multiframe.jsonl`)
   for ISO-8601 UTC evaluation against Dataset A ground truth using `scripts/evaluate_dataset_a.py`.

This script provides the local reference implementation and CLI utility for reproducing and
inspecting the exact logic executed in the Colab notebook.
"""

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


# -----------------------------------------------------------------------------
# 1. DATASET DEFINITION (Matches Colab_vision_boundary.ipynb Cell 2)
# -----------------------------------------------------------------------------
class ScreenshotDataset(Dataset):
    """Recursively indexes all PNG/JPG files in screenshots/ subdirectories."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.weights = MobileNet_V3_Small_Weights.DEFAULT
        self.preprocess = self.weights.transforms()
        # Recursively find all PNGs/JPGs inside 'screenshots' folders
        self.image_paths = sorted(list(self.root_dir.rglob("screenshots/scr_smart_*.*")))

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int):
        path = self.image_paths[idx]
        img = Image.open(path).convert("RGB")
        return self.preprocess(img), str(path)


# -----------------------------------------------------------------------------
# 2. MODEL INITIALIZATION
# -----------------------------------------------------------------------------
def get_vision_model(device: Optional[torch.device] = None):
    """Initializes lightweight pre-trained MobileNet_V3_Small model."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weights = MobileNet_V3_Small_Weights.DEFAULT
    model = mobilenet_v3_small(weights=weights).to(device)
    model.eval()
    return model, weights.transforms(), device


# Backward-compatible helper for single image embedding
def vectorize_screenshot(image_path: str, model=None, preprocess=None, device=None) -> list:
    """Compresses a raw screenshot into a dense numerical vector (1000-d)."""
    if model is None:
        model, preprocess, device = get_vision_model()
    img = Image.open(image_path).convert("RGB")
    batch = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        vector = model(batch).squeeze().cpu().numpy().tolist()
    return vector


# Backward-compatible helper for two-image boundary comparison
def detect_segment_boundary(img_path_1: str, img_path_2: str, threshold: float = 0.85) -> bool:
    """Evaluates two consecutive frames to detect structural UI changes using cosine similarity."""
    model, preprocess, device = get_vision_model()
    img1 = preprocess(Image.open(img_path_1).convert("RGB")).unsqueeze(0).to(device)
    img2 = preprocess(Image.open(img_path_2).convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        v1 = model(img1)
        v2 = model(img2)
        similarity = F.cosine_similarity(v1, v2).item()
    print(f"Consecutive Frame Similarity: {similarity:.4f}")
    if similarity < threshold:
        print("Action: Significant visual drift detected (Similarity < 0.85). Triggering new segment.")
        return True
    print("Action: Task continuous. Extending current segment.")
    return False


# -----------------------------------------------------------------------------
# 3. EXPERIMENT 1: SINGLE-FRAME CONSECUTIVE COSINE THRESHOLDING (Colab Cell 3)
# -----------------------------------------------------------------------------
def run_single_frame_detection(
    dataset_root: str,
    output_file: str = "experiments/vision_boundaries.jsonl",
    threshold: float = 0.85,
    batch_size: int = 128,
) -> List[Dict]:
    """
    Evaluates adjacent frames (f_t, f_{t+1}) with cosine similarity thresholding.
    Produces vision_boundaries.jsonl (9,481 state changes on Dataset A).
    """
    model, _, device = get_vision_model()
    dataset = ScreenshotDataset(dataset_root)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    previous_vector = None
    segment_boundaries = []

    print(f"[Experiment 1] Found {len(dataset)} screenshots. Running single-frame cosine thresholding...")

    with torch.no_grad():
        for batch_imgs, batch_paths in dataloader:
            batch_imgs = batch_imgs.to(device)
            vectors = model(batch_imgs)

            for i in range(len(vectors)):
                current_vector = vectors[i]
                path = batch_paths[i]

                if previous_vector is not None:
                    similarity = F.cosine_similarity(previous_vector.unsqueeze(0), current_vector.unsqueeze(0)).item()
                    if similarity < threshold:
                        segment_boundaries.append({
                            "boundary_detected_at": path,
                            "similarity_score": round(similarity, 4),
                        })

                previous_vector = current_vector

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for b in segment_boundaries:
            f.write(json.dumps(b) + "\n")

    print(f"[Experiment 1] Complete! Detected {len(segment_boundaries)} state changes -> {output_file}")
    return segment_boundaries


# -----------------------------------------------------------------------------
# 4. EXPERIMENT 2: MULTI-FRAME ROLLING RELATIONAL WINDOW (Colab Cell 4)
# -----------------------------------------------------------------------------
def run_multiframe_rolling_window(
    dataset_root: str,
    output_file: str = "experiments/vision_boundaries_multiframe.jsonl",
    drop_tolerance: float = 0.15,
    batch_size: int = 128,
) -> List[Dict]:
    """
    Evaluates a 4-frame dynamic FIFO buffer (f1, f2, f3, f4).
    Calculates drop relative to surrounding visual stability plateaus:
      Drop Magnitude = ((sim_before + sim_after) / 2) - sim_transition
    Produces vision_boundaries_multiframe.jsonl (5,894 verified state changes on Dataset A).
    """
    model, _, device = get_vision_model()
    dataset = ScreenshotDataset(dataset_root)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    window = deque(maxlen=4)
    segment_boundaries = []

    print(f"[Experiment 2] Found {len(dataset)} screenshots. Running 4-frame dynamic rolling window...")

    with torch.no_grad():
        for batch_imgs, batch_paths in dataloader:
            batch_imgs = batch_imgs.to(device)
            vectors = model(batch_imgs)

            for i in range(len(vectors)):
                current_vector = vectors[i]
                path = batch_paths[i]

                window.append((current_vector, path))

                if len(window) == 4:
                    v1, p1 = window[0]
                    v2, p2 = window[1]
                    v3, p3 = window[2]
                    v4, p4 = window[3]

                    sim_before = F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
                    sim_transition = F.cosine_similarity(v2.unsqueeze(0), v3.unsqueeze(0)).item()
                    sim_after = F.cosine_similarity(v3.unsqueeze(0), v4.unsqueeze(0)).item()

                    avg_stability = (sim_before + sim_after) / 2
                    drop_magnitude = avg_stability - sim_transition

                    if drop_magnitude > drop_tolerance:
                        segment_boundaries.append({
                            "boundary_detected_at": p3,
                            "drop_magnitude": round(drop_magnitude, 4),
                            "transition_similarity": round(sim_transition, 4),
                            "stability_before": round(sim_before, 4),
                            "stability_after": round(sim_after, 4),
                        })

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for b in segment_boundaries:
            f.write(json.dumps(b) + "\n")

    print(f"[Experiment 2] Complete! Detected {len(segment_boundaries)} verified state changes -> {output_file}")
    return segment_boundaries


# -----------------------------------------------------------------------------
# 5. BOUNDARY CONVERSION TO ISO-8601 UTC EVALUATION SEGMENTS
# -----------------------------------------------------------------------------
def convert_boundaries_to_segments(input_jsonl: str, output_jsonl: str) -> int:
    """
    Converts raw vision boundary detections into start/end ISO-8601 UTC session segments
    compatible with scripts/evaluate_dataset_a.py.
    """
    sessions = {}

    with open(input_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            path_str = data["boundary_detected_at"]
            path = PurePosixPath(path_str)

            # Extract session_id
            session_id = None
            for parent in path.parents:
                if parent.name.startswith("ses_"):
                    session_id = parent.name
                    break
            if not session_id:
                session_id = "default_session"

            # Extract millisecond timestamp from filename (scr_smart_<ts>_monitor_1_post.jpg)
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
                "label": "Automated Vision Segment",
            })

    out_p = Path(output_jsonl)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as out_f:
        for seg in segment_records:
            out_f.write(json.dumps(seg) + "\n")

    print(f"Converted {len(segment_records)} valid segments across {len(sessions)} sessions into {output_jsonl}")
    return len(segment_records)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Frame Context-Aware Computer Vision PoC")
    parser.add_argument("--mode", choices=["single", "multiframe", "convert"], default="multiframe", help="Pipeline execution mode")
    parser.add_argument("--dataset-dir", default="dataset_a", help="Dataset directory containing screenshots")
    parser.add_argument("--input", default="experiments/vision_boundaries_multiframe.jsonl", help="Input boundaries file for conversion (e.g. experiments/vision_boundaries.jsonl or experiments/vision_boundaries_multiframe.jsonl)")
    parser.add_argument("--output", default="experiments/evaluated_vision_boundaries_multiframe.jsonl", help="Output evaluation segments JSONL file (e.g. experiments/evaluated_vision_boundaries_multiframe.jsonl or experiments/evaluated_segments_multiframe.jsonl)")
    args = parser.parse_args()

    if args.mode == "single":
        run_single_frame_detection(args.dataset_dir, output_file=args.output)
    elif args.mode == "multiframe":
        run_multiframe_rolling_window(args.dataset_dir, output_file=args.output)
    elif args.mode == "convert":
        convert_boundaries_to_segments(args.input, args.output)
