"""Plan validation and rescue acceptance — the code that stands between the model and the answer.

The research planner lets the model decide WHICH documents to look up and, on a re-plan, WHAT
SEARCH KEY to try. It never lets the model decide what the citizen is shown. Everything here is a
pure function so the guardrails can be tested without a model, a network, or a graph.

WHAT THE MODEL DOES AND DOES NOT PLAN. The first resolution pass is NOT planned: every published
document is resolved deterministically, because completeness is a system invariant. Routing it
through a model plan would re-cap resolution at MAX_PLAN_STEPS and silently truncate the citizen's
checklist again — the bug Step 0 removed. This mirrors N3, where per-document freshness is a
deterministic system step rather than a model decision.

What the model DOES plan is the RESCUE pass: given the documents that came back unresolved, which
ones are worth retrying and with what search key, inside a budget. That is a real decision under
uncertainty, grounded in an observation rather than speculation, and its outcome is measurable.

Two separate jobs:

`compile_plan` turns a model-proposed rescue plan into executable steps, clamping every field that
could carry a fabrication:
  * documents are addressed by INDEX into the record, never by free text, because
    `resolve_document(name)` echoes its input into `ResolvedDocument.name_ar` — which the UI
    displays. A model-invented name would therefore appear on screen as a required document.
  * an `alias` is a SEARCH KEY only. The displayed name always comes from the record.
  * `check_freshness` is forced to the record's own post_id, so freshness from a different service
    cannot be attached to this answer.
  * both live calls are added whether the model planned them or not — the brief requires >=2
    external tool calls and that is not a model's decision to make.

`accept_rescue` decides whether an alias retry may be believed. Measured on the demo services, a
naive retry rescued 6 of 9 unresolved documents but three were wrong: «طلب مقدم» resolved to the
Directorate of ANTIQUITIES (0.7879) and «جواز سفر الزوجه الصالح» to the Directorate of ANIMAL
WEALTH (0.7402) — both scoring HIGHER than a correct rescue at 0.6936. So `match_score` cannot
separate right from wrong, and a threshold tuned to make that sample work would be fitted on four
points. This project has already retracted two results for exactly that.

The separator used instead is structural: a document required by a civil-registry procedure is not
issued by the antiquities directorate. A rescue is believed only when its issuing authority shares
a directorate with the service's own, or when it came from the human-curated lookup table.
"""
from __future__ import annotations

import re
from typing import Any

from tools.text_norm import normalize_ar

ALLOWED_TOOLS = ("resolve_document", "check_freshness", "live_service_lookup")
# N3 cap on MODEL-scheduled calls. It bounds the RESCUE pass only. It must never be applied to
# first-pass document resolution: that is what silently dropped 23 of #11610's 29 requirements.
MAX_PLAN_STEPS = 6
EXTERNAL_TOOLS = ("check_freshness", "live_service_lookup")

# An authority string looks like "المديرية العامة للأحوال الشخصية – دائرة شؤون الجنسية والقضايا":
# a directorate, then a sub-department. The head is what identifies the institution.
_SPLIT_HEAD = re.compile(r"\s*[–—\-]\s*|\s*\(")


def authority_family(authority: str | None) -> str | None:
    """The institution part of an authority string, normalised for comparison.

    Returns None when there is nothing to compare, which callers must treat as "cannot verify"
    rather than "verified" — see `accept_rescue`.
    """
    if not authority or not str(authority).strip():
        return None
    head = _SPLIT_HEAD.split(str(authority).strip(), maxsplit=1)[0]
    head = normalize_ar(head).strip()
    return head or None


def accept_rescue(resolved: dict, service_authority: str | None) -> tuple[bool, str]:
    """May an alias-retry result be shown to the citizen? Returns (accepted, reason).

    Fails CLOSED: when the service publishes no authority we cannot run the consistency check, so
    an alias rescue is refused rather than trusted. A document staying unresolved is a visible,
    honest gap; a document attributed to the wrong ministry is a fabrication the citizen would act
    on.
    """
    if not resolved or resolved.get("resolution") == "unresolved":
        return False, "did not resolve"

    # The curated lookup table is human-verified, so it needs no structural check.
    if resolved.get("resolution") == "lookup_table":
        return True, "human-curated lookup table"

    want = authority_family(service_authority)
    got = authority_family(resolved.get("where_to_obtain"))
    if want is None:
        return False, "service publishes no authority — cannot verify consistency, refusing"
    if got is None:
        return False, "resolved record publishes no authority — cannot verify consistency"
    if want == got:
        return True, "authority consistent with the service"
    return False, f"authority mismatch: service={want[:34]!r} resolved={got[:34]!r}"


