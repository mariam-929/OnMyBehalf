"""G7 unit tests: freshness semantics, review-queue invariants, outage drill (A08/A09/A14).

No network. The A14 drill injects a dead REST session rather than turning off the wifi, which is
the point of the drill: Dawlati must be able to fail while Groq stays up.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.check_freshness import check_freshness, lookup_row_freshness  # noqa: E402
from tools.live_service_lookup import live_service_lookup  # noqa: E402
from tools.review_queue import (append_event, open_events, read_events,  # noqa: E402
                                resolve_event, summary)

SNAP = "2026-07-13T14:16:21"


# --------------------------------------------------------------------------- fakes
class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns a canned payload."""
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status
        self.calls = []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        return FakeResponse(self.payload, self.status)


class DeadSession:
    """A14: Dawlati is down. Groq is NOT — nothing here touches the LLM."""
    def get(self, url, **kw):
        raise TimeoutError("simulated Dawlati outage")


# --------------------------------------------------------------------------- freshness
def test_unchanged_when_timestamps_match():
    s = FakeSession({"id": 1, "modified_gmt": SNAP})
    assert check_freshness(1, "ministry_service_ser", SNAP, session=s).status == "unchanged"


def test_changed_when_source_is_newer():
    s = FakeSession({"id": 1, "modified_gmt": "2026-07-20T00:00:00"})
    assert check_freshness(1, "ministry_service_ser", SNAP, session=s).status == "changed"


def test_changed_when_source_moved_BACKWARDS():
    """A restore-from-backup or reverted edit is a change a reviewer must see.

    The original implementation compared `live > snapshot` and silently called this `unchanged`.
    """
    s = FakeSession({"id": 1, "modified_gmt": "2020-01-01T00:00:00"})
    assert check_freshness(1, "ministry_service_ser", SNAP, session=s).status == "changed"


def test_unverified_on_outage_not_a_crash_and_not_unchanged():
    """A14: dead source -> `unverified` + a caveat, never a silent pass."""
    res = check_freshness(1, "ministry_service_ser", SNAP, session=DeadSession())
    assert res.status == "unverified"
    assert res.source_modified_gmt is None
    assert "unreachable" in res.note
    assert SNAP in res.note          # the snapshot date must reach the citizen


def test_unverified_on_non_200():
    s = FakeSession({}, status=503)
    assert check_freshness(1, "ministry_service_ser", SNAP, session=s).status == "unverified"


def test_unverified_when_source_omits_modified_gmt():
    s = FakeSession({"id": 1})
    assert check_freshness(1, "ministry_service_ser", SNAP, session=s).status == "unverified"


# --------------------------------------------------------------------------- FR6b TTL
def test_lookup_row_within_ttl_is_unchanged():
    recent = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    assert lookup_row_freshness(recent).status == "unchanged"


def test_lookup_row_past_180d_ttl_is_unverified():
    old = (datetime.now(timezone.utc) - timedelta(days=181)).isoformat()
    res = lookup_row_freshness(old)
    assert res.status == "unverified"
    assert "TTL" in res.note


def test_lookup_row_without_date_is_unverified():
    assert lookup_row_freshness(None).status == "unverified"
    assert lookup_row_freshness("not-a-date").status == "unverified"


# --------------------------------------------------------------------------- live lookup (N6)
HITS = [
    {"id": 11464, "title": {"rendered": "بطاقة هوية"}, "modified_gmt": SNAP},
    {"id": 11633, "title": {"rendered": "إصدار بطاقة تعريف للخيل"},
     "modified_gmt": "2026-07-21T16:20:50"},
]


def test_is_newer_is_anchored_to_OUR_service_not_the_newest_hit():
    """The bug this guards: `max(modified_gmt)` over hits reported is_newer=True from an unrelated
    horse-ID-card record, which would have raised needs_human_review on a correct answer."""
    res = live_service_lookup("بطاقة هوية", post_id=11464, snapshot_modified_gmt=SNAP,
                              session=FakeSession(HITS))
    assert res.exists is True
    assert res.is_newer is False          # OUR post is unchanged
    assert res.newest_post_id == 11633    # still reported, as information


