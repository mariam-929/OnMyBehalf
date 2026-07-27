"""Unit tests: Duration parser + aggregator (A10) and RRF fusion (F10/A12) — both G5 criteria."""
from __future__ import annotations

import pytest

from agents.models import BreakdownStep, Duration
from tools.duration import aggregate, parse_duration
from tools.rrf import margin, rrf_fuse


# ---------------------------------------------------------------- Duration
@pytest.mark.parametrize("text,unit,lo,hi", [
    ("3 أيام عمل", "business_days", 3, 3),
    ("خلال أسبوعين", "weeks", 2, 2),
    ("شهر واحد", "months", 1, 1),
    ("من 5 إلى 10 أيام", "calendar_days", 5, 10),
    ("2-4 weeks", "weeks", 2, 4),
    ("٣ أيام", "calendar_days", 3, 3),          # Arabic-Indic digits
])
def test_parse_duration(text, unit, lo, hi):
    d = parse_duration(text)
    assert d.unit == unit
    assert d.min_val == lo and d.max_val == hi


@pytest.mark.parametrize("text", [None, "", "   ", "غير محدد"])
def test_parse_duration_invents_nothing(text):
    """No number in the source => no number in the output. This is the whole point of A10."""
    d = parse_duration(text)
    assert d.min_val is None and d.max_val is None


def test_unit_word_without_magnitude_keeps_unit_drops_number():
    d = parse_duration("خلال أشهر")
    assert d.unit == "months"
    assert d.min_val is None


def test_aggregate_same_unit_sums():
    steps = [BreakdownStep(step="a", duration=Duration(min_val=2, max_val=3, unit="weeks")),
             BreakdownStep(step="b", duration=Duration(min_val=1, max_val=1, unit="weeks"))]
    t = aggregate(steps)
    assert t.computable is True
    assert t.total_min_days == 21 and t.total_max_days == 28   # (2+1)*7, (3+1)*7


def test_aggregate_mixed_units_is_not_computable():
    """THE A10 CASE: business_days + months cannot be summed without inventing a working week
    and a month length. Refuse the total, keep the breakdown."""
    steps = [BreakdownStep(step="a", duration=Duration(min_val=5, max_val=5, unit="business_days")),
             BreakdownStep(step="b", duration=Duration(min_val=1, max_val=1, unit="months"))]
    t = aggregate(steps)
    assert t.computable is False
    assert len(t.breakdown) == 2          # the parts are still shown


def test_aggregate_all_unknown_is_not_computable():
    steps = [BreakdownStep(step="a", duration=Duration(unit="unknown"))]
    assert aggregate(steps).computable is False


def test_aggregate_marks_lower_bound_when_a_step_has_no_magnitude():
    steps = [BreakdownStep(step="a", duration=Duration(min_val=3, max_val=3, unit="weeks")),
             BreakdownStep(step="b", duration=Duration(unit="weeks"))]
    t = aggregate(steps)
    assert t.computable is True and t.is_lower_bound is True


def test_aggregate_empty():
    assert aggregate([]).computable is False


# ---------------------------------------------------------------- RRF
def test_rrf_swapped_top_two_tie_and_break_deterministically():
    """[1,2,3] vs [2,1,3]: ids 1 and 2 hold ranks {1,2} in some order, so their RRF scores are
    genuinely EQUAL. The tie must break on ascending id, not on input order."""
    fused = rrf_fuse([1, 2, 3], [2, 1, 3])
    assert fused[0][1] == pytest.approx(fused[1][1])
    assert [d for d, _ in fused] == [1, 2, 3]


def test_rrf_item_in_both_lists_beats_item_in_one():
    fused = dict(rrf_fuse([1, 2], [1, 3]))
    assert fused[1] > fused[2] and fused[1] > fused[3]


def test_rrf_absence_is_not_a_penalty():
    """An item missing from BM25 must still win on a strong dense rank — the cross-lingual case
    (English query, Arabic-only title) depends on this."""
    fused = dict(rrf_fuse([99], [1]))
    assert fused[1] == fused[99]


def test_rrf_is_deterministic_on_ties():
    a = rrf_fuse([1, 2], [2, 1])
    b = rrf_fuse([1, 2], [2, 1])
    assert a == b
    assert [d for d, _ in a] == sorted(d for d, _ in a)   # tie -> ascending id


def test_rrf_empty():
    assert rrf_fuse() == [] and rrf_fuse([]) == []


def test_margin_single_candidate_is_infinite():
    assert margin([(1, 0.5)]) == float("inf")


def test_margin_gap():
    assert margin([(1, 0.5), (2, 0.2)]) == pytest.approx(0.3)
