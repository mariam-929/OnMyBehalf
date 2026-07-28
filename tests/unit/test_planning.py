"""The guardrails between the model and the citizen's answer.

Every test here runs without a model, a network or a graph. The measured failures that motivated
the acceptance test are pinned as cases: a naive alias retry resolved «طلب مقدم» to the Directorate
of ANTIQUITIES at match_score 0.7879 and «جواز سفر الزوجه الصالح» to the Directorate of ANIMAL
WEALTH at 0.7402, both scoring HIGHER than a correct rescue at 0.6936. No confidence threshold
separates those, so the check is structural.
"""
from __future__ import annotations

from agents.planning import (
    MAX_PLAN_STEPS, accept_rescue, authority_family, compile_plan, deterministic_plan,
)

PERSONAL_STATUS = "المديرية العامة للأحوال الشخصية – دائرة شؤون الجنسية والقضايا"
PERSONAL_STATUS_PAREN = "المديرية العامة للأحوال الشخصية (أقلام النفوس)"
PERSONAL_STATUS_OTHER = "المديرية العامة للأحوال الشخصية – دوائر وأقلام النفوس"
ANTIQUITIES = "Directorate العامة للآثار – دائرة الديوان"
ANIMAL_WEALTH = "مديرية الثروة الحيوانية – مصلحة إنتاج وتربية"


def _record(n: int = 3, post_id: int = 11476) -> dict:
    return {"post_id": post_id,
            "sections": {"required_documents": [f"مستند {i}" for i in range(1, n + 1)],
                         "where_to_apply": PERSONAL_STATUS}}


# ============================================================ acceptance test
def test_antiquities_rescue_is_rejected_despite_high_score():
    """The measured 0.7879 false positive. Score is high; the authority is absurd."""
    ok, why = accept_rescue(
        {"resolution": "corpus", "where_to_obtain": ANTIQUITIES, "match_score": 0.7879},
        PERSONAL_STATUS)
    assert ok is False
    assert "mismatch" in why


def test_animal_wealth_rescue_is_rejected_despite_high_score():
    """A passport copy resolving to the livestock directorate — the horse passport, again."""
    ok, _ = accept_rescue(
        {"resolution": "corpus", "where_to_obtain": ANIMAL_WEALTH, "match_score": 0.7402},
        PERSONAL_STATUS)
    assert ok is False


def test_consistent_rescue_is_accepted_even_with_a_lower_score():
    """0.6936 is LOWER than both rejected cases. Structure decides, not confidence."""
    ok, why = accept_rescue(
        {"resolution": "corpus", "where_to_obtain": PERSONAL_STATUS_OTHER, "match_score": 0.6936},
        PERSONAL_STATUS)
    assert ok is True
    assert "consistent" in why


def test_score_is_never_consulted():
    """Same authority, absurd scores, both directions — the decision must not move."""
    good = {"resolution": "corpus", "where_to_obtain": PERSONAL_STATUS_OTHER}
    assert accept_rescue({**good, "match_score": 0.01}, PERSONAL_STATUS)[0] is True
    bad = {"resolution": "corpus", "where_to_obtain": ANTIQUITIES}
    assert accept_rescue({**bad, "match_score": 0.99}, PERSONAL_STATUS)[0] is False


def test_curated_lookup_table_needs_no_structural_check():
    ok, why = accept_rescue(
        {"resolution": "lookup_table", "where_to_obtain": "أي مكان"}, PERSONAL_STATUS)
    assert ok is True and "curated" in why


def test_unresolved_is_not_a_rescue():
    assert accept_rescue({"resolution": "unresolved"}, PERSONAL_STATUS)[0] is False


def test_fails_closed_when_the_service_has_no_authority():
    """Cannot verify must mean refuse, not trust."""
    ok, why = accept_rescue(
        {"resolution": "corpus", "where_to_obtain": PERSONAL_STATUS_OTHER}, None)
    assert ok is False and "cannot verify" in why


def test_fails_closed_when_the_rescue_has_no_authority():
    ok, _ = accept_rescue({"resolution": "corpus", "where_to_obtain": None}, PERSONAL_STATUS)
    assert ok is False


def test_authority_family_ignores_subdepartment_and_punctuation():
    a = authority_family(PERSONAL_STATUS)
    b = authority_family(PERSONAL_STATUS_PAREN)
    c = authority_family(PERSONAL_STATUS_OTHER)
    assert a == b == c
    assert authority_family(ANTIQUITIES) != a
    assert authority_family(None) is None and authority_family("   ") is None


# ============================================================ plan compilation
def test_invented_document_name_cannot_reach_the_screen():
    """THE anti-hallucination test. An alias is a search key; the display name is the record's."""
    plan = {"plan": [{"tool": "resolve_document",
                      "args": {"doc_index": 0, "alias": "وثيقة مختلقة تماما"}}]}
    steps, _ = compile_plan(plan, _record(3))
    step = next(s for s in steps if s["tool"] == "resolve_document")
    assert step["display_name"] == "مستند 1"            # from the record
    assert step["search_key"] == "وثيقة مختلقة تماما"   # used only to search
    assert step["is_alias"] is True


