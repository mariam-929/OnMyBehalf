"""Unit tests: the external-source fallback (tools/external_source.py + its graph branch).

Each test here pins a defect that was actually hit while building the feature on 2026-07-28, not a
hypothetical. The two that matter most are `test_no_fees_invented_from_a_layout_table` and
`test_external_documents_never_carry_where_to_obtain` — both guard facts reaching a citizen.
"""
from __future__ import annotations

import pytest

from agents.graph import build_graph
from agents.nodes.external import external_lookup_node, route_after_external
from tools.external_source import (
    REGISTRY, abstained_documents, extract_sections, external_freshness, _match,
)


# ---------------------------------------------------------------- registry matching
@pytest.mark.parametrize("query,language,expected", [
    ("كيف أجدد جواز سفري؟", "ar", "passport_biometric"),
    ("How do I renew my passport?", "en", "passport_biometric"),
    ("بدي صدق صور عن صفحات جواز السفر", "ar", "passport_certify_copies"),
    ("certifying copies of passport pages", "en", "passport_certify_copies"),
    ("تعديل الأحرف في جواز السفر", "ar", "passport_modify"),
])
def test_match_finds_the_right_entry(query, language, expected):
    entry = _match(query, language)
    assert entry is not None and entry["key"] == expected


@pytest.mark.parametrize("query", [
    "",
    "كيف بسجل ولادة طفلي؟",          # a Dawlati service — must NOT be hijacked
    "how do I open a bank account",   # not a government service at all
    "ضاع مني",                        # a qualifier with no subject
])
def test_match_abstains_rather_than_guessing(query):
    """A miss costs the citizen today's `service_not_found`. A false hit answers a question about
    one service with another service's documents."""
    assert _match(query, "ar") is None and _match(query, "en") is None


def test_base_entry_is_last_so_specific_entries_win():
    """Specificity is expressed by ORDER — the unqualified passport entry must never shadow the
    qualified ones."""
    assert REGISTRY[-1]["key"] == "passport_biometric"
    assert REGISTRY[-1]["qualifiers_ar"] == [] and REGISTRY[-1]["qualifiers_en"] == []


# ---------------------------------------------------------------- extraction
_PAGE = """
<div id="post-container" class="content">
  <p><strong><u>Requested documents:</u></strong></p>
  <ul><li>An application form.</li><li>A photo.</li></ul>
  <p><strong><u>Fees:</u></strong></p>
  <table><tr><td>Passport 5 years</td><td>6,000,000 L.L</td></tr></table>
</div>
<div id="footer"><table><tr><td>Beirut Port center</td><td>01/584400</td></tr></table></div>
"""

_PAGE_NO_FEES = """
<div id="post-container" class="content">
  <div>تعتمد المستندات التالية:</div>
  <div dir="rtl"><ul><li>إقامة في الخارج.</li><li>جواز سفر أجنبي.</li></ul></div>
</div>
<div id="footer"><table><tr><td>Beirut Port center</td><td>01/584400</td></tr></table></div>
"""


def test_extracts_documents_and_real_fees():
    s = extract_sections(_PAGE)
    assert s["required_documents"] == ["An application form.", "A photo."]
    assert "6,000,000 L.L" in s["fees"]


def test_no_fees_invented_from_a_layout_table():
    """REGRESSION. An earlier version fell back to "any <table> on the page" when no fees section
    was found, and captured the site's CONTACT DIRECTORY — "Beirut Port center 01/584400" would
    have been rendered to a citizen as the fee for the service."""
    s = extract_sections(_PAGE_NO_FEES)
    assert s["fees"] is None
    assert "584400" not in (s["fees"] or "")


def test_documents_found_when_the_lead_in_is_a_div_not_a_p():
    """REGRESSION. /ar/posts/76 opens with a bare <div>; a <p>-only heading scan identified no
    section and silently dropped all four documents, while the <p>-based EN twin extracted fine."""
    assert extract_sections(_PAGE_NO_FEES)["required_documents"] == [
        "إقامة في الخارج.", "جواز سفر أجنبي."]


def test_extraction_failure_is_none_not_empty_list():
    """FR12: None means "could not extract"; [] would claim the source requires no documents."""
    assert extract_sections("<html><body>nothing here</body></html>")["required_documents"] is None


