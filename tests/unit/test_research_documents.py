"""The answer must carry EVERY document the source publishes.

Regression tests for a silent truncation: `MAX_MODEL_TOOL_CALLS` (the N3 cap on model-scheduled
tool calls) was being applied to local document resolution, and `compose` passes
`resolved_documents` straight into `AnswerOut.required_documents` with no backfill. The result was
that #11610 — 29 published documents — produced an answer listing 6, dropping 23 requirements with
no warning in the answer, the confidence score, or the trace. 25 of 193 services were affected.

These tests use a fake resolver, so they are fast, offline, and independent of corpus contents.
"""
from __future__ import annotations

import pytest

from agents.nodes.research import MAX_MODEL_TOOL_CALLS, research


def _record(n_docs: int, post_id: int = 11610) -> dict:
    return {
        "post_id": post_id,
        "type": "ministry_service_ser",
        "title_ar": "خدمة اختبار",
        "sections": {"required_documents": [f"مستند رقم {i}" for i in range(1, n_docs + 1)]},
    }


def _tools(seen: list[str] | None = None) -> dict:
    """Local resolver stand-in. Echoes the name the way the real one does."""
    def resolve(name_ar: str) -> dict:
        if seen is not None:
            seen.append(name_ar)
        return {"name_ar": name_ar, "resolution": "corpus", "where_to_obtain": "مكان ما",
                "match_score": 0.9, "needs_human_review": False}

    return {
        "resolve_document": resolve,
        "check_freshness": lambda pid: {"status": "unchanged", "snapshot_modified_gmt": "x",
                                        "checked_at": "y", "note": ""},
        "live_service_lookup": lambda q: {"query": q, "exists": True, "is_newer": False},
    }


@pytest.mark.parametrize("n_docs", [0, 1, 5, 6, 7, 17, 29])
def test_every_published_document_reaches_the_answer(n_docs):
    """The invariant: one resolved entry per published document, at any list length."""
    out = research({"query": "q", "service_record": _record(n_docs)}, tools=_tools())
    assert len(out["resolved_documents"]) == n_docs


def test_the_worst_service_in_the_corpus_is_not_truncated():
    """#11610 publishes 29 documents. The bug returned exactly MAX_MODEL_TOOL_CALLS of them."""
    out = research({"query": "q", "service_record": _record(29)}, tools=_tools())
    assert len(out["resolved_documents"]) == 29
    assert len(out["resolved_documents"]) != MAX_MODEL_TOOL_CALLS


def test_no_document_is_silently_substituted_or_reordered():
    """Resolution must preserve the source's wording and order, not just the count."""
    record = _record(9)
    source = record["sections"]["required_documents"]
    out = research({"query": "q", "service_record": record}, tools=_tools())
    assert [d["name_ar"] for d in out["resolved_documents"]] == source


def test_trace_exposes_the_completeness_invariant():
    """The evidence artefact must be enough to audit this without re-running the agent."""
    out = research({"query": "q", "service_record": _record(17)}, tools=_tools())
    event = [e for e in out["trace_events"] if e["node"] == "research"][-1]
    assert event["n_source_documents"] == 17
    assert event["n_resolved"] == 17
    assert event["documents_complete"] is True


def test_model_call_budget_still_bounds_model_scheduled_calls():
    """Removing the truncation must not remove the N3 cap it was confused with."""
    assert MAX_MODEL_TOOL_CALLS == 6


def test_every_document_is_actually_looked_up():
    """Count alone could be satisfied by padding; assert the resolver saw each name."""
    seen: list[str] = []
    record = _record(12)
    research({"query": "q", "service_record": record}, tools=_tools(seen))
    assert seen == record["sections"]["required_documents"]


def test_fixture_path_needs_no_tools():
    """G5 and the offline demo run with tools=None; that path must stay intact."""
    out = research({"query": "q", "service_record": _record(29),
                    "resolved_documents": []}, tools=None)
    assert out["resolved_documents"] == []
    event = [e for e in out["trace_events"] if e["node"] == "research"][-1]
    assert event["mode"] == "fixture"


def test_service_with_no_published_documents_is_not_an_error():
    out = research({"query": "q", "service_record": _record(0)}, tools=_tools())
    assert out["resolved_documents"] == []