def test_out_of_range_doc_index_is_dropped_with_a_reason():
    steps, rejections = compile_plan(
        {"plan": [{"tool": "resolve_document", "args": {"doc_index": 99}}]}, _record(3))
    assert not [s for s in steps if s["tool"] == "resolve_document"]
    assert any("out of range" in r for r in rejections)


def test_non_integer_doc_index_is_dropped():
    for bad in ("0", 1.5, None, True, {"a": 1}):
        steps, rejections = compile_plan(
            {"plan": [{"tool": "resolve_document", "args": {"doc_index": bad}}]}, _record(3))
        assert not [s for s in steps if s["tool"] == "resolve_document"], bad
        assert rejections


def test_disallowed_tool_is_dropped():
    steps, rejections = compile_plan(
        {"plan": [{"tool": "os.system", "args": {"cmd": "rm -rf /"}}]}, _record())
    assert all(s["tool"] in ("check_freshness", "live_service_lookup") for s in steps)
    assert any("not permitted" in r for r in rejections)


def test_freshness_target_is_forced_to_the_retrieved_record():
    """The model must not be able to attach another service's freshness to this answer."""
    steps, rejections = compile_plan(
        {"plan": [{"tool": "check_freshness", "args": {"post_id": 99999}}]},
        _record(post_id=11476))
    fresh = [s for s in steps if s["tool"] == "check_freshness"]
    assert fresh and all(s["post_id"] == 11476 for s in fresh)
    assert any("overridden" in r for r in rejections)


def test_plan_is_capped():
    plan = {"plan": [{"tool": "resolve_document", "args": {"doc_index": i}} for i in range(12)]}
    steps, rejections = compile_plan(plan, _record(12))
    assert len([s for s in steps if s["tool"] == "resolve_document"]) <= MAX_PLAN_STEPS
    assert any("exceeded" in r for r in rejections)


def test_duplicate_document_indices_do_not_burn_budget():
    plan = {"plan": [{"tool": "resolve_document", "args": {"doc_index": 0}} for _ in range(4)]}
    steps, rejections = compile_plan(plan, _record(3))
    assert len([s for s in steps if s["tool"] == "resolve_document"]) == 1
    assert any("duplicate" in r for r in rejections)


def test_both_external_calls_are_added_when_the_model_omits_them():
    """>=2 external tool calls is a brief requirement, not a model preference."""
    steps, _ = compile_plan(
        {"plan": [{"tool": "resolve_document", "args": {"doc_index": 0}}]}, _record(3))
    tools = [s["tool"] for s in steps]
    assert "check_freshness" in tools and "live_service_lookup" in tools


def test_external_calls_are_not_duplicated_when_the_model_does_plan_them():
    plan = {"plan": [{"tool": "check_freshness", "args": {}},
                     {"tool": "live_service_lookup", "args": {"query": "x"}}]}
    steps, _ = compile_plan(plan, _record(3))
    assert [s["tool"] for s in steps].count("check_freshness") == 1
    assert [s["tool"] for s in steps].count("live_service_lookup") == 1


def test_garbage_plans_never_raise_and_still_schedule_the_externals():
    for junk in (None, {}, [], "hello", {"plan": "not a list"}, {"plan": [None, 3, "x"]},
                 {"nope": []}, 42):
        steps, _ = compile_plan(junk, _record(3), query="q")
        tools = [s["tool"] for s in steps]
        assert "check_freshness" in tools and "live_service_lookup" in tools, junk


def test_live_lookup_falls_back_to_the_user_query():
    steps, _ = compile_plan({"plan": [{"tool": "live_service_lookup", "args": {}}]},
                            _record(), query="سؤال المستخدم")
    step = next(s for s in steps if s["tool"] == "live_service_lookup")
    assert step["query"] == "سؤال المستخدم"


def test_record_without_post_id_schedules_no_freshness_call():
    rec = {"sections": {"required_documents": ["أ"], "where_to_apply": PERSONAL_STATUS}}
    steps, _ = compile_plan({"plan": []}, rec)
    assert not [s for s in steps if s["tool"] == "check_freshness"]


# ============================================================ fallback
def test_deterministic_fallback_retries_nothing():
    """The no-model path must equal today's behaviour: no rescues at all."""
    plan = deterministic_plan(query="q")
    assert not [s for s in plan["plan"] if s["tool"] == "resolve_document"]
    assert plan["done"] is True


def test_deterministic_fallback_still_schedules_both_external_calls():
    steps, _ = compile_plan(deterministic_plan(query="q"), _record(3))
    tools = [s["tool"] for s in steps]
    assert "check_freshness" in tools and "live_service_lookup" in tools