# ---------------------------------------------------------------- abstention
def test_external_documents_never_carry_where_to_obtain():
    """Measured on /ar/posts/11: 1 of 13 lines resolved against the corpus and it was WRONG — a
    RULE about General Security families, attributed to the civil-registry directorate at 0.6367
    while a genuine line scored 0.7004 and abstained. FR4 says abstain rather than attach a
    doubtful source, so v1 offers no per-document resolution for external records."""
    record = {"url": "https://example.gov.lb/x",
              "sections": {"required_documents": ["وثيقة أ", "قاعدة إجرائية ب"]}}
    docs = abstained_documents(record)
    assert len(docs) == 2
    assert all(d["resolution"] == "unresolved" for d in docs)
    assert all(d["where_to_obtain"] is None for d in docs)
    assert all(d["needs_human_review"] for d in docs)
    # every published line still reaches the citizen — abstention is not truncation
    assert [d["name_ar"] for d in docs] == ["وثيقة أ", "قاعدة إجرائية ب"]


def test_freshness_is_unverified_and_says_which_copy_served():
    """A08: `unchanged` means a modification timestamp matched. This source publishes none, so
    `unverified` is the only honest label — and the note must distinguish live from snapshot."""
    live = external_freshness({"served_from": "live", "fetched_at": "2026-07-28T20:00:06+00:00",
                               "source_domain": "general-security.gov.lb"})
    snap = external_freshness({"served_from": "snapshot", "fetched_at": "2026-07-28T19:00:00+00:00",
                               "source_domain": "general-security.gov.lb"})
    assert live["status"] == snap["status"] == "unverified"
    assert "live" in live["note"].lower() and "snapshot" in snap["note"].lower()


# ---------------------------------------------------------------- the graph branch
def test_node_is_a_pass_through_when_not_wired():
    state = {"query": "كيف أجدد جواز سفري؟", "trace_events": []}
    out = external_lookup_node(state, external_fn=None)
    assert "service_record" not in out
    assert route_after_external({**state, **out}) == "not_found"


def test_a_raising_source_degrades_to_not_found_rather_than_crashing():
    def boom(_q, _l):
        raise RuntimeError("network on fire")

    out = external_lookup_node({"query": "جواز سفر", "trace_events": []}, external_fn=boom)
    assert route_after_external(out) == "not_found"


def test_disabled_branch_leaves_not_found_behaviour_identical():
    """The safety property the whole design rests on: with `external_fn=None` the graph behaves
    exactly as it did before this branch existed."""
    g = build_graph()
    r = g.invoke({"query": "كيف أجدد جواز سفري؟", "trace_events": [], "messages": []})
    assert r["final_response"]["action"] == "service_not_found"


def test_external_branch_answers_when_wired():
    g = build_graph(external_fn=lambda q, l: {
        "post_id": None, "type": "external_gov_site",
        "url": "https://www.general-security.gov.lb/ar/posts/11",
        "title_ar": "جواز سفر بيومتري", "title_en": "Biometric passport",
        "raw_text": "طلب جواز سفر", "record_status": "complete",
        "sections": {"required_documents": ["طلب جواز سفر"], "fees": None,
                     "processing_time": None, "where_to_apply": None,
                     "authority": "الأمن العام", "steps": None},
        "source_domain": "general-security.gov.lb", "served_from": "snapshot",
        "fetched_at": "2026-07-28T00:00:00+00:00",
    })
    r = g.invoke({"query": "كيف أجدد جواز سفري؟", "trace_events": [], "messages": []})
    env = r["final_response"]
    assert env["action"] == "answer"
    assert env["output"]["service"]["source_url"].startswith("https://www.general-security")
    # provenance must be disclosed to the citizen, first, before the conditional caveats
    assert "general-security.gov.lb" in env["output"]["caveats"][0]
    assert env["output"]["service"]["freshness"]["status"] == "unverified"


def test_found_path_never_reaches_the_external_branch():
    """Structural guarantee, asserted rather than assumed: nothing that answers today can regress
    through this feature."""
    g = build_graph(external_fn=lambda q, l: pytest.fail("external branch reached on a found path"))
    r = g.invoke({"query": "شو الأوراق المطلوبة لتجديد بطاقة الهوية؟", "trace_events": [],
                  "messages": [], "retrieval_outcome": "found",
                  "service_record": {"post_id": 1, "title_ar": "بطاقة هوية", "url": "u",
                                     "record_status": "complete", "raw_text": "",
                                     "sections": {"required_documents": ["أ"]}}})
    assert r["final_response"]["action"] == "answer"
