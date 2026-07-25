"""LangGraph agent state (SCOPE §5). Filled in during the BUILD track (G5)."""
from __future__ import annotations

from typing import Any, Optional, TypedDict

from agents.models import (
    CorpusRecord, IntentResult, LiveLookupResult, ResolvedDocument, RetrievedCandidate,
)


class AgentState(TypedDict, total=False):
    # inputs / routing
    query: str
    language: str                      # "ar" | "en" (FR1 authoritative detector)
    intent: Optional[IntentResult]
    # retrieval / research
    retrieved: list[RetrievedCandidate]
    service_record: Optional[CorpusRecord]
    resolved_documents: list[ResolvedDocument]
    live_lookup: Optional[LiveLookupResult]
    replans_used: int
    # session memory (FR11)
    messages: list[dict]               # last 6 turns
    user_held_documents: list[str]
    # output
    final_response: Optional[dict]     # a validated Envelope, dumped
    retry_count: int
    trace_events: list[dict[str, Any]]  # single source for UI panel + eval (SCOPE §10)
