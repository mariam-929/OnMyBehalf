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
    # guardrail / routing outcomes (set by nodes, read by the conditional edges)
    invalid: Optional[dict]            # InvalidOut dumped -> routes to respond_invalid
    retrieval_outcome: str             # "found" | "ambiguous" | "not_found"
    schema_ok: bool
    error_stage: str
    error_detail: str
    # retrieval / research
    retrieved: list[RetrievedCandidate]
    service_record: Optional[CorpusRecord]
    resolved_documents: list[ResolvedDocument]
    service_freshness: Optional[dict]  # FreshnessResult dumped (deterministic system step, N3)
    live_lookup: Optional[LiveLookupResult]
    # The model's rescue plan, set by plan_research and consumed by research. It MUST be declared
    # here: LangGraph filters node updates against this schema, so an undeclared key is silently
    # dropped. When it was missing, `research` never saw a plan, kept taking the first-pass branch,
    # re-ran the live freshness call on every iteration, and never incremented replans_used — an
    # infinite loop that presented as a network hang inside the TLS handshake.
    research_plan: Optional[dict]
    replans_used: int
    # Set only by the external-source branch. Like research_plan above, it MUST be declared here or
    # LangGraph drops the node's update against this schema and the UI can never show the badge
    # that tells the citizen the facts came from a site other than Dawlati.
    external_source_used: bool
    candidates: list[dict]             # ClarifyOut candidates
    suggestions: list[dict]            # NotFoundOut suggestions
    time_estimate: Optional[dict]
    reasoning: str
    # session memory (FR11)
    messages: list[dict]               # last 6 turns
    user_held_documents: list[str]
    # output
    final_response: Optional[dict]     # a validated Envelope, dumped
    retry_count: int
    trace_events: list[dict[str, Any]]  # single source for UI panel + eval (SCOPE §10)
