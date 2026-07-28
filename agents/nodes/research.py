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
# N3 caps how many tool calls the MODEL may schedule. It is deliberately NOT a cap on how many
# documents the citizen is shown: applying it to local document resolution silently truncated the
# answer. #11610 publishes 29 required documents and the answer carried 6 — 23 requirements dropped
# without a word, on 25 of 193 services (104 documents in total). `resolve_document` is local
# (corpus + curated lookup, no HTTP) and measures ~60 ms, so resolving all 29 costs ~1.4 s on the
# worst service in the corpus and nothing at all on any service with 6 documents or fewer.
# An incomplete checklist is a wrong answer to a citizen; 1.4 s is a latency line in a report.
MAX_MODEL_TOOL_CALLS = 6   # N3 cap — MODEL-scheduled calls only, never the display list
DEGRADE_ABOVE_DOCS = 4     # >4 documents => skip per-doc freshness, check the service only


def _as_dict(result) -> dict:
    """Tools may return a Pydantic model or an already-dumped dict; normalise to dict.

    The trace is what the demo shows on screen, so a `getattr` against a dict silently rendering
    `None` is a visible defect, not just an internal one — it made two working external calls
    look like failures.
    """
    if isinstance(result, dict):
        return result
    return result.model_dump() if hasattr(result, "model_dump") else {}


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

    # --- resolve EVERY published document ----------------------------------
    # Every document the source lists must reach the answer, resolved or not. Whether we could
    # find where to obtain it is a separate question from whether the citizen needs it, and only
    # the source decides the second one. See the note on MAX_MODEL_TOOL_CALLS above.
    resolve = tools.get("resolve_document")
    if resolve:
        for name in doc_names:
            documents.append(resolve(name))
            calls.append({"tool": "resolve_document", "arg": name[:60]})

    # --- freshness: DETERMINISTIC system step, not a model decision (N3) ----
    degraded = len(doc_names) > DEGRADE_ABOVE_DOCS
    check = tools.get("check_freshness")
    if check and record.get("post_id") is not None:
        fresh = _as_dict(check(record["post_id"]))
        calls.append({"tool": "check_freshness", "arg": record["post_id"],
                      "result": fresh.get("status")})
        state = {**state, "service_freshness": fresh}

    # --- live lookup: the 2nd external call --------------------------------
    lookup = tools.get("live_service_lookup")
    if lookup:
        res = _as_dict(lookup(state.get("query", "")))
        calls.append({"tool": "live_service_lookup", "arg": state.get("query", "")[:60],
                      "result": f"exists={res.get('exists')}"
                                + (f" newest=#{res['newest_post_id']}"
                                   if res.get("newest_post_id") else "")})
        state = {**state, "live_lookup": res}

    return with_trace(
        state, "research",
        {"resolved_documents": documents, "replans_used": replans,
         "service_freshness": state.get("service_freshness"),
         "live_lookup": state.get("live_lookup")},
        mode="live", n_documents=len(documents), tool_calls=len(calls), calls=calls,
        per_doc_freshness_degraded=degraded,
        # Both counts are traced so the completeness invariant is auditable from the evidence
        # artefact alone: n_resolved MUST equal n_source_documents. When they diverged, the answer
        # was quietly short and nothing on screen or in the trace said so.
        n_source_documents=len(doc_names), n_resolved=len(documents),
        documents_complete=len(documents) == len(doc_names),
    )