def step_field(raw: dict, name: str) -> Any:
    """Read a plan-step argument from either the flat or the nested `args` shape.

    The schema sent to the model is flat (strict json_schema cannot express an open `args` object).
    The nested form is still accepted so a model that emits it, or an older recorded plan, is not
    discarded over shape alone.
    """
    if name in raw:
        return raw.get(name)
    args = raw.get("args")
    return args.get(name) if isinstance(args, dict) else None


def _clamp_resolve_step(raw: dict, doc_names: list[str]) -> tuple[dict | None, str | None]:
    idx = step_field(raw, "doc_index")
    if not isinstance(idx, int) or isinstance(idx, bool):
        return None, f"doc_index missing or not an integer: {idx!r}"
    if not (0 <= idx < len(doc_names)):
        return None, f"doc_index {idx} out of range (record has {len(doc_names)} documents)"

    display = doc_names[idx]                      # ALWAYS the record's wording
    alias = step_field(raw, "alias")
    alias = str(alias).strip() if isinstance(alias, str) and alias.strip() else None
    return {
        "tool": "resolve_document",
        "doc_index": idx,
        "display_name": display,
        "search_key": alias or display,
        "is_alias": alias is not None,
    }, None


def compile_plan(plan: Any, record: dict, *, query: str = "") -> tuple[list[dict], list[str]]:
    """Validate a model plan into executable steps. Returns (steps, rejections).

    `plan` is whatever the model produced — possibly None, malformed, or hostile. Nothing here
    raises; anything unusable is dropped with a recorded reason, and an empty or absent plan
    degrades to the deterministic behaviour the system had before planning existed.
    """
    doc_names = ((record or {}).get("sections") or {}).get("required_documents") or []
    post_id = (record or {}).get("post_id")
    rejections: list[str] = []
    steps: list[dict] = []
    seen_docs: set[int] = set()

    raw_steps = []
    if isinstance(plan, dict) and isinstance(plan.get("plan"), list):
        raw_steps = plan["plan"]
    elif plan not in (None, {}, []):
        rejections.append("plan is not an object with a 'plan' list — ignored")

    for raw in raw_steps:
        if len(steps) >= MAX_PLAN_STEPS:
            rejections.append(f"plan exceeded {MAX_PLAN_STEPS} steps — remainder dropped")
            break
        if not isinstance(raw, dict):
            rejections.append("step is not an object")
            continue
        tool = raw.get("tool")
        if tool not in ALLOWED_TOOLS:
            rejections.append(f"tool not permitted: {tool!r}")
            continue

        if tool == "resolve_document":
            step, why = _clamp_resolve_step(raw, doc_names)
            if step is None:
                rejections.append(why or "invalid resolve_document step")
                continue
            if step["doc_index"] in seen_docs:
                rejections.append(f"duplicate doc_index {step['doc_index']} — dropped")
                continue
            seen_docs.add(step["doc_index"])
            steps.append(step)

        elif tool == "check_freshness":
            # The target is never the model's choice.
            asked = step_field(raw, "post_id")
            if asked not in (None, post_id):
                rejections.append(
                    f"check_freshness post_id {asked!r} overridden with the "
                    f"retrieved record's {post_id!r}")
            if post_id is not None:
                steps.append({"tool": "check_freshness", "post_id": post_id})

        elif tool == "live_service_lookup":
            q = step_field(raw, "query")
            steps.append({"tool": "live_service_lookup",
                          "query": str(q).strip() if isinstance(q, str) and q.strip() else query})

    # The two external calls are a brief requirement, not a preference. Add whatever the model
    # left out, so a timed-out or lazy plan cannot cost a graded criterion.
    for tool in EXTERNAL_TOOLS:
        if any(s["tool"] == tool for s in steps):
            continue
        if tool == "check_freshness" and post_id is not None:
            steps.append({"tool": "check_freshness", "post_id": post_id})
        elif tool == "live_service_lookup":
            steps.append({"tool": "live_service_lookup", "query": query})

    return steps, rejections


def deterministic_plan(*, query: str = "") -> dict:
    """The rescue plan used when there is no model, the call fails, or the plan is unusable.

    It retries NOTHING. That is deliberate: today's system performs no alias retries, so refusing
    to retry is exactly the current behaviour and the fallback cannot make anything worse. The two
    external calls are still scheduled because they are a brief requirement.

    Note this is a RESCUE plan. First-pass resolution of every published document happens
    unconditionally in the research node and is never expressed as a plan.
    """
    return {
        "plan": [{"tool": "check_freshness", "args": {}},
                 {"tool": "live_service_lookup", "args": {"query": query}}],
        "done": True,
    }
