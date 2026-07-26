"""HITL review queue: append-only JSONL with a file lock and dedupe (SCOPE §6, A09).

The queue is the system owner's (OMSAR content ops) work list. Every claim the agent could not
verify lands here rather than being quietly dropped or quietly asserted.

Design constraints from A09:
  * **append-only** — history is evidence; resolving an event appends a new line, never rewrites
    an old one, so the JSONL stays a log rather than a mutable store;
  * **file-locked** (portalocker) — the agent and `diff_recrawl.py` can both append concurrently;
  * **deduped on (event_type, subject, open)** — a service that is stale stays stale, and a query
    re-asked ten times must not produce ten identical open events.

`subject_post_id` is nullable: an unresolved *document* is usually not a service post and has no
id of its own (A09), so `subject_label` carries the human-readable subject in every case.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.models import QueueEvent  # noqa: E402

QUEUE_PATH = ROOT / "data" / "review_queue.jsonl"


def _lock(fh):
    """portalocker if present; otherwise a no-op so a missing optional dep cannot lose an event."""
    try:
        import portalocker
        portalocker.lock(fh, portalocker.LOCK_EX)
        return True
    except Exception:  # noqa: BLE001
        return False


def read_events(path: Path | None = None) -> list[QueueEvent]:
    p = path or QUEUE_PATH
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(QueueEvent.model_validate_json(line))
        except Exception:  # noqa: BLE001  a corrupt line must not hide the rest of the queue
            continue
    return out


def open_events(path: Path | None = None) -> list[QueueEvent]:
    """Latest state per event_id, filtered to still-open. Resolution is an appended line, so the
    last line mentioning an event_id wins."""
    latest: dict[str, QueueEvent] = {}
    for ev in read_events(path):
        latest[ev.event_id] = ev
    return [e for e in latest.values() if e.status == "open"]


def _dedupe_key(event_type: str, subject_post_id: int | None, subject_label: str) -> tuple:
    return (event_type, subject_post_id, subject_label.strip())


def append_event(event_type: str, subject_label: str, subject_post_id: int | None = None,
                 source: str = "agent", source_url: str | None = None, details: str = "",
                 path: Path | None = None) -> QueueEvent | None:
    """Append one event. Returns None if an identical OPEN event already exists (deduped).

    Dedupe is on (event_type, subject, still-open) per A09 — deliberately NOT on time, so the same
    unverifiable claim re-encountered tomorrow does not create a second ticket for the same work.
    """
    p = path or QUEUE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)

    key = _dedupe_key(event_type, subject_post_id, subject_label)
    for ev in open_events(p):
        if _dedupe_key(ev.event_type, ev.subject_post_id, ev.subject_label) == key:
            return None

    ev = QueueEvent(
        event_id=uuid.uuid4().hex[:12],
        event_type=event_type,          # type: ignore[arg-type]  validated by the model
        subject_post_id=subject_post_id,
        subject_label=subject_label,
        source_url=source_url,
        detected_at=datetime.now(timezone.utc).isoformat(),
        source=source,                  # type: ignore[arg-type]
        status="open",
        details=details,
    )
    line = ev.model_dump_json() + "\n"
    # "a" + lock + flush + fsync: an event that reached the queue must survive a crash, and two
    # processes appending must not interleave a partial line.
    with open(p, "a", encoding="utf-8") as fh:
        _lock(fh)
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return ev


def resolve_event(event_id: str, details: str = "", path: Path | None = None) -> QueueEvent | None:
    """Close an event by APPENDING its resolved state — the log is never rewritten."""
    p = path or QUEUE_PATH
    current = {e.event_id: e for e in read_events(p)}
    ev = current.get(event_id)
    if ev is None or ev.status == "resolved":
        return None
    resolved = ev.model_copy(update={
        "status": "resolved",
        "details": (ev.details + " | " if ev.details else "") + (details or "resolved"),
    })
    with open(p, "a", encoding="utf-8") as fh:
        _lock(fh)
        fh.write(resolved.model_dump_json() + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return resolved


def summary(path: Path | None = None) -> dict:
    evs = read_events(path)
    opens = open_events(path)
    by_type: dict[str, int] = {}
    for e in opens:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
    return {"lines": len(evs), "open": len(opens), "by_type": by_type}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    s = summary()
    print(f"review queue: {QUEUE_PATH}")
    print(f"  lines {s['lines']} | open {s['open']}")
    for k, v in sorted(s["by_type"].items()):
        print(f"    {k:24s} {v}")
    for e in open_events()[:10]:
        print(f"  [{e.event_type:22s}] {e.subject_label[:50]}  ({e.detected_at[:10]})")
