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

from agents.models import ResearchPlan
from agents.nodes.trace import with_trace
from agents.planning import accept_rescue, compile_plan, deterministic_plan

PLAN_TIMEOUT_S = 5.0   # bounded like the other two model calls; fallback retries nothing

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


def _unresolved(documents: list[dict]) -> list[tuple[int, dict]]:
    return [(i, d) for i, d in enumerate(documents)
            if (d or {}).get("resolution") == "unresolved"]


def plan_research(state: dict, adapter=None, system_prompt: str = "") -> dict:
    """Ask the model WHICH unresolved documents to retry, and with what search key.

    This is the `plan` step of the loop and it is grounded in an observation: the first pass has
    already resolved every published document, so the model is planning against a measured failure
    rather than speculating. Its budget is the rescue pass only — completeness is never delegated.

    Every failure path produces `deterministic_plan()`, which retries NOTHING. That is exactly the
    behaviour the system had before planning existed, so no model outage can make an answer worse
    than today's.
    """
    record = state.get("service_record") or {}
    documents = list(state.get("resolved_documents") or [])
    query = state.get("query", "") or ""
    pending = _unresolved(documents)

    if not pending:
        return with_trace(state, "plan_research", {"research_plan": deterministic_plan(query=query)},
                          mode="nothing_to_retry", n_unresolved=0)

    if adapter is None:
        return with_trace(state, "plan_research", {"research_plan": deterministic_plan(query=query)},
                          mode="fixture", n_unresolved=len(pending), retries_planned=0)

    # The model sees INDICES and the source wording, and nothing it can turn into a displayed fact.
    # The listing is capped: the whole request competes for an 8K TPM free-tier budget that the
    # composer's prompt already eats into, and an over-long request is simply refused with a 429 —
    # measured, repeatedly. A planner that never runs is worse than one that sees six documents.
    listing = "\n".join(f"[{i}] {(d.get('name_ar') or '')[:80]}" for i, d in pending[:6])
    user = (f"AUTHORITY: {((record.get('sections') or {}).get('where_to_apply') or '')[:70]}\n"
            f"UNRESOLVED (retry by doc_index, optionally with a better search alias):\n{listing}")

    try:
        # reasoning_effort="low": this is a mechanical string-transformation task, not analysis, and
        # generated reasoning tokens count against the same per-minute budget that was refusing the
        # call outright.
        result, meta = adapter.complete(system_prompt, user, ResearchPlan,
                                        reasoning_effort="low", timeout=PLAN_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — a planner outage must not degrade the answer
        return with_trace(state, "plan_research",
                          {"research_plan": deterministic_plan(query=query)},
                          mode="fallback", n_unresolved=len(pending), retries_planned=0,
                          error=str(exc)[:80])

    plan = result.model_dump()
    return with_trace(state, "plan_research", {"research_plan": plan}, mode="model",
                      n_unresolved=len(pending),
                      retries_planned=sum(1 for s in plan.get("plan") or []
                                          if s.get("tool") == "resolve_document"),
                      latency_s=meta.get("latency_s"))


def rescue_pass(state: dict, tools: dict | None = None) -> dict:
    """Execute the planned retries, and BELIEVE ONLY WHAT SURVIVES `accept_rescue`.

    This is the `observe` step, and it is substantive because it can veto the model. Measured: a
    naive retry resolved «طلب مقدم» to the Directorate of Antiquities at 0.7879 and a passport copy
    to the Directorate of Animal Wealth at 0.7402 — both higher-scoring than a correct rescue. A
    rejected rescue leaves the document unresolved, which is the honest outcome.

    Indices are positional into `resolved_documents`, which Step 0 guarantees is one entry per
    published document in source order.
    """
    record = state.get("service_record") or {}
    documents = list(state.get("resolved_documents") or [])
    replans = int(state.get("replans_used") or 0) + 1
    authority = (record.get("sections") or {}).get("where_to_apply")
    resolve = (tools or {}).get("resolve_document")

    steps, rejections = compile_plan(state.get("research_plan"), record,
                                    query=state.get("query", "") or "")
    retries = [s for s in steps if s["tool"] == "resolve_document"]

    accepted, refused, calls = 0, [], []
    if resolve:
        for step in retries:
            idx = step["doc_index"]
            if not (0 <= idx < len(documents)):
                continue
            result = _as_dict(resolve(step["search_key"]))
            ok, why = accept_rescue(result, authority)
            calls.append({"tool": "resolve_document", "arg": step["search_key"][:60],
                          "result": ("accepted" if ok else "rejected") + f" — {why[:60]}"})
            if ok:
                # The DISPLAYED name is always the record's wording; the alias was only a key.
                result["name_ar"] = step["display_name"]
                documents[idx] = result
                accepted += 1
            else:
                refused.append({"doc_index": idx, "searched_as": step["search_key"][:60],
                                "reason": why[:100]})

    return with_trace(
        state, "research",
        {"resolved_documents": documents, "replans_used": replans},
        mode="rescue", tool_calls=len(calls), calls=calls,
        retries_attempted=len(retries), rescues_accepted=accepted,
        rescues_rejected=len(refused), rejected_detail=refused[:6],
        plan_rejections=rejections[:6],
        n_resolved=len(documents),
        still_unresolved=len(_unresolved(documents)),
    )


def research(state: dict, tools: dict | None = None) -> dict:
    """Execute the research pass. Second entry runs the RESCUE pass, not a repeat of the first.

    `tools=None` is the fixture path: no external calls, resolved documents come from state.
    With `tools`, each entry is a callable keyed by tool name (resolve_document,
    check_freshness, live_service_lookup).
    """
    # A plan in state means the router sent us back here after observing unresolved documents.
    if state.get("research_plan"):
        return rescue_pass(state, tools)

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
    if record.get("source_domain"):
        # EXTERNAL record: the corpus resolver cannot be trusted against it (measured — see
        # tools/external_source.abstained_documents). Every document is carried through the answer,
        # marked unresolved, so the citizen still gets the complete published checklist and nothing
        # is attributed to an authority that did not issue it.
        from tools.external_source import abstained_documents

        documents = abstained_documents(record)
    elif resolve:
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
