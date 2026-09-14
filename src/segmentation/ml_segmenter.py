"""
ML Golden Thread Segmenter (Phase 3+ Machine Learning Enhancement).

Combines:
1. HistGradientBoostingClassifier trained on 18 tabular temporal & interaction
   features to pinpoint task transition boundaries.
2. Calibrated TF-IDF + LogisticRegression semantic classifier trained on portal ports,
   window titles, route tokens, and Japanese UI elements to predict standardized labels.
3. Idle suppression and semantic merging post-processor to ensure coherent segments.
"""

from __future__ import annotations

import os
import re
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

from src.segmentation.segmenter import (
    Segment,
    merge_segments,
    GoldenThreadSegmenter,
    MIN_SEGMENT_MS,
    IDLE_TIMEOUT_MS,
)


FEATURE_NAMES = [
    "dt_prev",
    "dt_next",
    "is_app_sw",
    "is_clip",
    "is_nav",
    "is_short",
    "is_clk",
    "clip_len",
    "clip_delta",
    "has_id",
    "hub",
    "url_depth",
    "app_cat",
    "app_changed",
    "title_len",
    "title_changed",
    "idle_10",
    "idle_30",
]


def get_app_category(app_name: str) -> int:
    name = (app_name or "").lower()
    if "chrome" in name:
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
    if n == 0:
        return X

    prev_clip_len = 0
    prev_app_cat = 0
    prev_title = ""
    id_regex = re.compile(r"[A-Za-z0-9_-]{4,}")

    for i in range(n):
        ev = events[i]
        ev_type = ev.get("event_type", "")
        t = ev.get("timestamp_ms", 0)

        dt_prev = ev.get("correlation", {}).get("ms_since_last_event", 0)
        if dt_prev is None or dt_prev < 0:
            dt_prev = (t - events[i - 1].get("timestamp_ms", t)) if i > 0 else 0
        dt_prev = min(float(dt_prev), 60000.0)

        dt_next = (events[i + 1].get("timestamp_ms", t) - t) if i < n - 1 else 0
        dt_next = min(max(float(dt_next), 0.0), 60000.0)

        is_app_sw = 1.0 if ev_type == "app_switch" else 0.0
        is_clip = 1.0 if ev_type == "clipboard_change" else 0.0
        is_nav = 1.0 if ev_type == "browser_navigation" else 0.0
        is_short = 1.0 if ev_type == "shortcut" else 0.0
        is_clk = 1.0 if "click" in ev_type else 0.0

        clip_content = (ev.get("payload") or {}).get("text_content") or ""
        clip_len = len(clip_content)
        clip_delta = abs(clip_len - prev_clip_len) if is_clip else 0.0
        has_id = 1.0 if (clip_content and bool(id_regex.search(clip_content))) else 0.0
        if is_clip:
            prev_clip_len = clip_len

        ctx = ev.get("context") or {}
        active_tab = ctx.get("active_browser_tab") or {}
        url = active_tab.get("url") or ""
        hub = 1.0 if is_hub_url(url) else 0.0
        url_depth = float(url.count("/")) if url else 0.0

        active_app = ctx.get("active_app") or {}
        app_name = active_app.get("app_name") or active_app.get("process_name") or ""
        app_cat = get_app_category(app_name)
        app_changed = 1.0 if (app_cat != prev_app_cat and i > 0) else 0.0
        prev_app_cat = app_cat

        title = active_app.get("window_title") or ""
        title_len = float(len(title))
        title_changed = 1.0 if (title != prev_title and i > 0) else 0.0
        prev_title = title

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


