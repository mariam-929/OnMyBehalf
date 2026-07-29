"""The reasoning loop itself: the retry-or-stop decision, the planner node, the rescue pass.

`test_planning.py` covers the pure guardrails. This covers the machinery that USES them, and above
all that the loop TERMINATES. The only evidence it terminated used to be that a human watched it
terminate once — and the bug that made it loop was invisible to every existing test: `research_plan`
was returned by the planner but not declared in `AgentState`, so LangGraph dropped the key, the
plan never arrived, and the graph span until the recursion limit while re-running a live HTTP call
each time. It surfaced as a network hang, not as a loop.

Nothing here touches a model or the network: the adapter is a stub and the tools are fakes.
"""
from __future__ import annotations

import pytest

from agents.graph import route_after_research, run
from agents.models import IntentResult, Narration, ResearchPlan
from agents.nodes.research import MAX_REPLANS, plan_research, rescue_pass
from agents.state import AgentState

AUTHORITY = "المديرية العامة للأحوال الشخصية – دائرة شؤون الجنسية والقضايا"
SAME_FAMILY = "المديرية العامة للأحوال الشخصية – دوائر النفوس"
OTHER_FAMILY = "مديرية الثروة الحيوانية – مصلحة إنتاج"


def _record(n: int = 3, post_id: int = 11476) -> dict:
    return {"post_id": post_id, "type": "ministry_service_ser", "title_ar": "خدمة",
            "modified_gmt": "2026-07-01T00:00:00",
            "sections": {"required_documents": [f"مستند {i}" for i in range(1, n + 1)],
                         "where_to_apply": AUTHORITY}}


def _docs(n: int = 3, unresolved: tuple[int, ...] = (0,)) -> list[dict]:
    out = []
    for i in range(n):
        if i in unresolved:
            out.append({"name_ar": f"مستند {i + 1}", "resolution": "unresolved"})
        else:
            out.append({"name_ar": f"مستند {i + 1}", "resolution": "corpus",
                        "where_to_obtain": SAME_FAMILY})
    return out


class StubAdapter:
    """Returns a fixed plan, and a valid stand-in for the graph's other two model calls.

    One adapter serves classify_intent, plan_research and compose, so a stub that always returned a
    ResearchPlan broke the graph before it ever reached the planner. Dispatch on the requested
    schema instead. Records the planner's user message so tests can assert what the model was shown.
    """

    def __init__(self, plan: dict | None = None, raises: Exception | None = None):
        self.plan = plan if plan is not None else {
            "plan": [{"tool": "resolve_document", "doc_index": 0, "alias": "بيان قيد"}],
            "done": True}
        self.raises = raises
        self.seen_user = None
        self.seen_kwargs = {}

    def complete(self, system, user, schema_model, **kwargs):
        if schema_model is ResearchPlan:
            self.seen_user = user
            self.seen_kwargs = kwargs
            if self.raises:
                raise self.raises
            return ResearchPlan.model_validate(self.plan), {"latency_s": 0.4}
        if schema_model is IntentResult:
            return IntentResult(intent="service_query", reason="stub",
                                language_advisory="ar"), {"latency_s": 0.1}
        if schema_model is Narration:
            return Narration(reasoning="stub reasoning", summary="ملخص"), {"latency_s": 0.1}
        raise AssertionError(f"stub asked for an unexpected schema: {schema_model!r}")


def _tools(where: str = SAME_FAMILY, resolution: str = "corpus") -> dict:
    return {
        "resolve_document": lambda name: {"name_ar": name, "resolution": resolution,
                                          "where_to_obtain": where, "match_score": 0.8},
        "check_freshness": lambda pid: {"status": "unchanged", "snapshot_modified_gmt": "x",
                                        "checked_at": "y", "note": ""},
        "live_service_lookup": lambda q: {"query": q, "exists": True, "is_newer": False},
    }


# ==================================================== the state-schema regression
def test_research_plan_is_declared_in_the_state_schema():
    """The bug that caused the infinite loop. LangGraph drops undeclared keys silently, so no
    behavioural test catches this cheaply — assert the declaration directly."""
    assert "research_plan" in AgentState.__annotations__


