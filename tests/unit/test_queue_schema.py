"""Unit tests: review-queue append-only/lock/dedupe (A09), schema round-trip, normalizer,
and the conditional detector that carries the G2 finding into the answer."""
from __future__ import annotations

import json

import pytest

from agents.models import (
    AnswerOut, Envelope, FreshnessResult, InvalidOut, QueueEvent, ServiceOut, TimeEstimate,
)
from tools.conditional_detect import (
    caveat_lines, confidence_penalty, detect_conditionals, needs_review,
)
from tools.review_queue import append_event, event_id_for, existing_ids, queue_event
from tools.text_norm import normalize_ar


# ---------------------------------------------------------------- queue (A09)
@pytest.fixture()
def qpath(tmp_path):
    return tmp_path / "review_queue.jsonl"


def test_append_and_read_back(qpath):
    assert queue_event("stale_source", "بطاقة هوية", 11464, path=qpath) is True
    assert len(existing_ids(qpath)) == 1


def test_dedupe_same_event(qpath):
    """The same stale service hit by ten users must not create ten tickets."""
    assert queue_event("stale_source", "بطاقة هوية", 11464, path=qpath) is True
    for _ in range(9):
        assert queue_event("stale_source", "بطاقة هوية", 11464, path=qpath) is False
    assert len(existing_ids(qpath)) == 1


def test_distinct_events_both_queued(qpath):
    queue_event("stale_source", "بطاقة هوية", 11464, path=qpath)
    queue_event("conditional_structure", "اكتساب الجنسية", 11476, path=qpath)
    assert len(existing_ids(qpath)) == 2


def test_append_only_never_rewrites(qpath):
    queue_event("stale_source", "A", 1, path=qpath)
    first = qpath.read_text(encoding="utf-8")
    queue_event("stale_source", "B", 2, path=qpath)
    after = qpath.read_text(encoding="utf-8")
    assert after.startswith(first)          # the original line is byte-identical and still first
    assert len(after.splitlines()) == 2


def test_event_id_is_stable_across_runs():
    assert event_id_for("stale_source", 11464, "x") == event_id_for("stale_source", 11464, "x")
    assert event_id_for("stale_source", 11464, "x") != event_id_for("stale_source", 11465, "x")


def test_torn_line_does_not_break_the_queue(qpath):
    qpath.write_text('{"event_id": "aaa"}\nNOT JSON\n', encoding="utf-8")
    assert "aaa" in existing_ids(qpath)      # survives the corrupt line
    assert queue_event("stale_source", "A", 1, path=qpath) is True


def test_every_line_is_valid_queueevent_json(qpath):
    queue_event("conditional_structure", "اكتساب الجنسية", 11476, path=qpath,
                details="branch,recency")
    for line in qpath.read_text(encoding="utf-8").splitlines():
        QueueEvent.model_validate_json(line)


# ---------------------------------------------------------------- normalizer
def test_normalize_ar_is_idempotent():
    s = "بطاقة الهويّة"
    assert normalize_ar(normalize_ar(s)) == normalize_ar(s)


def test_normalize_ar_folds_alef_variants():
    assert normalize_ar("إعادة") == normalize_ar("اعادة")


# ---------------------------------------------------------------- schema round-trip
def _envelope() -> Envelope:
    return Envelope(
        action="answer", reasoning="r", confidence=0.7, language="ar",
        output=AnswerOut(
            service=ServiceOut(
                name_ar="بطاقة هوية", source_url="https://dawlati.gov.lb/x",
                freshness=FreshnessResult(status="unchanged", snapshot_modified_gmt="t",
                                          checked_at="t", note=""),
                record_status="complete"),
            time_estimate=TimeEstimate(computable=False)))


def test_envelope_round_trip():
    e = _envelope()
    again = Envelope.model_validate(json.loads(e.model_dump_json()))
    assert again.action == "answer" and again.output.service.name_ar == "بطاقة هوية"


def test_discriminated_union_keeps_its_variant():
    e = Envelope(action="invalid_request", reasoning="r", confidence=1.0, language="en",
                 output=InvalidOut(reason_code="bribery", message="no"))
    again = Envelope.model_validate(json.loads(e.model_dump_json()))
    assert again.output.reason_code == "bribery"


def test_confidence_bounds_enforced():
    for bad in (-0.1, 1.1):
        with pytest.raises(Exception):
            Envelope(action="answer", reasoning="r", confidence=bad, language="ar",
                     output=_envelope().output)


# ---------------------------------------------------------------- conditional detector (G2)
def test_detects_branch_and_recency():
    docs = ["بالنسبة للزوجه السورية : بيان قيد سوري يعود تاريخه لأقل من ستة أشهر"]
    kinds = {f.kind for f in detect_conditionals(docs)}
    assert "branch" in kinds and "recency" in kinds


def test_either_or_is_low_confidence_and_does_not_escalate():
    """«أو» is ubiquitous in Arabic — it earns a caveat but must not queue a review ticket."""
    flags = detect_conditionals(["اقامه صالحه او تاشيرة دخول صالحه"])
    assert [f.kind for f in flags] == ["either_or"]
    assert flags[0].high_confidence is False
    assert needs_review(flags) is False


def test_high_confidence_flag_escalates():
    assert needs_review(detect_conditionals(["بالنسبة للفلسطينية: بيان قيد"])) is True


def test_clean_service_produces_no_flags():
    """The verified-clean demo service must not be cluttered with spurious caveats."""
    assert detect_conditionals(["طلب مقدم من المطلقة مصدق من المختار",
                                "صورة طبق الأصل عن وثيقة الطلاق"]) == []


def test_penalty_is_capped():
    docs = ["بالنسبة للسورية بيان قيد يعود تاريخه لأقل من ستة أشهر بشرط أن مرّ عام او صورة"]
    assert confidence_penalty(detect_conditionals(docs)) <= 0.40


def test_branch_evidence_survives_header_stripping_via_raw_text():
    """The splitter now removes Roman-numeral case headers from `documents`, so branch evidence
    for services like #11528 exists ONLY in raw_text. If this regresses, branches go undetected
    exactly where they matter most."""
    assert detect_conditionals(["شهادة الولادة المحلية"]) == []
    flags = detect_conditionals(["شهادة الولادة المحلية"], extra_text="I – ولادة القاصر")
    assert "branch" in {f.kind for f in flags}


def test_caveats_are_localised():
    flags = detect_conditionals(["بالنسبة للفلسطينية: بيان قيد"])
    assert caveat_lines(flags, "ar") and caveat_lines(flags, "en")
    assert caveat_lines(flags, "ar") != caveat_lines(flags, "en")
