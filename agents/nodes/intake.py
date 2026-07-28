"""Intake nodes: detect_language -> validate_input -> classify_intent.

Language detection and input validation are DETERMINISTIC and run BEFORE any model call (FR1).
Two reasons: an adversarial input should never reach the model at all, and the demo's failure
case must be reproducible — an LLM-decided refusal that varies run to run cannot be rehearsed.
"""
from __future__ import annotations

import re

from agents.models import IntentResult, InvalidOut
from agents.nodes.trace import with_trace

# Arabic block, excluding Arabic-Indic digits (a number is not evidence of language)
_ARABIC = re.compile(r"[ء-ي٠-٩]")
_ARABIC_LETTERS = re.compile(r"[ء-ي]")
_LATIN = re.compile(r"[A-Za-z]")

MIN_LEN = 3
MAX_LEN = 500

# Bounds the classification wait. This call runs for every query, so its worst case is the
# system's worst case — one eval run reached 30 s end-to-end on the free tier. Timing out here is
# safe by construction: `validate_input` has already refused adversarial input deterministically
# before any model call, so the fallback costs routing nuance, not safety.
INTENT_TIMEOUT_S = 6.0

# Adversarial patterns -> invalid_request (SCOPE §11). Deterministic, pre-model.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bribery", re.compile(r"\b(bribe|bribing|backhander|kickback)\b|رشوة|رشوه|بقشيش|واسطة",
                           re.I)),
    ("injection", re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions"
        r"|disregard\s+(the\s+)?(system|previous)"
        r"|you\s+are\s+now\s+|system\s*prompt\s*[:=]"
        r"|تجاهل\s+(كل\s+)?(التعليمات|الأوامر)", re.I)),
    ("legal_advice", re.compile(r"\b(should I sue|legal advice|will I win.*(case|court))\b"
                                r"|هل\s+أرفع\s+دعوى|استشارة\s+قانونية", re.I)),
    ("pii", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"                      # SSN-shaped
                       r"|\b(?:\d[ -]?){13,19}\b"                     # card-shaped
                       r"|رقم\s+(?:بطاقتي|حسابي)\s+(?:المصرفي|البنكي)", re.I)),
    ("out_of_jurisdiction", re.compile(
        r"\b(in|for)\s+(syria|jordan|egypt|france|turkey|cyprus|iraq|saudi)\b"
        r"|في\s+(سوريا|الأردن|مصر|فرنسا|تركيا|العراق|السعودية)", re.I)),
]


def detect_language(state: dict) -> dict:
    """Authoritative language decision (FR1) — the model's advisory never overrides it.

    Script ratio, not a library: the corpus is Arabic and the queries are short, which is where
    statistical detectors are least reliable. Ties go to Arabic because the source is Arabic.
    """
    q = state.get("query", "") or ""
    ar, la = len(_ARABIC_LETTERS.findall(q)), len(_LATIN.findall(q))
    language = "ar" if ar >= la else "en"
    return with_trace(state, "detect_language", {"language": language},
                      arabic_chars=ar, latin_chars=la, decided=language)


def validate_input(state: dict) -> dict:
    """Deterministic guardrail. Sets `invalid` on the state to route to the terminal branch."""
    q = (state.get("query") or "").strip()

    if len(q) < MIN_LEN:
        return _invalid(state, "gibberish", "Query too short to act on.", reason="too_short")
    if len(q) > MAX_LEN:
        return _invalid(state, "gibberish", f"Query exceeds {MAX_LEN} characters.",
                        reason="too_long")
    # no letters in either script at all => not a question
    if not _ARABIC_LETTERS.search(q) and not _LATIN.search(q):
        return _invalid(state, "gibberish", "Query contains no readable text.",
                        reason="no_letters")

    for code, pat in _PATTERNS:
        if m := pat.search(q):
            return _invalid(state, code, _REFUSAL[code], reason=code, matched=m.group(0)[:40])

    return with_trace(state, "validate_input", {"invalid": None}, ok=True)


_REFUSAL = {
    "bribery": "I can only provide official procedures, fees and required documents.",
    "injection": "I can only answer questions about Lebanese government procedures.",
    "legal_advice": "I can't give legal advice — only official procedural information.",
    "pii": "Please don't share personal identifiers. I don't need them to answer.",
    "out_of_jurisdiction": "I only cover Lebanese government procedures published on Dawlati.",
}


def _invalid(state: dict, code: str, message: str, **trace_fields) -> dict:
    out = InvalidOut(reason_code=code, message=message)  # type: ignore[arg-type]
    return with_trace(state, "validate_input", {"invalid": out.model_dump()}, **trace_fields)


def classify_intent(state: dict, adapter=None, system_prompt: str = "") -> dict:
    """service_query | follow_up | invalid_request (N2).

    `adapter=None` is the fixture path used by G5 and the offline demo: it classifies from state
    without a model call, so every terminal path is traversable with no network and no key.
    """
    q = state.get("query", "") or ""
    if adapter is None:
        has_history = bool(state.get("messages"))
        # a short query on top of existing history reads as a follow-up
        intent = "follow_up" if has_history and len(q.split()) <= 4 else "service_query"
        result = IntentResult(intent=intent, reason="fixture-mode heuristic",
                              language_advisory=state.get("language", "ar"))
        return with_trace(state, "classify_intent", {"intent": result.model_dump()},
                          intent=intent, mode="fixture")

    try:
        result, meta = adapter.complete(system_prompt, q, IntentResult,
                                        timeout=INTENT_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        # Classification is on the critical path for EVERY query, including refusals, so an
        # unbounded or failed call would stall the whole system. Falling back to the fixture
        # heuristic degrades routing quality, never safety: `validate_input` has already run
        # deterministically, so adversarial input is refused whether or not this call succeeds.
        result = IntentResult(intent="service_query", reason=f"model unavailable: {exc!s:.60}",
                              language_advisory=state.get("language", "ar"))
        return with_trace(state, "classify_intent", {"intent": result.model_dump()},
                          intent=result.intent, mode="fallback", error=str(exc)[:80])
    return with_trace(state, "classify_intent", {"intent": result.model_dump()},
                      intent=result.intent, mode="model", latency_s=meta.get("latency_s"))
