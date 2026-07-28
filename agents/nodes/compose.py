"""compose -> validate_schema -> respond, plus the terminal branches.

This is where the G2 conditional-structure finding is acted on. `required_documents: list[str]`
cannot express the branches, disjunctions, preconditions and per-case recency windows that 63%
of the corpus contains, so a flattened answer can be confidently wrong. We cannot fix the data
model before the deadline — so compose DETECTS the constructs, DISCLOSES them in `caveats`,
PENALISES `confidence`, and QUEUES the service for human review.

That ordering matters: the confidence penalty is applied to the same object that carries the
caveat, so an answer can never present a merged multi-branch document list at 0.9 confidence.
"""
from __future__ import annotations

from agents.models import (
    AnswerOut, ClarifyOut, Envelope, ErrorOut, FreshnessResult, InvalidOut, NotFoundOut,
    ServiceOut, TimeEstimate,
)
from agents.nodes.trace import with_trace
from tools.conditional_detect import (
    caveat_lines, confidence_penalty, detect_conditionals, needs_review,
)

# FR7 (A23): an evidence-quality heuristic, NOT a calibrated probability. Disclosed as such.
BASE_CORE = 0.9
BASE_NON_CORE = 0.5
PENALTY_FRESHNESS = 0.2
PENALTY_UNRESOLVED = 0.1
PENALTY_INCOMPLETE = 0.3
CONFIDENCE_FLOOR = 0.05


def compute_confidence(*, is_core: bool, freshness_status: str, any_unresolved: bool,
                       incomplete: bool, conditional_flags: list) -> tuple[float, list[str]]:
    """Returns (confidence, reasons). Reasons are recorded in the trace so a number in the eval
    can always be traced back to the deductions that produced it."""
    score = BASE_CORE if is_core else BASE_NON_CORE
    reasons = [f"base={'core' if is_core else 'non_core'}"]

    if freshness_status != "unchanged":
        score -= PENALTY_FRESHNESS
        reasons.append(f"freshness={freshness_status}")
    if any_unresolved:
        score -= PENALTY_UNRESOLVED
        reasons.append("unresolved_document")
    if incomplete:
        score -= PENALTY_INCOMPLETE
        reasons.append("incomplete_record")
    if conditional_flags:
        p = confidence_penalty(conditional_flags)
        score -= p
        reasons.append(f"conditional_structure(-{p:.2f})=" +
                       ",".join(sorted({f.kind for f in conditional_flags})))

    return max(score, CONFIDENCE_FLOOR), reasons


FALLBACK_REASONING = ("Matched the query to a Dawlati service and assembled its published "
                      "requirements. (Deterministic composition — no model available.)")


def _fallback_reasoning(record: dict) -> str:
    """Naming the wrong source is a factual error even when it is only the log line.

    An external-source record did not come from Dawlati — Dawlati is precisely where it was NOT
    found — so the deterministic reasoning must say which site actually supplied the facts.
    """
    domain = record.get("source_domain")
    if not domain:
        return FALLBACK_REASONING
    return (f"Not published on Dawlati; assembled from the official source {domain}, which "
            f"publishes this procedure. (Deterministic composition — no model available.)")

# Hard cap on the narration wait. The free tier's latency is erratic (0.5-12.8 s for identical
# calls, one eval case reaching 40 s end-to-end); the variance is the provider's, but an
# unbounded wait would be ours. Past this we fall back to deterministic prose, which costs the
# answer nothing factual because every fact is assembled from the record either way. A plainer
# sentence beats a 40-second silence in front of an audience.
NARRATION_TIMEOUT_S = 8.0


def _evidence_brief(record: dict, documents: list, freshness, flags: list) -> str:
    """What the composer model is shown. Deliberately a SUMMARY, not the raw record.

    The model is given counts and names but is never asked to reproduce them, because anything it
    is asked to echo it can also corrupt. Keeping the evidence brief short also keeps us inside
    the 8K TPM free-tier budget on every call.
    """
    sec = record.get("sections") or {}
    resolved = sum(1 for d in documents
                   if (d.get("resolution") if isinstance(d, dict) else d.resolution) != "unresolved")
    lines = [
        f"service: {record.get('title_ar','')}",
        f"authority: {sec.get('authority') or 'not published'}",
        f"required documents: {len(documents)} listed, {resolved} resolved to a source",
        f"fees: {'published' if sec.get('fees') else 'NOT published'}",
        f"where to apply: {'published' if sec.get('where_to_apply') else 'NOT published'}",
        f"record status: {record.get('record_status','incomplete')}",
        f"source freshness: {freshness.status}",
    ]
    if flags:
        lines.append("conditional structure detected: "
                     + ", ".join(sorted({f.kind for f in flags}))
                     + " (requirements differ by applicant case)")
    return "\n".join(lines)