def test_is_newer_true_when_our_service_moved():
    res = live_service_lookup("بطاقة هوية", post_id=11464,
                              snapshot_modified_gmt="2026-01-01T00:00:00",
                              session=FakeSession(HITS))
    assert res.is_newer is True


def test_exists_false_when_our_service_is_absent_from_live_results():
    res = live_service_lookup("بطاقة هوية", post_id=999999, snapshot_modified_gmt=SNAP,
                              session=FakeSession(HITS))
    assert res.exists is False
    assert res.is_newer is False


def test_outage_reports_cannot_confirm_never_invents_a_removal():
    res = live_service_lookup("بطاقة هوية", post_id=11464, snapshot_modified_gmt=SNAP,
                              session=DeadSession())
    assert res.exists is False
    assert res.is_newer is False


def test_unanchored_call_never_sets_is_newer():
    res = live_service_lookup("بطاقة هوية", snapshot_modified_gmt="2020-01-01T00:00:00",
                              session=FakeSession(HITS))
    assert res.is_newer is False


# --------------------------------------------------------------------------- review queue (A09)
@pytest.fixture()
def qpath(tmp_path):
    return tmp_path / "review_queue.jsonl"


def test_append_and_read(qpath):
    ev = append_event("unresolved_document", "إخراج قيد إفرادي", path=qpath)
    assert ev is not None
    assert len(read_events(qpath)) == 1
    assert open_events(qpath)[0].subject_label == "إخراج قيد إفرادي"


def test_dedupe_suppresses_identical_open_event(qpath):
    assert append_event("unresolved_document", "إخراج قيد إفرادي", path=qpath) is not None
    assert append_event("unresolved_document", "إخراج قيد إفرادي", path=qpath) is None
    assert len(open_events(qpath)) == 1


def test_different_subject_is_not_deduped(qpath):
    append_event("unresolved_document", "إخراج قيد إفرادي", path=qpath)
    append_event("unresolved_document", "بيان قيد عائلي", path=qpath)
    assert len(open_events(qpath)) == 2


def test_different_type_same_subject_is_not_deduped(qpath):
    append_event("unresolved_document", "بطاقة هوية", subject_post_id=11464, path=qpath)
    append_event("stale_source", "بطاقة هوية", subject_post_id=11464, path=qpath)
    assert len(open_events(qpath)) == 2


def test_nullable_subject_post_id(qpath):
    """A09: an unresolved document is usually not a service post and has no id."""
    ev = append_event("unresolved_document", "شهادة سكن", path=qpath)
    assert ev.subject_post_id is None


def test_resolution_appends_and_never_rewrites(qpath):
    ev = append_event("stale_source", "تسجيل زواج", subject_post_id=11552, path=qpath)
    resolve_event(ev.event_id, "checked against source", path=qpath)
    assert len(read_events(qpath)) == 2      # append-only: both lines survive
    assert open_events(qpath) == []          # but nothing is open


def test_reopening_after_resolution_is_allowed(qpath):
    """Dedupe keys on OPEN events, so a genuinely recurring problem can be re-raised."""
    ev = append_event("stale_source", "تسجيل زواج", subject_post_id=11552, path=qpath)
    resolve_event(ev.event_id, path=qpath)
    assert append_event("stale_source", "تسجيل زواج", subject_post_id=11552, path=qpath) is not None
    assert len(open_events(qpath)) == 1


def test_corrupt_line_does_not_hide_the_queue(qpath):
    append_event("stale_source", "تسجيل زواج", subject_post_id=11552, path=qpath)
    with open(qpath, "a", encoding="utf-8") as fh:
        fh.write("{not json at all\n")
    assert len(read_events(qpath)) == 1


def test_summary_counts_by_type(qpath):
    append_event("stale_source", "أ", subject_post_id=1, path=qpath)
    append_event("unresolved_document", "ب", path=qpath)
    s = summary(qpath)
    assert s["open"] == 2
    assert s["by_type"]["stale_source"] == 1
