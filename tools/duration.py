"""Duration parsing + aggregation (A10: explicit units, NO cross-unit arithmetic).

The source states processing times in mixed, vague units ("خلال أسبوعين", "3 أيام عمل",
"شهر تقريباً"). The rule from A10 is deliberate and load-bearing:

    We never convert between units to produce a total.

Because "5 business days" and "1 month" cannot be summed without inventing a working-week and a
month length — and inventing numbers is precisely the failure this project exists to avoid. When
the steps of one answer carry different units, the aggregate is reported as
`TimeEstimate(computable=False)` and the breakdown is shown instead. An honest "we can't total
this, here are the parts" beats a confident wrong number.
"""
from __future__ import annotations

import re

from agents.models import BreakdownStep, Duration, TimeEstimate

_UNIT_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"يوم\s*عمل|أيام\s*عمل|ايام\s*عمل|business\s+day"), "business_days"),
    (re.compile(r"أسبوع|اسبوع|week"), "weeks"),
    (re.compile(r"شهر|أشهر|اشهر|month"), "months"),
    (re.compile(r"يوم|أيام|ايام|day"), "calendar_days"),
]
# Arabic-Indic digits -> ASCII
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
# duals: أسبوعين = 2 weeks, يومين = 2 days, شهرين = 2 months
_DUAL = re.compile(r"(?:أسبوع|اسبوع|يوم|شهر)ين")
_ONE = re.compile(r"\bواحد(?:ة)?\b|\bone\b", re.I)
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|إلى|الى|to)\s*(\d+(?:\.\d+)?)")
_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def parse_duration(text: str | None) -> Duration:
    """Free text -> Duration. Unknown/absent stays `unit='unknown'` with no invented numbers."""
    if not text or not text.strip():
        return Duration()
    t = text.translate(_AR_DIGITS)

    unit = "unknown"
    for pat, u in _UNIT_WORDS:
        if pat.search(t):
            unit = u
            break

    if m := _RANGE.search(t):
        lo, hi = float(m.group(1)), float(m.group(2))
        return Duration(min_val=min(lo, hi), max_val=max(lo, hi), unit=unit)
    if _DUAL.search(t) and not _NUM.search(t):
        return Duration(min_val=2, max_val=2, unit=unit)
    # spelled-out "one" ("شهر واحد", "one month"). Reading a written numeral is not inventing
    # one; only the absence of any magnitude leaves min_val None.
    if _ONE.search(t) and not _NUM.search(t):
        return Duration(min_val=1, max_val=1, unit=unit)
    if m := _NUM.search(t):
        v = float(m.group(1))
        return Duration(min_val=v, max_val=v, unit=unit)
    # a unit word with no number ("خلال أشهر") — the unit is known, the magnitude is not
    return Duration(unit=unit)


_TO_DAYS = {"business_days": 1.0, "calendar_days": 1.0, "weeks": 7.0, "months": 30.0}


def aggregate(steps: list[BreakdownStep]) -> TimeEstimate:
    """Sum step durations ONLY when every step shares one unit (A10).

    Mixed units, unknown units, or any missing magnitude => computable=False. `is_lower_bound`
    marks a total assembled from steps where at least one magnitude was missing, so the caller
    can render "at least N" rather than "N".
    """
    if not steps:
        return TimeEstimate(computable=False)

    units = {s.duration.unit for s in steps}
    if len(units) > 1 or units == {"unknown"}:
        # different units, or nothing usable — report the parts, refuse the total
        return TimeEstimate(computable=False, breakdown=steps)

    unit = units.pop()
    known = [s for s in steps if s.duration.min_val is not None]
    if not known:
        return TimeEstimate(computable=False, breakdown=steps)

    factor = _TO_DAYS[unit]
    lo = sum((s.duration.min_val or 0) for s in known) * factor
    hi = sum((s.duration.max_val if s.duration.max_val is not None else s.duration.min_val or 0)
             for s in known) * factor
    return TimeEstimate(
        computable=True,
        total_min_days=lo,
        total_max_days=hi,
        is_lower_bound=len(known) < len(steps),
        breakdown=steps,
    )
