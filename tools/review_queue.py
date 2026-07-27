"""Append-only HITL review queue (A09: append-only + file lock + dedupe).

One JSONL file is the single queue for both producers — the live agent and the recrawl differ —
and OMSAR content ops owns it. Three properties matter and each is tested:

  APPEND-ONLY  we never rewrite or truncate; an audit trail that can be edited is not evidence.
  LOCKED       the agent (Streamlit, possibly several sessions) and the recrawl cron can write
               concurrently; without a lock, interleaved writes corrupt JSONL lines.
  DEDUPED      the same stale service hit by ten users in one session must not produce ten
               tickets. Identity = (event_type, subject_post_id, subject_label).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import portalocker

from agents.models import QueueEvent

QUEUE_PATH = Path(__file__).resolve().parents[1] / "data" / "review_queue.jsonl"


def event_id_for(event_type: str, subject_post_id: int | None, subject_label: str) -> str:
    """Stable id from the event's identity — same problem, same id, on any machine or run."""
    key = f"{event_type}|{subject_post_id}|{subject_label}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:16]


def _ids_from(text: str) -> set[str]:
    ids: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(json.loads(line)["event_id"])
        except (json.JSONDecodeError, KeyError):
            continue  # a torn line must not stop the queue from working
    return ids


def existing_ids(path: Path | None = None) -> set[str]:
    p = path or QUEUE_PATH
    if not p.exists():
        return set()
    return _ids_from(p.read_text(encoding="utf-8"))


def append_event(event: QueueEvent, path: Path | None = None) -> bool:
    """Append one event. Returns False if an identical event is already queued (deduped).

    The dedupe read happens INSIDE the lock, through the SAME handle ("a+", seek to 0). Two
    details matter and both were found by the tests:
      * checking before locking would let two concurrent writers both see "absent" and both
        append — the dedupe has to be inside the critical section;
      * on Windows the lock is MANDATORY, so re-opening the path for reading while holding it
        raises PermissionError. One handle, seek, read, then append.
    """
    p = path or QUEUE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    with portalocker.Lock(str(p), mode="a+", encoding="utf-8", timeout=10) as fh:
        fh.seek(0)
        if event.event_id in _ids_from(fh.read()):
            return False
        fh.seek(0, 2)  # back to EOF before appending
        fh.write(event.model_dump_json() + "\n")
        fh.flush()
    return True


def queue_event(event_type: str, subject_label: str, subject_post_id: int | None = None,
                source: str = "agent", source_url: str | None = None, details: str = "",
                path: Path | None = None) -> bool:
    """Convenience constructor + append. Returns True if newly queued."""
    ev = QueueEvent(
        event_id=event_id_for(event_type, subject_post_id, subject_label),
        event_type=event_type,  # type: ignore[arg-type]
        subject_post_id=subject_post_id,
        subject_label=subject_label,
        source_url=source_url,
        detected_at=datetime.now(timezone.utc).isoformat(),
        source=source,  # type: ignore[arg-type]
        details=details,
    )
    return append_event(ev, path)
