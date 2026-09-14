"""
Train Domain-Agnostic Boundary Classifier for PC Operation Telemetry.

Extracts tabular temporal, interaction, and state-change features from Dataset A
and trains a fast HistGradientBoostingClassifier against true boundaries
from gt_manifest.json.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
import bisect
import pickle
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score
from src.pipeline.loader import load_session_events, load_ground_truth_manifest
from scripts.evaluate_dataset_a import extract_true_boundaries


FEATURE_NAMES = [
    "dt_prev_ms",
    "dt_next_ms",
    "is_app_switch",
    "is_clipboard_change",
    "is_browser_nav",
    "is_shortcut",
    "is_click",
    "clipboard_len",
    "clipboard_delta",
    "has_id_code",
    "url_is_hub",
    "url_depth",
    "app_category",
    "app_category_changed",
    "window_title_len",
    "window_title_changed",
    "idle_gt_10s",
    "idle_gt_30s",
]


def get_app_category(app_name: str) -> int:
    name = (app_name or "").lower()
    if "chrome" in name or "edge" in name or "browser" in name:
        return 1
    if "excel" in name or "calc" in name:
        return 2
    if "word" in name or "doc" in name:
        return 3
    if "notepad" in name or "memo" in name:
        return 4
    return 0


def is_hub_url(url: str) -> bool:
    if not url:
        return False
    clean = url.split("?")[0].rstrip("/")
    if any(clean.endswith(h) for h in ["/dashboard", "/index", "/home", ":5122", ":5123", ":5124", ":5132", ":5133", ":5134"]):
        return True
    return False


def extract_features_from_session(events: List[Dict[str, Any]]) -> np.ndarray:
    """Extract tabular feature matrix X for all events in a session."""
    n = len(events)
    X = np.zeros((n, len(FEATURE_NAMES)), dtype=np.float32)

    prev_clip_len = 0
    prev_app_cat = 0
    prev_title = ""

    id_regex = re.compile(r"[A-Za-z0-9_-]{4,}")

    for i in range(n):
        ev = events[i]
        ev_type = ev.get("event_type", "")
        t = ev.get("timestamp_ms", 0)

        # 1. Temporal deltas
        dt_prev = ev.get("correlation", {}).get("ms_since_last_event", 0)
        if dt_prev is None or dt_prev < 0:
            dt_prev = (t - events[i - 1].get("timestamp_ms", t)) if i > 0 else 0
        dt_prev = min(float(dt_prev), 60000.0)

        dt_next = (events[i + 1].get("timestamp_ms", t) - t) if i < n - 1 else 0
        dt_next = min(max(float(dt_next), 0.0), 60000.0)

        # 2. Event type indicators
        is_app_sw = 1.0 if ev_type == "app_switch" else 0.0
        is_clip = 1.0 if ev_type == "clipboard_change" else 0.0
        is_nav = 1.0 if ev_type == "browser_navigation" else 0.0
        is_short = 1.0 if ev_type == "shortcut" else 0.0
        is_clk = 1.0 if "click" in ev_type else 0.0

        # 3. Clipboard dynamics
        clip_content = (ev.get("payload") or {}).get("text_content") or ""
        clip_len = len(clip_content)
        clip_delta = abs(clip_len - prev_clip_len) if is_clip else 0.0
        has_id = 1.0 if (clip_content and bool(id_regex.search(clip_content))) else 0.0
        if is_clip:
            prev_clip_len = clip_len

        # 4. URL topology
        ctx = ev.get("context") or {}
        active_tab = ctx.get("active_browser_tab") or {}
        url = active_tab.get("url") or ""
        hub = 1.0 if is_hub_url(url) else 0.0
        url_depth = float(url.count("/")) if url else 0.0

        # 5. App & Title dynamics
        active_app = ctx.get("active_app") or {}
        app_name = active_app.get("app_name") or active_app.get("process_name") or ""
        app_cat = get_app_category(app_name)
        app_changed = 1.0 if (app_cat != prev_app_cat and i > 0) else 0.0
        prev_app_cat = app_cat

        title = active_app.get("window_title") or ""
        title_len = float(len(title))
        title_changed = 1.0 if (title != prev_title and i > 0) else 0.0
        prev_title = title

        # 6. Idle thresholds
        idle_10 = 1.0 if dt_prev >= 10000.0 else 0.0
        idle_30 = 1.0 if dt_prev >= 30000.0 else 0.0

        X[i] = [
            dt_prev,
            dt_next,
            is_app_sw,
            is_clip,
            is_nav,
            is_short,
            is_clk,
            float(clip_len),
            float(clip_delta),
            has_id,
            hub,
            url_depth,
            float(app_cat),
            app_changed,
            title_len,
            title_changed,
            idle_10,
            idle_30,
        ]

    return X


def build_dataset(dataset_dir: Path, tolerance_ms: int = 3500) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    session_dirs = sorted([p for p in dataset_dir.glob("ses_*") if p.is_dir()])
    print(f"Building dataset from {len(session_dirs)} sessions in {dataset_dir}...")

    all_X = []
    all_y = []
    session_ids = []

    for idx, s_dir in enumerate(session_dirs, 1):
        manifest = load_ground_truth_manifest(s_dir)
        if not manifest:
            continue
        events = load_session_events(s_dir)
        if not events:
            continue

        boundaries = extract_true_boundaries(manifest)
        b_times = sorted([b["ts_ms"] for b in boundaries])

        X_sess = extract_features_from_session(events)
        y_sess = np.zeros(len(events), dtype=np.int32)

        # Align ground truth boundaries with bisect
        for i, ev in enumerate(events):
            t = ev.get("timestamp_ms", 0)
            # Find closest boundary
            pos = bisect.bisect_left(b_times, t)
            candidates = []
            if pos < len(b_times):
                candidates.append(abs(b_times[pos] - t))
            if pos > 0:
                candidates.append(abs(b_times[pos - 1] - t))
            if candidates and min(candidates) <= tolerance_ms:
                y_sess[i] = 1

        all_X.append(X_sess)
        all_y.append(y_sess)
        session_ids.extend([s_dir.name] * len(events))

        if idx % 15 == 0 or idx == len(session_dirs):
            print(f"  Processed [{idx}/{len(session_dirs)}] sessions...")

    X = np.vstack(all_X)
    y = np.concatenate(all_y)
    return X, y, session_ids


def train_and_evaluate(X: np.ndarray, y: np.ndarray, output_path: Path):
    print(f"\nTotal Event Samples: {len(y):,}")
    print(f"Positive Boundary Samples: {np.sum(y):,} ({np.mean(y)*100:.2f}%)")

    # 80/20 train/test split by chronological session ordering
    split_idx = int(len(y) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    print("Training HistGradientBoostingClassifier...")
    clf = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_train)

    val_probs = clf.predict_proba(X_val)[:, 1]
    roc_auc = roc_auc_score(y_val, val_probs)
    pr_auc = average_precision_score(y_val, val_probs)

    print(f"\n=== Validation Performance ===")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"PR-AUC:  {pr_auc:.4f} (Baseline prevalence: {np.mean(y_val):.4f})")

    # Save model and metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": clf,
        "feature_names": FEATURE_NAMES,
        "optimal_threshold": 0.55,
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "validation_metrics": {"roc_auc": roc_auc, "pr_auc": pr_auc},
    }
    with open(output_path, "wb") as f:
        pickle.dump(payload, f)
    print(f"\nModel successfully saved to: {output_path}")


def main():
    root = Path(__file__).resolve().parents[1]
    dataset_dir = root / "dataset_a"
    model_output = root / "src" / "segmentation" / "boundary_model.pkl"

    X, y, _ = build_dataset(dataset_dir)
    train_and_evaluate(X, y, model_output)


if __name__ == "__main__":
    main()
