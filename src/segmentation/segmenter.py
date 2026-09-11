"""Entity-Centric Golden Thread Segmenter.

Phase 3 Deliverable:
Segment continuous PC operation logs into discrete business process executions
using an Entity-Centric Golden Thread state machine.

Algorithm Workflow
------------------
1. Filter Noise (State Construction):
   - Discard high-frequency noise: mouse_scroll, mouse_click (unless interacting
     with a submit/confirm button), and raw keystrokes (except recognized shortcuts
     like Ctrl+C / Ctrl+V).
   - Keep state-changing events: app_switch, clipboard_change, browser_navigation,
     and window_title_change (plus shortcuts, window_state_change, dialogs).

2. The Golden Thread State Machine:
   - The Anchor: When a clipboard_change event occurs, capture the payload
     as the active Entity_Anchor (using text_content or text_length fingerprint
     when masked for privacy).
   - The Thread: As the user switches applications (app_switch) or navigates
     (browser_navigation), append events to the current Active Segment as long
     as the task remains in focus.
   - Boundary Detection: Close the current segment and yield it if:
       a) The user returns to a "Hub" (URLs ending in /dashboard, /index, or root).
       b) A completely new Entity_Anchor is copied (switch to a new case/task).
       c) A prolonged period of inactivity occurs (e.g. > 60 seconds).
       d) The portal system itself changes (e.g., HR -> Finance).

3. LLM-Assisted Labeling (Preparation):
   - Extract unique Window Titles, URLs, and Japanese extracted_text from events.
   - generate_segment_label(segment_context) provides a mock fallback returning
     'process_unknown', with an interface ready for LLM API integration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from src.segmentation.llm_labeler import predict_label

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

# Inactivity threshold: close active segment if no event for > 60 seconds
IDLE_TIMEOUT_MS: int = 60_000

# Minimum duration to consider an event group a valid process execution
MIN_SEGMENT_MS: int = 8_000

# High-frequency or non-state-changing event types to drop
_DROPPED_TYPES: frozenset = frozenset(
    {
        "mouse_scroll",
        "screenshot_smart",
        "session_start",
        "session_end",
        "upload_started",
        "upload_completed",
        "upload_failed",
        "extension_connected",
        "extension_disconnected",
        "keystroke",  # handled specifically to preserve shortcuts
    }
)

# Known portal system window-title substrings (Dataset A)
_PORTAL_SYSTEMS: Tuple[str, ...] = (
    "HR人事給与システム",
    "財務会計システム",
    "受発注在庫管理システム",
)

# URL pattern that represents the portal hub / index root
_HUB_URL_RE = re.compile(r"^https?://[^/]+/?(?:#/?)?$")

# Keywords for detecting submit / confirm button interactions
_SUBMIT_CONFIRM_KEYWORDS: Tuple[str, ...] = (
    "submit", "confirm", "save", "apply", "ok", "execute", "next", "search",
    "update", "done", "complete", "register", "send",
    "登録", "確定", "保存", "送信", "実行", "次へ", "検索", "更新", "決定",
    "完了", "承認", "申請", "作成", "閉じる"
)

# Apps considered "non-Chrome" work apps (user left portal to work in external tool)
_WORK_APPS: frozenset = frozenset(
    {
        "Microsoft Excel",
        "excel",
        "Notepad",
        "notepad",
        "Microsoft Word",
        "word",
        "Microsoft Teams",
        "teams",
        "OneNote",
        "onenote",
        "Outlook",
        "outlook",
        "olk",
        "File Explorer",
        "Windows Explorer",
        "explorer",
    }
)


# ──────────────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Segment:
    """A completed business-process segment."""

    session_id: str
    start_ms: int
    end_ms: int
    label: str
    event_count: int = 0
    # Rich context for labeling / auditing
    window_titles: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    extracted_texts: List[str] = field(default_factory=list)
    apps_seen: List[str] = field(default_factory=list)
    anchor_texts: List[str] = field(default_factory=list)

    @property
    def start_iso(self) -> str:
        dt = datetime.fromtimestamp(self.start_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def end_iso(self) -> str:
        dt = datetime.fromtimestamp(self.end_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def duration_s(self) -> float:
        return (self.end_ms - self.start_ms) / 1000.0

    def to_deliverable(self) -> Dict[str, str]:
        """Convert to the standard deliverable JSON schema."""
        return {
            "session_id": self.session_id,
            "start": self.start_iso,
            "end": self.end_iso,
            "label": self.label,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Filter the Noise (State Construction)
# ──────────────────────────────────────────────────────────────────────────────


def _is_submit_or_confirm_click(ev: Dict[str, Any]) -> bool:
    """Return True if mouse click interacts with a submit, confirm, or save button."""
    pl = ev.get("payload") or {}
    te = pl.get("target_element") or {}
    name = str(te.get("name") or "").lower()
    auto_id = str(te.get("automation_id") or "").lower()

    elem = pl.get("element") or {}
    attrs = elem.get("attributes") or {}
    elem_text = str(
        attrs.get("text")
        or attrs.get("innerText")
        or attrs.get("value")
        or elem.get("text")
        or ""
    ).lower()
    elem_id = str(attrs.get("id") or "").lower()

    combined = f"{name} {auto_id} {elem_text} {elem_id}"
    return any(kw in combined for kw in _SUBMIT_CONFIRM_KEYWORDS)


def _is_recognized_shortcut(ev: Dict[str, Any]) -> bool:
    """Check if keystroke is a recognized shortcut (Ctrl+C, Ctrl+V, etc.)."""
    pl = ev.get("payload") or {}
    mods = pl.get("modifiers") or {}
    key = str(pl.get("key") or pl.get("character") or "").lower()
    if mods.get("ctrl") or mods.get("control"):
        if key in ("c", "v", "x", "s", "f", "a", "z"):
            return True
    return False


def filter_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pre-processing noise filter.

    Discards:
      - mouse_scroll, screenshot_smart, system events (session_*, upload_*, extension_*)
      - mouse_click / mouse_double_click (unless interacting with a submit/confirm button)
      - raw keystrokes (except recognized shortcuts like Ctrl+C / Ctrl+V)

    Keeps:
      - app_switch, clipboard_change, browser_navigation, window_title_change
      - shortcut events (OS-level shortcuts)
      - submit/confirm button mouse clicks
      - window_state_change, dialog_opened, dialog_closed
    """
    filtered = []
    for ev in events:
        etype = ev.get("event_type")
        if etype in _DROPPED_TYPES:
            if etype == "keystroke" and _is_recognized_shortcut(ev):
                filtered.append(ev)
            continue
        if etype in ("mouse_click", "mouse_double_click", "mouse_drag_drop"):
            if _is_submit_or_confirm_click(ev):
                filtered.append(ev)
            continue
        filtered.append(ev)
    return filtered


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Golden Thread State Machine Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _get_portal_system(window_title: Optional[str]) -> Optional[str]:
    """Return the portal system identifier if the window title matches."""
    if not window_title:
        return None
    for ps in _PORTAL_SYSTEMS:
        if ps in window_title:
            return ps
    return None


