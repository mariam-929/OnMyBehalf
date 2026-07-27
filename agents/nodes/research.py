"""Research node — BOUNDED loop (A02) with a deterministic system freshness step (N3).

The loop is bounded on purpose: 1 plan -> batched execute -> at most 1 re-plan -> compose. An
open-ended tool loop on an 8K-TPM free tier is both a cost risk and a latency risk in a live
8-minute demo, and an agent that can loop indefinitely cannot be given a truthful worst-case
latency figure in the report.

Per-document freshness is NOT delegated to the model (N3). It is a deterministic system step:
the model decides WHICH service to look at, the system decides what is stale. A model asked to
judge staleness will confabulate a judgement; a timestamp comparison will not.
"""
from __future__ import annotations

from agents.nodes.trace import with_trace

MAX_REPLANS = 1
MAX_MODEL_TOOL_CALLS = 6   # N3 cap
DEGRADE_ABOVE_DOCS = 4     # >4 documents => skip per-doc freshness, check the service only


def research(state: dict, tools: dict | None = None) -> dict:
    """Execute the (single) research pass.

    `tools=None` is the fixture path: no external calls, resolved documents come from state.
    With `tools`, each entry is a callable keyed by tool name (resolve_document,
    check_freshness, live_service_lookup).
    """
    replans = int(state.get("replans_used") or 0)
    documents = list(state.get("resolved_documents") or [])
    calls: list[dict] = []

    if tools is None:
        return with_trace(state, "research",
                          {"resolved_documents": documents, "replans_used": replans},
                          mode="fixture", n_documents=len(documents), tool_calls=0)

    record = state.get("service_record") or {}
    doc_names = ((record.get("sections") or {}).get("required_documents")) or []

    # --- resolve documents (bounded) ---------------------------------------
    budget = MAX_MODEL_TOOL_CALLS
    resolve = tools.get("resolve_document")
    if resolve:
        for name in doc_names[:budget]:
            documents.append(resolve(name))
            calls.append({"tool": "resolve_document", "arg": name[:60]})
        budget -= min(len(doc_names), budget)

    # --- freshness: DETERMINISTIC system step, not a model decision (N3) ----
    degraded = len(doc_names) > DEGRADE_ABOVE_DOCS
    check = tools.get("check_freshness")
    if check and record.get("post_id") is not None:
        fresh = check(record["post_id"])
        calls.append({"tool": "check_freshness", "arg": record["post_id"],
                      "result": getattr(fresh, "status", None) or fresh.get("status")})
        state = {**state, "service_freshness": fresh if isinstance(fresh, dict)
                 else fresh.model_dump()}

    # --- live lookup: the 2nd external call --------------------------------
    lookup = tools.get("live_service_lookup")
    if lookup:
        res = lookup(state.get("query", ""))
        calls.append({"tool": "live_service_lookup", "arg": state.get("query", "")[:60],
                      "result": getattr(res, "exists", None)})
        state = {**state, "live_lookup": res if isinstance(res, dict) else res.model_dump()}

    return with_trace(
        state, "research",
        {"resolved_documents": documents, "replans_used": replans,
         "service_freshness": state.get("service_freshness"),
         "live_lookup": state.get("live_lookup")},
        mode="live", n_documents=len(documents), tool_calls=len(calls), calls=calls,
        per_doc_freshness_degraded=degraded,
    )