def narrate(state: dict, record: dict, documents: list, freshness, flags: list,
            adapter=None, system_prompt: str = ""):
    """Ask the model for `reasoning` + `summary` ONLY. Returns (reasoning, summary, meta).

    Falls back to a deterministic string whenever the model is absent or fails. That fallback is
    what makes `--offline` and the no-API-key path work, and it means a provider outage degrades
    the answer's prose rather than the answer's facts.
    """
    if adapter is None:
        return _fallback_reasoning(record), None, {"mode": "deterministic"}

    lang = state.get("language", "ar")
    user = (f"Citizen's question ({lang}): {state.get('query','')}\n\n"
            f"EVIDENCE (this is all you may rely on):\n"
            f"{_evidence_brief(record, documents, freshness, flags)}\n\n"
            f"Write `reasoning` (English, for the log) and `summary` "
            f"(in {'Arabic' if lang == 'ar' else 'English'}, 1-2 sentences, addressed to the "
            f"citizen). Do NOT list documents, fees, amounts or URLs — those are rendered "
            f"separately from verified data. If fees or details are not published, say the "
            f"official source does not state them.")
    try:
        from agents.models import Narration
        result, meta = adapter.complete(system_prompt, user, Narration,
                                        timeout=NARRATION_TIMEOUT_S)
        return result.reasoning, result.summary, {"mode": "model", **meta}
    except Exception as exc:  # noqa: BLE001 — prose is never worth failing an answer over
        return _fallback_reasoning(record), None, {"mode": "fallback", "error": str(exc)[:120]}


def compose(state: dict, curated_core: set[int] | None = None, adapter=None,
            system_prompt: str = "") -> dict:
    """Build the AnswerOut + Envelope for the happy path.

    The model contributes LANGUAGE only (`reasoning`, `summary`). Every factual field —
    documents, fees, authority, URL, freshness, confidence — is assembled here from the retrieved
    record and never round-trips through the model. That split is why the answer cannot contain a
    fabricated document even when the prose is model-written.
    """
    record = state.get("service_record") or {}
    sections = record.get("sections") or {}
    language = state.get("language", "ar")
    documents = state.get("resolved_documents") or []

    # --- the G2 finding, acted on ------------------------------------------
    flags = detect_conditionals(sections.get("required_documents"), record.get("raw_text", ""))

    fresh_raw = state.get("service_freshness") or {}
    freshness = FreshnessResult(
        status=fresh_raw.get("status", "unverified"),
        source_modified_gmt=fresh_raw.get("source_modified_gmt"),
        snapshot_modified_gmt=fresh_raw.get("snapshot_modified_gmt")
        or record.get("modified_gmt_at_crawl", ""),
        checked_at=fresh_raw.get("checked_at", ""),
        note=fresh_raw.get("note", "not checked in this run"),
    )

    incomplete = record.get("record_status") == "incomplete"
    any_unresolved = any((d.get("resolution") if isinstance(d, dict) else d.resolution)
                         == "unresolved" for d in documents)
    is_core = record.get("post_id") in (curated_core or set())

    confidence, reasons = compute_confidence(
        is_core=is_core, freshness_status=freshness.status, any_unresolved=any_unresolved,
        incomplete=incomplete, conditional_flags=flags,
    )

    caveats = caveat_lines(flags, language)
    # The citizen is entitled to know the answer did not come from the portal they were pointed at.
    # Stated FIRST, before the conditional caveats, because provenance changes how much of the rest
    # they should trust — and the freshness guarantee is genuinely weaker here (A08 change-detection
    # needs a modification timestamp this source does not publish).
    if record.get("source_domain"):
        domain = record["source_domain"]
        caveats.insert(0,
                       f"This service is not published on Dawlati. The requirements below come "
                       f"from the official site of the issuing authority ({domain}); verify "
                       f"against that page before travelling to an office."
                       if language == "en" else
                       f"هذه المعاملة غير منشورة على دولتي. المعلومات أدناه مأخوذة من الموقع "
                       f"الرسمي للجهة المصدرة ({domain})؛ يُرجى التأكد منها على تلك الصفحة قبل "
                       f"التوجه إلى الدائرة.")
    if incomplete:
        caveats.append("The official source has not published complete details for this service."
                       if language == "en" else
                       "لم ينشر المصدر الرسمي تفاصيل كاملة لهذه المعاملة.")

    review_reasons: list[str] = []
    if needs_review(flags):
        review_reasons.append("conditional_structure")
    if freshness.status != "unchanged":
        review_reasons.append("stale_source" if freshness.status == "changed"
                              else "unverified_source")
    if any_unresolved:
        review_reasons.append("unresolved_document")
    if incomplete:
        review_reasons.append("incomplete_record")

    reasoning, summary, narr_meta = narrate(state, record, documents, freshness, flags,
                                            adapter=adapter, system_prompt=system_prompt)

    answer = AnswerOut(
        service=ServiceOut(
            name_ar=record.get("title_ar", ""),
            name_en=record.get("title_en"),
            source_url=record.get("url", ""),
            authority=sections.get("authority"),
            fees=sections.get("fees"),
            where_to_apply=sections.get("where_to_apply"),
            freshness=freshness,
            record_status=record.get("record_status", "incomplete"),
        ),
        required_documents=documents,  # type: ignore[arg-type]
        time_estimate=state.get("time_estimate") or TimeEstimate(computable=False),
        caveats=caveats,
        conditional_flags=flags,
        summary=summary,
    )
    env = Envelope(
        action="answer",
        reasoning=reasoning,
        confidence=confidence,
        language=language,
        needs_human_review=bool(review_reasons),
        review_reasons=review_reasons,  # type: ignore[arg-type]
        output=answer,
    )
    return with_trace(state, "compose", {"final_response": env.model_dump()},
                      confidence=round(confidence, 3), confidence_reasons=reasons,
                      conditional_flags=[f.kind for f in flags],
                      needs_human_review=bool(review_reasons),
                      narration=narr_meta.get("mode"),
                      narration_latency_s=narr_meta.get("latency_s"))