def _is_hub_url(url: Optional[str]) -> bool:
    """True if URL represents a Hub (root URL or ending with /dashboard or /index)."""
    if not url:
        return False
    u = url.strip().rstrip("/").lower()
    if u.endswith("/dashboard") or u.endswith("#/dashboard"):
        return True
    if u.endswith("/index") or u.endswith("/index.html"):
        return True
    return bool(_HUB_URL_RE.match(url.strip()))


def _is_chrome(app_name: Optional[str]) -> bool:
    return "chrome" in (app_name or "").lower()


def _get_app_name(event: Dict[str, Any]) -> str:
    """Extract active app name from event context or payload."""
    if event.get("event_type") == "app_switch":
        pl = event.get("payload") or {}
        name = (pl.get("new_app") or {}).get("app_name") or ""
        if name:
            return name
    ctx = event.get("context") or {}
    aa = ctx.get("active_app") or {}
    return aa.get("app_name") or aa.get("process_name") or ""


def _get_window_title(event: Dict[str, Any]) -> str:
    """Extract the active window title from the event."""
    if event.get("event_type") == "app_switch":
        pl = event.get("payload") or {}
        wt = (pl.get("new_app") or {}).get("window_title") or ""
        if wt:
            return wt
    if event.get("event_type") == "window_title_change":
        pl = event.get("payload") or {}
        wt = pl.get("new_title") or ""
        if wt:
            return wt
    ctx = event.get("context") or {}
    aa = ctx.get("active_app") or {}
    return aa.get("window_title") or ""


def _get_browser_url(event: Dict[str, Any]) -> str:
    """Extract browser URL from browser_navigation or active browser tab."""
    if event.get("event_type") == "browser_navigation":
        pl = event.get("payload") or {}
        url = pl.get("url") or pl.get("to_url") or ""
        if url:
            return url
    ctx = event.get("context") or {}
    tab = ctx.get("active_browser_tab") or {}
    return tab.get("url") or ""


