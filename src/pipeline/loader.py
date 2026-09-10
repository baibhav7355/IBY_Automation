"""Session event loader for PC operation logs.

Handles multi-chunk ingestion, strict chronological sorting across chunks,
UTF-8 encoding enforcement for Japanese text, and mitigation of buggy
recording events (such as unreliable `text_input_complete` events).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Literal, Optional, Union

logger = logging.getLogger(__name__)

TextInputPolicy = Literal["drop", "flag", "keep"]


def find_session_chunks(session_dir: Union[str, Path]) -> List[Path]:
    """Find and return all chunk subdirectories for a given session.

    Args:
        session_dir: Path to the session directory (e.g., 'dataset_a/ses_...').

    Returns:
        Sorted list of Path objects pointing to chunk subdirectories containing
        an events.jsonl file.

    Raises:
        FileNotFoundError: If session_dir does not exist.
        NotADirectoryError: If session_dir is not a directory.
    """
    session_path = Path(session_dir)
    if not session_path.exists():
        raise FileNotFoundError(f"Session directory not found: {session_path}")
    if not session_path.is_dir():
        raise NotADirectoryError(f"Session path is not a directory: {session_path}")

    # Chunks are subdirectories matching 'chunk*' containing 'events.jsonl'
    chunks = [
        p.parent
        for p in session_path.glob("chunk*/events.jsonl")
        if p.is_file()
    ]
    return sorted(chunks, key=lambda p: p.name)


def find_session_event_files(session_dir: Union[str, Path]) -> List[Path]:
    """Find all `events.jsonl` files across all chunks of a session.

    Args:
        session_dir: Path to the session directory.

    Returns:
        Sorted list of Path objects pointing to `events.jsonl` files.
    """
    chunks = find_session_chunks(session_dir)
    return [chunk / "events.jsonl" for chunk in chunks]


def _process_event(
    event: Dict[str, Any],
    policy: TextInputPolicy,
) -> Optional[Dict[str, Any]]:
    """Process a single event according to data quirk mitigation policies.

    Per DATA_SCHEMA.md:
    'text_input_complete is not reliable. Due to a recording defect, some entries
    are missing their content, and some events that are not actually text input
    (such as keyboard shortcuts) are mixed in. If you need text input, reconstruct
    it from keystroke or clipboard_change.'

    Args:
        event: Raw event dictionary parsed from events.jsonl.
        policy: One of 'drop', 'flag', or 'keep'.

    Returns:
        The processed event dictionary, or None if the event should be dropped.
    """
    event_type = event.get("event_type")
    if event_type == "text_input_complete":
        if policy == "drop":
            return None
        elif policy == "flag":
            event["_is_unreliable"] = True
            event["_quirk_reason"] = (
                "text_input_complete is unreliable per schema; use keystroke or clipboard_change"
            )
            # Flag in metadata if present or create it
            metadata = event.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["is_buggy_recording"] = True
    return event


def load_session_events(
    session_dir: Union[str, Path],
    text_input_policy: TextInputPolicy = "drop",
    drop_text_input_complete: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Load, filter, and strictly sort all events from all chunks in a session.

    Args:
        session_dir: Path to the session directory.
        text_input_policy: How to handle buggy 'text_input_complete' events.
            - 'drop' (default): Filter out and exclude text_input_complete events.
            - 'flag': Retain events but mark them with `_is_unreliable=True`.
            - 'keep': Keep events as-is without flagging.
        drop_text_input_complete: Deprecated boolean alias for text_input_policy.
            If set to True, policy is 'drop'. If False and text_input_policy was
            not explicitly provided, policy is 'flag'.

    Returns:
        List of event dictionaries, strictly sorted chronologically by
        timestamp_ms (and sequence_number for ties).
    """
    policy = text_input_policy
    if drop_text_input_complete is not None:
        policy = "drop" if drop_text_input_complete else "flag"

    event_files = find_session_event_files(session_dir)
    if not event_files:
        logger.warning("No events.jsonl files found in session directory: %s", session_dir)
        return []

    events: List[Dict[str, Any]] = []

    for file_path in event_files:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    raw_event = json.loads(line_str)
                except json.JSONDecodeError as err:
                    logger.warning(
                        "JSON decode error in %s at line %d: %s",
                        file_path,
                        line_idx,
                        err,
                    )
                    continue

                processed = _process_event(raw_event, policy)
                if processed is not None:
                    events.append(processed)

    # Sort strictly chronologically by timestamp_ms.
    # Break ties using chunk sequence_number or fallback to 0.
    events.sort(
        key=lambda ev: (
            ev.get("timestamp_ms") if ev.get("timestamp_ms") is not None else 0,
            ev.get("correlation", {}).get("sequence_number", 0)
            if isinstance(ev.get("correlation"), dict)
            else 0,
        )
    )

    return events


def iter_session_events(
    session_dir: Union[str, Path],
    text_input_policy: TextInputPolicy = "drop",
    drop_text_input_complete: Optional[bool] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Yield all events for a session in strict chronological order.

    Args:
        session_dir: Path to the session directory.
        text_input_policy: Handling policy ('drop', 'flag', 'keep').
        drop_text_input_complete: Optional boolean flag.

    Yields:
        Event dictionaries sorted by timestamp_ms.
    """
    events = load_session_events(
        session_dir=session_dir,
        text_input_policy=text_input_policy,
        drop_text_input_complete=drop_text_input_complete,
    )
    yield from events


def load_ground_truth(session_dir: Union[str, Path]) -> Optional[List[Dict[str, Any]]]:
    """Load ground truth events from `gt.jsonl` if present in the session directory.

    Args:
        session_dir: Path to session directory.

    Returns:
        List of ground truth records, or None if gt.jsonl is not present (e.g., Dataset B).
    """
    gt_file = Path(session_dir) / "gt.jsonl"
    if not gt_file.is_file():
        return None

    records: List[Dict[str, Any]] = []
    with open(gt_file, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                records.append(record)
            except json.JSONDecodeError as err:
                logger.warning("JSON decode error in %s at line %d: %s", gt_file, line_idx, err)
    return records


def load_ground_truth_manifest(session_dir: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load ground truth summary manifest `gt_manifest.json` if present.

    Args:
        session_dir: Path to session directory.

    Returns:
        Parsed ground truth manifest dictionary, or None if not present.
    """
    manifest_file = Path(session_dir) / "gt_manifest.json"
    if not manifest_file.is_file():
        return None

    with open(manifest_file, "r", encoding="utf-8") as f:
        return json.load(f)
