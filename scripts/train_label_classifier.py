"""
Train Calibrated Semantic Label Classifier for PC Operation Telemetry.

Extracts rich context features (Window Titles, URL routes, Port numbers, and OCR text)
from all 2,009 ground truth executions in Dataset A, and trains a TF-IDF +
Calibrated Classifier to accurately predict the standardized 2-3 word English process label.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pickle
import numpy as np
from datetime import datetime, timezone
from collections import Counter
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from src.pipeline.loader import load_session_events, load_ground_truth_manifest


# Ground Truth Process Code to Standard English Label mapping
CODE_TO_LABEL = {
    "A": "resident_tax_verification",
    "B": "payroll_adjustment",
    "C": "leave_application_processing",
    "D": "insurance_pension_processing",
    "E": "onboarding_verification",
    "F": "invoice_approval",
    "G": "expense_processing",
    "H": "bank_reconciliation",
    "I": "budget_variance_analysis",
    "J": "payment_processing",
    "K": "order_processing",
    "L": "inventory_adjustment",
    "M": "supplier_communication",
    "N": "shipment_tracking",
    "O": "return_processing",
}


def extract_execution_context(events: List[Dict[str, Any]], start_ms: int, end_ms: int) -> str:
    """Extract aggregated text and structural markers for a segment window."""
    seg_events = [e for e in events if start_ms <= e.get("timestamp_ms", 0) <= end_ms]
    if not seg_events:
        return ""

    tokens = []
    for e in seg_events:
        ctx = e.get("context") or {}
        # Port detection
        url = (ctx.get("active_browser_tab") or {}).get("url") or ""
        if ":5122" in url:
            tokens.append("SYS_HR_5122")
        elif ":5123" in url:
            tokens.append("SYS_FIN_5123")
        elif ":5124" in url:
            tokens.append("SYS_OPS_5124")
        elif ":5132" in url:
            tokens.append("SYS_HR_5132")
        elif ":5133" in url:
            tokens.append("SYS_FIN_5133")
        elif ":5134" in url:
            tokens.append("SYS_OPS_5134")

        # URL path / hash
        if "#" in url:
            tokens.append("ROUTE_" + url.split("#")[-1].replace("/", "_"))

        # Window title
        active_app = ctx.get("active_app") or {}
        title = active_app.get("window_title") or ""
        if title:
            tokens.append(title)

        # Extracted OCR text
        ocr = ctx.get("extracted_text") or ""
        if isinstance(ocr, str) and ocr:
            tokens.append(ocr[:100])
        elif isinstance(ocr, list):
            for item in ocr[:3]:
                if isinstance(item, str):
                    tokens.append(item)
                elif isinstance(item, dict) and item.get("text"):
                    tokens.append(item["text"])

        # Clipboard content
        pl = e.get("payload") or {}
        clip = pl.get("text_content") or ""
        if clip:
            tokens.append("CLIP_" + clip[:50])

        # Target element / Form interaction text
        te = pl.get("target_element") or {}
        elem = pl.get("element") or {}
        attrs = elem.get("attributes") or {}
        elem_txt = (
            te.get("name")
            or elem.get("text")
            or attrs.get("innerText")
            or attrs.get("placeholder")
            or attrs.get("value")
            or ""
        )
        if elem_txt and isinstance(elem_txt, str) and len(elem_txt.strip()) > 1:
            tokens.append(elem_txt.strip()[:100])

    return " ".join(tokens)


def build_training_data(dataset_dir: Path) -> Tuple[List[str], List[str]]:
    session_dirs = sorted([p for p in dataset_dir.glob("ses_*") if p.is_dir()])
    print(f"Extracting task context across {len(session_dirs)} sessions...")

    texts = []
    labels = []

    for idx, s_dir in enumerate(session_dirs, 1):
        manifest = load_ground_truth_manifest(s_dir)
        if not manifest:
            continue
        events = load_session_events(s_dir)
        if not events:
            continue

        for proc in manifest.get("processes", []):
            code = proc["code"]
            label = CODE_TO_LABEL.get(code)
            if not label:
                continue

            for exc in proc.get("executions", []):
                start_str = exc.get("start_ts")
                end_str = exc.get("end_ts")
                if not start_str or not end_str:
                    continue

                st_ms = int(datetime.fromisoformat(start_str).timestamp() * 1000)
                et_ms = int(datetime.fromisoformat(end_str).timestamp() * 1000)

                doc = extract_execution_context(events, st_ms, et_ms)
                if doc:
                    texts.append(doc)
                    labels.append(label)

        if idx % 20 == 0 or idx == len(session_dirs):
            print(f"  Processed [{idx}/{len(session_dirs)}] sessions ({len(texts)} executions extracted)...")

    return texts, labels


def train_model(texts: List[str], labels: List[str], output_path: Path):
    print(f"\nTotal labeled execution instances: {len(labels)}")
    counts = Counter(labels)
    for lbl, cnt in counts.most_common():
        print(f"  {cnt:3d} : {lbl}")

    # Build Pipeline: TF-IDF + LogisticRegression
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="char_wb",
            max_features=5000,
            min_df=2,
        )),
        ("clf", LogisticRegression(
            C=5.0,
            max_iter=500,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    split_idx = int(len(texts) * 0.8)
    train_texts, val_texts = texts[:split_idx], texts[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]

    print("\nFitting TF-IDF + Logistic Regression...")
    pipeline.fit(train_texts, train_labels)

    val_preds = pipeline.predict(val_texts)
    print("\n=== Validation Classification Report ===")
    print(classification_report(val_labels, val_preds, digits=3))

    # Refit on 100% of data for production
    print("Refitting on full dataset for maximum generalization...")
    pipeline.fit(texts, labels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pipeline": pipeline,
        "classes": pipeline.classes_.tolist(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(output_path, "wb") as f:
        pickle.dump(payload, f)
    print(f"Model saved to: {output_path}")


def main():
    root = Path(__file__).resolve().parents[1]
    dataset_dir = root / "dataset_a"
    model_output = root / "src" / "segmentation" / "label_model.pkl"

    texts, labels = build_training_data(dataset_dir)
    train_model(texts, labels, model_output)


if __name__ == "__main__":
    main()
