"""Detect conditional structure the flat `required_documents: list[str]` model cannot express.

WHY THIS EXISTS (G2 human check, 2026-07-27 — Maria + Ghina, independently)
--------------------------------------------------------------------------
Dawlati services are not flat lists. They encode conditional logic:

  * BRANCH       one service, several applicant CASES with different documents
                 (#11528 I/II/III = minor / adult / outside the legal window;
                  #11476 general / بالنسبة للزوجة السورية / بالنسبة للفلسطينية)
  * EITHER_OR    one requirement satisfiable several ways
                 (اقامة صالحة **أو** تأشيرة دخول; التعميم 1/84 **أو** قرار قنصلي)
  * PRECONDITION eligibility gate inside a document
                 (#11476: marriage registered ≥ 1 year before applying)
  * RECENCY      how OLD the citizen's own document may be, differing per case
                 (#11476: Syrian بيان قيد < 6 months, Palestinian < 3 months)

Flattening turns "bring A **or** B" into "bring A **and** B", shows every branch to every
applicant, and drops the recency windows entirely — so the agent is not merely incomplete,
it is CONFIDENTLY WRONG, which is the one failure mode this project exists to prevent.

Measured across the corpus: **90 of 180 services (50%)** carry at least one marker; 21 carry
two or more. Fixing the data model (nested cases, disjunction, preconditions) is a schema
change plus re-extraction plus re-verification — not possible before the deadline. So we
DETECT AND DISCLOSE: caveat in the answer, confidence penalty, and a review-queue event.

NOTE ON PRECISION: `either_or` keys on «أو», which is ubiquitous in Arabic and also appears
inside single document names. It is therefore marked `high_confidence=False` and carries a
smaller penalty. `branch`, `precondition` and `recency` use specific multi-token patterns and
are treated as reliable. Never silently upgrade `either_or` to high confidence — the honest
uncertainty is the point.
"""
from __future__ import annotations

import re

from agents.models import ConditionalFlag

# ---------------------------------------------------------------- patterns
# BRANCH: an explicit per-applicant case marker, or a Roman-numeral case header.
# re.M is load-bearing: the blob is multi-line (documents joined by \n, plus raw_text), so a
# ^-anchored case header only matches at the start of the WHOLE string without it. Without re.M
# every Roman-numeral branch (#11528 and friends) is silently invisible — caught by
# test_branch_evidence_survives_header_stripping_via_raw_text.
_BRANCH = re.compile(
    r"بالنسبة\s+ل"                    # "as for the ..." — introduces an applicant case
    r"|^\s*(?:[IVX]{1,4})\s*[-–—.):]"  # I – / II- / III. case header
    r"|في\s+حال(?:ة)?\s+(?!توفر)",     # "in the case of" (excluding the frequent "if available")
    re.M,
)
# EITHER_OR: «أو» / «او» as a free-standing word. Deliberately broad, deliberately low-confidence.
_EITHER_OR = re.compile(r"(?:^|\s)(?:أو|او)(?:\s|$)")
# PRECONDITION: an eligibility gate.
_PRECOND = re.compile(r"بعد\s+مرور|بشرط|يشترط|شرط\s+أن|على\s+أن\s+يكون")
# RECENCY: how old the citizen's document may be.
_RECENCY = re.compile(
    r"لا\s+يتجاوز\s+تاريخ\S*\s|يعود\s+تاريخه\s+لأقل\s+من"
    r"|أقل\s+من\s+\S+\s*(?:أشهر|شهر|سنة|سنوات)"
    r"|خلال\s+\S+\s*(?:أشهر|شهر|سنة)"
)

_PATTERNS: list[tuple[str, re.Pattern[str], bool]] = [
    ("branch", _BRANCH, True),
    ("recency", _RECENCY, True),
    ("precondition", _PRECOND, True),
    ("either_or", _EITHER_OR, False),
]

# Confidence penalties (FR7 is otherwise blind to this — a branched core service would
# otherwise answer at 0.9 while showing the wrong branch).
_PENALTY = {"branch": 0.25, "recency": 0.15, "precondition": 0.10, "either_or": 0.05}
_MAX_PENALTY = 0.40


def _snippet(text: str, m: re.Match[str], width: int = 60) -> str:
    start = max(0, m.start() - width // 2)
    return ("…" if start else "") + text[start:m.end() + width].strip().replace("\n", " ") + "…"


def detect_conditionals(documents: list[str] | None, extra_text: str = "") -> list[ConditionalFlag]:
    """Scan a service's documents (+ any raw text) for constructs the flat model can't express.

    `extra_text` matters: the splitter now strips Roman-numeral case headers out of `documents`
    (they are not documents), so branch evidence for services like #11528 survives only in the
    record's raw_text. Pass it in, or branches become invisible exactly where they matter most.
    """
    blob = "\n".join(documents or []) + ("\n" + extra_text if extra_text else "")
    if not blob.strip():
        return []
    flags: list[ConditionalFlag] = []
    for kind, pat, high in _PATTERNS:
        m = pat.search(blob)
        if m:
            flags.append(ConditionalFlag(kind=kind, evidence=_snippet(blob, m), high_confidence=high))
    return flags


def confidence_penalty(flags: list[ConditionalFlag]) -> float:
    """Total confidence deduction, capped so a flagged answer is never driven to zero."""
    return min(sum(_PENALTY[f.kind] for f in flags), _MAX_PENALTY)


def caveat_lines(flags: list[ConditionalFlag], language: str = "ar") -> list[str]:
    """Citizen-facing disclosure. One line per constraint type — no jargon, no schema-speak."""
    if not flags:
        return []
    kinds = {f.kind for f in flags}
    ar = {
        "branch": "تختلف المستندات المطلوبة حسب حالتك (الجنسية، العمر، أو ما إذا وقع الحدث خارج لبنان). "
                  "القائمة أدناه تجمع كل الحالات — تأكّد من حالتك مع الدائرة المختصة.",
        "either_or": "بعض البنود بدائل («أو») وليست مستندات إضافية مطلوبة كلّها.",
        "precondition": "لهذه المعاملة شروط أهلية يجب توفّرها قبل التقديم.",
        "recency": "بعض المستندات يجب ألا يتجاوز تاريخها مدة محددة، وتختلف هذه المدة بحسب الحالة.",
    }
    en = {
        "branch": "Required documents differ by your situation (nationality, age, or whether the "
                  "event occurred abroad). The list below merges all cases — confirm yours with "
                  "the office.",
        "either_or": "Some items are alternatives (\"or\"), not additional required documents.",
        "precondition": "This procedure has eligibility conditions that must be met before applying.",
        "recency": "Some documents must be recent, and the allowed age differs by case.",
    }
    src = ar if language == "ar" else en
    return [src[k] for k in ("branch", "either_or", "precondition", "recency") if k in kinds]


def needs_review(flags: list[ConditionalFlag]) -> bool:
    """Only HIGH-confidence constructs escalate. «أو» alone is too common to queue on."""
    return any(f.high_confidence for f in flags)