def _get_clipboard_anchor(event: Dict[str, Any]) -> Optional[str]:
    """Extract the Entity_Anchor from a clipboard_change event.

    Captures text payload if present. When text content is masked for privacy,
    uses the text_length fingerprint as the entity representation.
    """
    if event.get("event_type") != "clipboard_change":
        return None
    pl = event.get("payload") or {}
    text = pl.get("text_content")
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    tlen = pl.get("text_length")
    if tlen is not None and tlen > 0:
        return f"len_{tlen}"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: LLM-Assisted Labeling (Preparation)
# ──────────────────────────────────────────────────────────────────────────────


def extract_segment_context(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract all unique Window Titles, URLs, and Japanese extracted_text."""
    window_titles: Set[str] = set()
    urls: Set[str] = set()
    extracted_texts: List[str] = []
    apps: Set[str] = set()
    portal_system: Optional[str] = None

    for ev in events:
        ctx = ev.get("context") or {}
        pl = ev.get("payload") or {}
        aa = ctx.get("active_app") or {}
        app_name = aa.get("app_name") or aa.get("process_name") or ""
        wt = _get_window_title(ev)

        if app_name:
            apps.add(app_name)
        if wt:
            window_titles.add(wt)

        for ps in _PORTAL_SYSTEMS:
            if ps in wt and portal_system is None:
                portal_system = ps

        url = _get_browser_url(ev)
        if url:
            urls.add(url)

        et = ctx.get("extracted_text")
        if et:
            if isinstance(et, str) and et.strip():
                extracted_texts.append(et.strip()[:200])
            elif isinstance(et, dict) and et.get("text"):
                extracted_texts.append(str(et["text"]).strip()[:300])
            elif isinstance(et, list):
                for item in et:
                    if isinstance(item, str) and item.strip():
                        extracted_texts.append(item.strip()[:200])
                    elif isinstance(item, dict) and item.get("text"):
                        extracted_texts.append(str(item["text"]).strip()[:300])

        te = pl.get("target_element") or {}
        elem = pl.get("element") or {}
        elem_attrs = elem.get("attributes") or {}
        form_txt = (
            te.get("name")
            or elem.get("text")
            or elem_attrs.get("innerText")
            or elem_attrs.get("placeholder")
            or elem_attrs.get("value")
        )
        if form_txt and isinstance(form_txt, str) and form_txt.strip():
            extracted_texts.append(form_txt.strip()[:100])

    return {
        "portal_system": portal_system,
        "window_titles": sorted(window_titles),
        "urls": sorted(urls),
        "extracted_text": sorted(set(extracted_texts))[:20],
        "apps": sorted(apps),
    }



def _rule_based_label(context: Dict[str, Any]) -> str:
    """Heuristic fallback derived from portal systems."""
    ps = context.get("portal_system")
    if ps == "HR人事給与システム":
        return "hr_process"
    if ps == "財務会計システム":
        return "finance_process"
    if ps == "受発注在庫管理システム":
        return "ops_process"
    for wt in context.get("window_titles", []):
        if "Chrome" not in wt and len(wt) > 3:
            clean = re.sub(r"[^\w\s-]", "", wt).strip()
            if clean:
                return clean[:30].lower().replace(" ", "_").replace("-", "_")
    return "process_unknown"


def generate_segment_label(
    segment_context: Union[Dict[str, Any], List[Dict[str, Any]]],
    llm_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
    fallback_to_rules: bool = False,
) -> str:
    """Generate a label for a completed segment from its context.

    Args:
        segment_context: Dict containing unique window_titles, urls, and
                         extracted_text (or list of segment events).
        llm_fn: Optional LLM callable: receives segment_context and returns
                a standardized label.
        fallback_to_rules: If True, fall back to domain heuristic rules.
                           Default False returns mock fallback 'process_unknown'.

    Returns:
        Label string. Defaults to mock fallback 'process_unknown'.
    """
    if isinstance(segment_context, list):
        context = extract_segment_context(segment_context)
    elif isinstance(segment_context, dict):
        context = segment_context
    else:
        context = {}

    if llm_fn is not None:
        try:
            label = llm_fn(context)
            if label and isinstance(label, str) and label.strip():
                return label.strip()[:64]
        except Exception:
            pass

    if fallback_to_rules:
        return _rule_based_label(context)

    # Step 3 mock fallback
    return "process_unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Segment Builder
# ──────────────────────────────────────────────────────────────────────────────


class _SegmentBuilder:
    """Accumulates state for a single in-progress segment."""

    def __init__(self, session_id: str, start_event: Dict[str, Any]) -> None:
        self.session_id = session_id
        self.start_ms: int = start_event.get("timestamp_ms", 0)
        self.last_ms: int = self.start_ms
        self._events: List[Dict[str, Any]] = [start_event]

        self.portal_system: Optional[str] = _get_portal_system(_get_window_title(start_event))
        self.last_chrome_portal_system: Optional[str] = self.portal_system

        self.window_titles: Set[str] = set()
        self.urls: Set[str] = set()
        self.extracted_texts: List[str] = []
        self.apps_seen: Set[str] = set()
        self.anchor: Optional[str] = None
        self.anchor_texts: List[str] = []
        self.was_in_work_app: bool = False

        self._absorb(start_event)

    @property
    def duration_s(self) -> float:
        return (self.last_ms - self.start_ms) / 1000.0

    def _absorb(self, ev: Dict[str, Any]) -> None:
        app = _get_app_name(ev)
        wt = _get_window_title(ev)
        url = _get_browser_url(ev)

        if app:
            self.apps_seen.add(app)
            if not _is_chrome(app) and app in _WORK_APPS:
                self.was_in_work_app = True
        if wt:
            self.window_titles.add(wt)
        if url:
            self.urls.add(url)

        ctx = ev.get("context") or {}
        pl = ev.get("payload") or {}
        et = ctx.get("extracted_text")
        if et:
            if isinstance(et, str) and et.strip():
                self.extracted_texts.append(et.strip()[:200])
            elif isinstance(et, dict) and et.get("text"):
                self.extracted_texts.append(str(et["text"]).strip()[:300])
            elif isinstance(et, list):
                for item in et:
                    if isinstance(item, str) and item.strip():
                        self.extracted_texts.append(item.strip()[:200])
                    elif isinstance(item, dict) and item.get("text"):
                        self.extracted_texts.append(str(item["text"]).strip()[:300])

        te = pl.get("target_element") or {}
        elem = pl.get("element") or {}
        elem_attrs = elem.get("attributes") or {}
        form_txt = (
            te.get("name")
            or elem.get("text")
            or elem_attrs.get("innerText")
            or elem_attrs.get("placeholder")
            or elem_attrs.get("value")
        )
        if form_txt and isinstance(form_txt, str) and form_txt.strip():
            self.extracted_texts.append(form_txt.strip()[:100])

        ps = _get_portal_system(wt)
        if ps and _is_chrome(app):
            self.last_chrome_portal_system = ps
            if self.portal_system is None:
                self.portal_system = ps

        anc = _get_clipboard_anchor(ev)
        if anc:
            self.anchor_texts.append(anc)
            if self.anchor is None:
                self.anchor = anc

    def push(self, ev: Dict[str, Any]) -> None:
        self._events.append(ev)
        self.last_ms = ev.get("timestamp_ms", self.last_ms)
        self._absorb(ev)

    def build(self, label: str = "process_unknown") -> Optional[Segment]:
        if (self.last_ms - self.start_ms) < MIN_SEGMENT_MS:
            return None
        return Segment(
            session_id=self.session_id,
            start_ms=self.start_ms,
            end_ms=self.last_ms,
            label=label,
            event_count=len(self._events),
            window_titles=sorted(self.window_titles),
            urls=sorted(self.urls),
            extracted_texts=self.extracted_texts[:10],
            apps_seen=sorted(self.apps_seen),
            anchor_texts=self.anchor_texts,
        )

    @property
    def events(self) -> List[Dict[str, Any]]:
        return self._events


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Semantic Merging Post-Processor
# ──────────────────────────────────────────────────────────────────────────────


def merge_segments(
    segments: List[Segment],
    max_gap_ms: int = 30_000,
) -> List[Segment]:
    """Semantic Merging Post-Processor.

    Iterate through chronological segments. If Segment A and Segment B are adjacent
    (or separated by less than a 30-second gap) and share the EXACT same label,
    merge them into a single segment spanning A.start to B.end.

    Args:
        segments: List of chronological Segment objects.
        max_gap_ms: Maximum gap between segments in ms to allow merging (default: 30,000 ms).

    Returns:
        List of merged Segment objects.
    """
    if not segments:
        return []

    sorted_segs = sorted(segments, key=lambda s: s.start_ms)
    merged: List[Segment] = [sorted_segs[0]]

    for curr in sorted_segs[1:]:
        prev = merged[-1]
        gap_ms = curr.start_ms - prev.end_ms

        prev_anc = set(prev.anchor_texts)
        curr_anc = set(curr.anchor_texts)
        different_entities = bool(prev_anc and curr_anc and not (prev_anc & curr_anc))

        can_merge = (
            prev.label == curr.label
            and prev.label != "process_unknown"
            and gap_ms <= max_gap_ms
            and not different_entities
            and ((curr.start_ms - prev.start_ms) < 75_000 or prev.duration_s < 25.0 or curr.duration_s < 25.0)
        )

        if can_merge:
            merged[-1] = Segment(
                session_id=prev.session_id,
                start_ms=prev.start_ms,
                end_ms=max(prev.end_ms, curr.end_ms),
                label=prev.label,
                event_count=prev.event_count + curr.event_count,
                window_titles=sorted(set(prev.window_titles) | set(curr.window_titles)),
                urls=sorted(set(prev.urls) | set(curr.urls)),
                extracted_texts=prev.extracted_texts + curr.extracted_texts,
                apps_seen=sorted(set(prev.apps_seen) | set(curr.apps_seen)),
                anchor_texts=prev.anchor_texts + curr.anchor_texts,
            )
        else:
            merged.append(curr)

    return merged


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Main Segmenter State Machine
# ──────────────────────────────────────────────────────────────────────────────


class GoldenThreadSegmenter:
    """Segments a chronological event stream into business-process executions.

    Implements the Entity-Centric Golden Thread algorithm tracing clipboard
    entities across applications and identifying natural process boundaries.
    """

    def __init__(
        self,
        session_id: str,
        idle_timeout_ms: int = IDLE_TIMEOUT_MS,
        min_segment_ms: int = MIN_SEGMENT_MS,
        llm_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
        fallback_to_rules: bool = False,
    ) -> None:
        self.session_id = session_id
        self.idle_timeout_ms = idle_timeout_ms
        self.min_segment_ms = min_segment_ms
        self.llm_fn = llm_fn
        self.fallback_to_rules = fallback_to_rules

    def segment(self, events: List[Dict[str, Any]]) -> Iterator[Segment]:
        """Segment an event list; yields Segment objects in chronological order."""
        # Step 1: filter noise
        kept = filter_events(events)
        if not kept:
            return

        # Step 2: generate initial heuristic segments from state machine
        raw_segments = list(self._run_state_machine(kept))
        if not raw_segments:
            return

        # Step 3: pass each segment's context to llm_labeler (or user-supplied llm_fn)
        label_fn = self.llm_fn if self.llm_fn is not None else predict_label
        for seg in raw_segments:
            ctx = {
                "window_titles": seg.window_titles,
                "urls": seg.urls,
                "extracted_text": seg.extracted_texts,
                "portal_system": None,
                "apps": seg.apps_seen,
            }
            lbl = label_fn(ctx)
            if lbl and isinstance(lbl, str) and lbl.strip():
                seg.label = lbl.strip()

        # Step 4: apply semantic merging post-processor
        merged_segments = merge_segments(raw_segments)
        yield from merged_segments

    def _run_state_machine(self, events: List[Dict[str, Any]]) -> Iterator[Segment]:
        """Core state machine: consumes filtered events, yields completed segments."""
        builder: Optional[_SegmentBuilder] = None
        pending_short: Optional[_SegmentBuilder] = None
        prev_anchor: Optional[str] = None

        for ev in events:
            ev_type = ev.get("event_type", "")
            ev_ms = ev.get("timestamp_ms", 0)
            app = _get_app_name(ev)
            wt = _get_window_title(ev)
            url = _get_browser_url(ev)
            anchor = _get_clipboard_anchor(ev)

            # ── Boundary Condition C: Prolonged Inactivity (> 60s) ───────────
            if builder is not None:
                gap = ev_ms - builder.last_ms
                if gap >= self.idle_timeout_ms:
                    seg = self._finalize(builder)
                    if seg:
                        yield from self._maybe_merge_pending(pending_short, seg)
                        pending_short = None
                    elif pending_short is not None:
                        for e in builder.events:
                            pending_short.push(e)
                    else:
                        pending_short = builder
                    builder = None

            # ── Boundary Condition A & Portal Transition on app_switch ────────
            if ev_type == "app_switch" and builder is not None:
                new_app = _get_app_name(ev)
                new_wt = _get_window_title(ev)
                new_ps = _get_portal_system(new_wt)
                new_url = _get_browser_url(ev)

                trigger: Optional[str] = None

                # 1. Portal system change
                if (
                    _is_chrome(new_app)
                    and new_ps is not None
                    and builder.last_chrome_portal_system is not None
                    and new_ps != builder.last_chrome_portal_system
                ):
                    trigger = "PORTAL_SYSTEM_CHANGE"

                # 2. Hub return: user returned to Chrome Hub after visiting external work apps
                elif (
                    _is_chrome(new_app)
                    and _is_hub_url(new_url)
                    and builder.was_in_work_app
                    and builder.duration_s >= 12.0
                ):
                    trigger = "HUB_RETURN"

                if trigger is not None:
                    seg = self._finalize(builder)
                    if seg:
                        yield from self._maybe_merge_pending(pending_short, seg)
                        pending_short = None
                    else:
                        if pending_short is not None:
                            for e in builder.events:
                                pending_short.push(e)
                        else:
                            pending_short = builder
                    builder = None

            # ── Boundary Condition A: Hub return via browser_navigation ──────
            if ev_type == "browser_navigation" and builder is not None:
                nav_url = (ev.get("payload") or {}).get("url") or (ev.get("payload") or {}).get("to_url") or ""
                if _is_hub_url(nav_url) and builder.was_in_work_app and builder.duration_s >= 12.0:
                    seg = self._finalize(builder)
                    if seg:
                        yield from self._maybe_merge_pending(pending_short, seg)
                        pending_short = None
                    builder = None

            # ── Boundary Condition B: A completely new Entity_Anchor is copied ─
            if ev_type == "clipboard_change" and builder is not None and anchor is not None:
                if (
                    builder.duration_s >= 20.0
                    and builder.was_in_work_app
                    and prev_anchor is not None
                    and anchor != prev_anchor
                ):
                    # Switch to a new case/task
                    seg = self._finalize(builder)
                    if seg:
                        yield from self._maybe_merge_pending(pending_short, seg)
                        pending_short = None
                    else:
                        if pending_short is not None:
                            for e in builder.events:
                                pending_short.push(e)
                        else:
                            pending_short = builder
                    builder = None

            if ev_type == "clipboard_change" and anchor is not None:
                prev_anchor = anchor

            # ── Start new segment or push event to current ───────────────────
            if builder is None:
                builder = _SegmentBuilder(self.session_id, ev)
            else:
                builder.push(ev)

        # ── Flush final segment at end of stream ─────────────────────────────
        if builder is not None:
            seg = self._finalize(builder)
            if seg:
                yield from self._maybe_merge_pending(pending_short, seg)
            elif pending_short is not None:
                for e in builder.events:
                    pending_short.push(e)
                merged = self._finalize(pending_short)
                if merged:
                    yield merged
        elif pending_short is not None:
            seg = self._finalize(pending_short)
            if seg:
                yield seg

    def _finalize(self, builder: _SegmentBuilder) -> Optional[Segment]:
        """Label and build a segment; return None if it is too short."""
        if (builder.last_ms - builder.start_ms) < self.min_segment_ms:
            return None
        context = extract_segment_context(builder.events)
        label = generate_segment_label(
            context,
            llm_fn=self.llm_fn,
            fallback_to_rules=self.fallback_to_rules,
        )
        return builder.build(label)

    @staticmethod
    def _maybe_merge_pending(
        pending: Optional[_SegmentBuilder],
        seg: Segment,
    ) -> Iterator[Segment]:
        """Yield pending (if exists and long enough) then the new segment."""
        if pending is not None:
            if (pending.last_ms - pending.start_ms) >= MIN_SEGMENT_MS:
                context = extract_segment_context(pending.events)
                label = generate_segment_label(context)
                built = pending.build(label)
                if built:
                    yield built
        yield seg


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────────────────────────────────────


def segment_session(
    session_id: str,
    events: List[Dict[str, Any]],
    llm_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
    idle_timeout_ms: int = IDLE_TIMEOUT_MS,
    min_segment_ms: int = MIN_SEGMENT_MS,
    fallback_to_rules: bool = False,
) -> List[Segment]:
    """Segment a session's event list; returns a list of Segments."""
    segmenter = GoldenThreadSegmenter(
        session_id=session_id,
        idle_timeout_ms=idle_timeout_ms,
        min_segment_ms=min_segment_ms,
        llm_fn=llm_fn,
        fallback_to_rules=fallback_to_rules,
    )
    return list(segmenter.segment(events))