# ---------------------------------------------------------------- terminal branches
def _terminal(state: dict, action: str, output, confidence: float, node: str) -> dict:
    env = Envelope(
        action=action,  # type: ignore[arg-type]
        reasoning=state.get("reasoning", f"Terminated at {node}."),
        confidence=confidence,
        language=state.get("language", "ar"),
        output=output,
    )
    return with_trace(state, node, {"final_response": env.model_dump()}, action=action)


def respond_invalid(state: dict) -> dict:
    raw = state.get("invalid") or {}
    out = InvalidOut(reason_code=raw.get("reason_code", "gibberish"),
                     message=raw.get("message", "Unsupported request."))
    # a refusal is a confident, correct outcome — not a low-confidence guess
    return _terminal(state, "invalid_request", out, 1.0, "respond_invalid")


def respond_not_found(state: dict) -> dict:
    out = NotFoundOut(
        message=("No matching service was found on Dawlati." if state.get("language") == "en"
                 else "لم يتم العثور على معاملة مطابقة على دولتي."),
        suggestions=(state.get("suggestions") or [])[:3],
    )
    return _terminal(state, "service_not_found", out, 0.3, "respond_not_found")


def respond_clarify(state: dict) -> dict:
    out = ClarifyOut(
        question=("Which of these did you mean?" if state.get("language") == "en"
                  else "أي من هذه المعاملات تقصد؟"),
        candidates=(state.get("candidates") or [])[:3],
    )
    return _terminal(state, "clarification_needed", out, 0.4, "respond_clarify")


def respond_error(state: dict) -> dict:
    out = ErrorOut(stage=state.get("error_stage", "unknown"),
                   detail=state.get("error_detail", "Unhandled error."))
    return _terminal(state, "error", out, 0.0, "respond_error")


def validate_schema(state: dict) -> dict:
    """Re-validate the envelope before it leaves the graph (FR9).

    Cheap, and it is the last place a malformed payload can be caught before it reaches the UI
    or the eval harness. A failure here routes to the error branch rather than raising, so the
    demo degrades to a handled error instead of a traceback on screen.
    """
    raw = state.get("final_response")
    if raw is None:
        return with_trace(state, "validate_schema",
                          {"error_stage": "validate_schema", "error_detail": "no response built",
                           "schema_ok": False}, ok=False)
    try:
        Envelope.model_validate(raw)
        return with_trace(state, "validate_schema", {"schema_ok": True}, ok=True)
    except Exception as e:  # noqa: BLE001 — any validation failure must route, not raise
        return with_trace(state, "validate_schema",
                          {"error_stage": "validate_schema", "error_detail": str(e)[:200],
                           "schema_ok": False}, ok=False)


def respond(state: dict) -> dict:
    """Terminal node — the response is already built and validated."""
    return with_trace(state, "respond", {},
                      action=(state.get("final_response") or {}).get("action"))