class MLGoldenThreadSegmenter:
    """Two-Stage Machine Learning Process Segmenter."""

    def __init__(
        self,
        session_id: str,
        idle_timeout_ms: int = IDLE_TIMEOUT_MS,
        min_segment_ms: int = MIN_SEGMENT_MS,
        boundary_model_path: Optional[Union[str, Path]] = None,
        label_model_path: Optional[Union[str, Path]] = None,
        boundary_threshold: float = 0.50,
        refractory_gap_ms: int = 12000,
    ) -> None:
        self.session_id = session_id
        self.idle_timeout_ms = idle_timeout_ms
        self.min_segment_ms = min_segment_ms
        self.boundary_threshold = boundary_threshold
        self.refractory_gap_ms = refractory_gap_ms

        base_dir = Path(__file__).resolve().parent
        self.b_path = Path(boundary_model_path) if boundary_model_path else base_dir / "boundary_model.pkl"
        self.l_path = Path(label_model_path) if label_model_path else base_dir / "label_model.pkl"

        self.boundary_model = None
        self.label_model = None

        self._load_models()

    def _load_models(self) -> None:
        try:
            if self.b_path.exists():
                with open(self.b_path, "rb") as f:
                    bm_payload = pickle.load(f)
                    self.boundary_model = bm_payload.get("model")
            if self.l_path.exists():
                with open(self.l_path, "rb") as f:
                    lm_payload = pickle.load(f)
                    self.label_model = lm_payload.get("pipeline")
        except Exception:
            self.boundary_model = None
            self.label_model = None

    def segment(self, events: List[Dict[str, Any]]) -> Iterator[Segment]:
        """Segment an event list; yields Segment objects in chronological order."""
        if not events:
            return

        # Fallback to heuristic Golden Thread if ML models are not available
        if self.boundary_model is None or self.label_model is None:
            fallback = GoldenThreadSegmenter(
                session_id=self.session_id,
                idle_timeout_ms=self.idle_timeout_ms,
                min_segment_ms=self.min_segment_ms,
            )
            yield from fallback.segment(events)
            return

        # Extract features and predict boundary probabilities
        X = extract_features_from_session(events)
        probs = self.boundary_model.predict_proba(X)[:, 1]

        t_list = [e.get("timestamp_ms", 0) for e in events]
        n_events = len(events)

        # 1. Candidate boundary peak extraction with refractory window
        peaks = []
        for i in range(n_events):
            if probs[i] >= self.boundary_threshold:
                t = t_list[i]
                if not peaks or (t - peaks[-1]["t"]) >= self.refractory_gap_ms:
                    peaks.append({"t": t, "p": probs[i], "idx": i})
                elif probs[i] > peaks[-1]["p"]:
                    peaks[-1] = {"t": t, "p": probs[i], "idx": i}

        # Add session start and end boundaries to encompass full timeline
        raw_cuts = [p["t"] for p in peaks]
        cuts = [t_list[0]]
        for ct in raw_cuts:
            if (ct - cuts[-1]) >= self.min_segment_ms:
                cuts.append(ct)
        if (t_list[-1] - cuts[-1]) >= self.min_segment_ms:
            cuts.append(t_list[-1])
        elif len(cuts) > 1:
            cuts[-1] = t_list[-1]
        else:
            cuts.append(t_list[-1])

        # 2. Candidate segment formation with idle suppression
        raw_segments: List[Segment] = []
        for j in range(len(cuts) - 1):
            c_start = cuts[j]
            c_end = cuts[j + 1]
            dur_ms = c_end - c_start
            if dur_ms < self.min_segment_ms:
                continue

            seg_ev = [e for e in events if c_start <= e.get("timestamp_ms", 0) <= c_end]
            dur_s = dur_ms / 1000.0

            # Suppress idle / break periods (e.g. coffee breaks, prolonged inactivity)
            if len(seg_ev) < 10 and dur_s > 15.0:
                continue

            # Extract context text & classify
            ctx_doc = extract_execution_context(events, c_start, c_end)
            if ctx_doc:
                lbl = self.label_model.predict([ctx_doc])[0]
            else:
                lbl = "process_unknown"

            # Gather metadata
            w_titles = set()
            urls = set()
            ex_texts = []
            apps = set()
            anchors = []

            for ev in seg_ev:
                ctx = ev.get("context") or {}
                app = (ctx.get("active_app") or {}).get("app_name") or ""
                if app:
                    apps.add(app)
                wt = (ctx.get("active_app") or {}).get("window_title") or ""
                if wt:
                    w_titles.add(wt)
                u = (ctx.get("active_browser_tab") or {}).get("url") or ""
                if u:
                    urls.add(u)
                et = ctx.get("extracted_text") or ""
                if isinstance(et, str) and et.strip():
                    ex_texts.append(et.strip()[:100])
                anc = (ev.get("payload") or {}).get("text_content") or ""
                if anc:
                    anchors.append(anc)

            seg = Segment(
                session_id=self.session_id,
                start_ms=c_start,
                end_ms=c_end,
                label=lbl,
                event_count=len(seg_ev),
                window_titles=sorted(w_titles),
                urls=sorted(urls),
                extracted_texts=ex_texts[:10],
                apps_seen=sorted(apps),
                anchor_texts=anchors,
            )
            raw_segments.append(seg)

        # 3. Post-processing: Semantic Merging
        merged_segments = merge_segments(raw_segments, max_gap_ms=35000)
        yield from merged_segments
