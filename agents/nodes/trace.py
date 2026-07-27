"""Trace helper — the single writer for `state['trace_events']`.

SCOPE §10 makes this list the one source for BOTH the UI trace panel and the eval harness, and
the brief requires a tool call to be visible in a trace during the demo. Keeping every append in
one place is what stops those two consumers from drifting apart.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def trace(node: str, **fields: Any) -> dict[str, Any]:
    """Build one trace event. Callers append the result to state['trace_events']."""
    return {"node": node, "at": datetime.now(timezone.utc).isoformat(), **fields}


def with_trace(state: dict, node: str, update: dict, **fields: Any) -> dict:
    """Return `update` with a trace event appended to the running list.

    LangGraph merges partial updates, so the whole list is carried forward rather than mutated
    in place — mutating `state` directly would lose events on any parallel or retried branch.
    """
    events = list(state.get("trace_events") or [])
    events.append(trace(node, **fields))
    return {**update, "trace_events": events}