# ==================================================== the retry-or-stop decision
def test_replans_when_a_document_is_unresolved_and_budget_remains():
    assert route_after_research(
        {"resolved_documents": _docs(unresolved=(0,)), "service_record": _record(),
         "replans_used": 0, "trace_events": []}) == "replan"


def test_stops_when_everything_resolved():
    assert route_after_research(
        {"resolved_documents": _docs(unresolved=()), "service_record": _record(),
         "replans_used": 0, "trace_events": []}) == "done"


def test_stops_once_the_replan_budget_is_spent():
    assert route_after_research(
        {"resolved_documents": _docs(unresolved=(0,)), "service_record": _record(),
         "replans_used": MAX_REPLANS, "trace_events": []}) == "done"


def test_stops_on_the_trace_budget_even_if_the_counter_was_lost():
    """The hardening. If a state key goes missing again, planner visits in the trace still bound it."""
    assert route_after_research(
        {"resolved_documents": _docs(unresolved=(0,)), "service_record": _record(),
         "replans_used": 0,
         "trace_events": [{"node": "plan_research"}]}) == "done"


def test_stops_without_a_record_to_plan_against():
    assert route_after_research(
        {"resolved_documents": _docs(unresolved=(0,)), "replans_used": 0,
         "trace_events": []}) == "done"


def test_decision_tolerates_empty_and_malformed_state():
    for state in ({}, {"resolved_documents": []}, {"resolved_documents": [None]},
                  {"resolved_documents": [{}], "service_record": _record()}):
        assert route_after_research(state) in ("replan", "done")


# ==================================================== the planner node
def test_planner_without_a_model_retries_nothing():
    out = plan_research({"query": "q", "service_record": _record(),
                         "resolved_documents": _docs(), "trace_events": []}, adapter=None)
    event = out["trace_events"][-1]
    assert event["mode"] == "fixture"
    assert not [s for s in out["research_plan"]["plan"] if s["tool"] == "resolve_document"]


def test_planner_skips_the_model_when_nothing_is_unresolved():
    stub = StubAdapter()
    out = plan_research({"query": "q", "service_record": _record(),
                         "resolved_documents": _docs(unresolved=()), "trace_events": []},
                        adapter=stub)
    assert out["trace_events"][-1]["mode"] == "nothing_to_retry"
    assert stub.seen_user is None          # no model call was made at all


def test_planner_falls_back_and_records_the_error_when_the_model_fails():
    stub = StubAdapter(raises=RuntimeError("429 rate limit"))
    out = plan_research({"query": "q", "service_record": _record(),
                         "resolved_documents": _docs(), "trace_events": []}, adapter=stub)
    event = out["trace_events"][-1]
    assert event["mode"] == "fallback"
    assert "429" in event["error"]
    assert not [s for s in out["research_plan"]["plan"] if s["tool"] == "resolve_document"]


def test_planner_records_the_model_plan_and_counts_retries():
    stub = StubAdapter({"plan": [{"tool": "resolve_document", "doc_index": 0, "alias": "أ"},
                                 {"tool": "resolve_document", "doc_index": 1, "alias": "ب"}],
                        "done": True})
    out = plan_research({"query": "q", "service_record": _record(),
                         "resolved_documents": _docs(unresolved=(0, 1)), "trace_events": []},
                        adapter=stub)
    event = out["trace_events"][-1]
    assert event["mode"] == "model" and event["retries_planned"] == 2
    assert out["research_plan"]["plan"][0]["doc_index"] == 0


def test_planner_shows_the_model_indices_and_bounds_the_request():
    """The model must be able to address documents by index, and the request must stay small
    enough to survive the free tier's token budget."""
    stub = StubAdapter()
    plan_research({"query": "q", "service_record": _record(12),
                   "resolved_documents": _docs(12, unresolved=tuple(range(12))),
                   "trace_events": []}, adapter=stub)
    assert "[0]" in stub.seen_user and "[5]" in stub.seen_user
    assert "[6]" not in stub.seen_user          # capped at six
    assert stub.seen_kwargs.get("reasoning_effort") == "low"
    assert stub.seen_kwargs.get("timeout")


# ==================================================== the rescue pass
def test_accepted_rescue_is_displayed_with_the_RECORD_wording_not_the_alias():
    """Anti-hallucination, at node level: the alias searched, the record is displayed."""
    state = {"query": "q", "service_record": _record(), "resolved_documents": _docs(),
             "replans_used": 0, "trace_events": [],
             "research_plan": {"plan": [{"tool": "resolve_document", "doc_index": 0,
                                         "alias": "كلمة مختلقة"}], "done": True}}
    out = rescue_pass(state, tools=_tools())
    assert out["resolved_documents"][0]["resolution"] == "corpus"
    assert out["resolved_documents"][0]["name_ar"] == "مستند 1"      # from the record
    assert out["trace_events"][-1]["rescues_accepted"] == 1


def test_rejected_rescue_leaves_the_document_unresolved():
    state = {"query": "q", "service_record": _record(), "resolved_documents": _docs(),
             "replans_used": 0, "trace_events": [],
             "research_plan": {"plan": [{"tool": "resolve_document", "doc_index": 0}],
                               "done": True}}
    out = rescue_pass(state, tools=_tools(where=OTHER_FAMILY))   # wrong directorate
    assert out["resolved_documents"][0]["resolution"] == "unresolved"
    event = out["trace_events"][-1]
    assert event["rescues_accepted"] == 0 and event["rescues_rejected"] == 1
    assert "mismatch" in event["rejected_detail"][0]["reason"]


def test_rescue_pass_always_spends_the_budget():
    """Whether or not anything was rescued — otherwise the loop could run again."""
    for tools in (_tools(), _tools(where=OTHER_FAMILY), None):
        out = rescue_pass({"query": "q", "service_record": _record(),
                           "resolved_documents": _docs(), "replans_used": 0,
                           "trace_events": [],
                           "research_plan": {"plan": [], "done": True}}, tools=tools)
        assert out["replans_used"] == 1


def test_rescue_pass_ignores_an_index_outside_the_document_list():
    state = {"query": "q", "service_record": _record(3), "resolved_documents": _docs(3),
             "replans_used": 0, "trace_events": [],
             "research_plan": {"plan": [{"tool": "resolve_document", "doc_index": 99}],
                               "done": True}}
    out = rescue_pass(state, tools=_tools())
    assert len(out["resolved_documents"]) == 3
    assert out["trace_events"][-1]["rescues_accepted"] == 0


def test_rescue_pass_never_changes_the_document_count():
    """Step 0's completeness invariant must survive the loop."""
    state = {"query": "q", "service_record": _record(5),
             "resolved_documents": _docs(5, unresolved=(0, 2, 4)), "replans_used": 0,
             "trace_events": [],
             "research_plan": {"plan": [{"tool": "resolve_document", "doc_index": i}
                                        for i in (0, 2, 4)], "done": True}}
    out = rescue_pass(state, tools=_tools())
    assert len(out["resolved_documents"]) == 5


# ==================================================== TERMINATION
@pytest.mark.parametrize("plan", [
    {"plan": [{"tool": "resolve_document", "doc_index": 0, "alias": "أ"}], "done": True},
    {"plan": [], "done": True},                                    # planner declines to retry
    {"plan": [{"tool": "resolve_document", "doc_index": 0}], "done": False},   # refuses to stop
])
def test_the_loop_visits_the_planner_at_most_once(plan):
    """The regression test for the infinite loop, whatever the model says.

    The rescue deliberately cannot succeed here (the resolver returns the WRONG directorate, so
    every rescue is refused), which keeps a document unresolved and keeps the re-plan condition
    true. Only the budget can stop it.
    """
    state = run("سؤال", adapter=StubAdapter(plan), tools=_tools(where=OTHER_FAMILY),
                search_fn=lambda q, k=5: [], service_record=_record(3),
                retrieved=[{"post_id": 11476, "title_ar": "خدمة", "rrf_score": 0.1,
                            "dense_cos": 0.9, "bm25_rank": 1}])
    visits = [e for e in state["trace_events"] if e.get("node") == "plan_research"]
    assert len(visits) <= MAX_REPLANS
    assert state.get("replans_used", 0) <= MAX_REPLANS
    assert state.get("final_response")          # it reached an answer rather than spinning
