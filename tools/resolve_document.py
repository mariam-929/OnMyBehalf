"""Per-document resolution: normalise -> lookup table -> corpus -> ABSTAIN (SCOPE FR4, A11).

This is the feature that distinguishes the product. Dawlati tells a citizen "bring an individual
civil extract"; it does not tell them where to get one. Several required documents ARE themselves
services in the corpus («بيان قيد عائلي وإفرادي» is #11548), so resolving a document name against
the service index answers "where do I obtain this" from the same cited source.

ABSTENTION IS THE POINT (A11). Attaching a doubtful source is worse than attaching none: a citizen
sent to the wrong office loses a day, and a wrong citation destroys the traceability claim the
whole project rests on. Below threshold, or too close between the top two candidates, the answer
is `unresolved` — recorded honestly and surfaced in the answer.

Depth is ONE level (SCOPE §11 puts depth-2 out of scope). We do not resolve the documents required
BY a resolved document; that recursion has no natural floor in this corpus.
"""
from __future__ import annotations

import json
from pathlib import Path

from agents.models import ResolvedDocument
from tools.text_norm import normalize_ar

ROOT = Path(__file__).resolve().parents[1]
LOOKUP_PATH = ROOT / "data" / "document_sources.json"
SEED_PATH = ROOT / "data" / "document_sources.seed.json"

# Cosine gates. Deliberately STRICTER than retrieval's theta_abs (0.55): a wrong service answer is
# visible and recoverable, but a wrong "go here to obtain this document" sends someone to the
# wrong ministry. TIE_BAND forces abstention when two candidates are near-indistinguishable.
THETA_DOC = 0.62
TIE_BAND = 0.04

_lookup: list[dict] | None = None


def _load_lookup() -> list[dict]:
    """G3's lookup table, falling back to the seed until Maria/Ghina fill it in."""
    global _lookup
    if _lookup is None:
        path = LOOKUP_PATH if LOOKUP_PATH.exists() else SEED_PATH
        _lookup = (json.loads(path.read_text(encoding="utf-8")).get("rows", [])
                   if path.exists() else [])
    return _lookup


def _cos(c) -> float:
    v = getattr(c, "dense_cos", None)
    if v is None and isinstance(c, dict):
        v = c.get("dense_cos")
    return float(v or 0.0)


def _from_lookup(name_ar: str) -> ResolvedDocument | None:
    """Hand-curated table first — a verified row beats anything inferred from similarity."""
    n = normalize_ar(name_ar)
    if not n:
        return None
    for row in _load_lookup():
        key = normalize_ar(row.get("doc_name_ar"))
        if key and (key in n or n in key):
            return ResolvedDocument(
                name_ar=name_ar,
                name_en=row.get("doc_name_en") or None,
                resolution="lookup_table",
                where_to_obtain=row.get("where") or row.get("issuing_authority"),
                source_url=row.get("source_url") or None,
                verified_on=row.get("verified_on") or None,
                # a lookup row with no source_url is unverified -> flag it rather than trust it
                needs_human_review=not row.get("source_url"),
            )
    return None


def resolve_document(name_ar: str, search_fn=None) -> ResolvedDocument:
    """Resolve one required-document name to where it can be obtained.

    `search_fn=None` uses the real retriever; injectable so tests need no index.
    """
    if not (name_ar or "").strip():
        return ResolvedDocument(name_ar=name_ar or "", resolution="unresolved",
                                needs_human_review=True)

    if hit := _from_lookup(name_ar):
        return hit

    if search_fn is None:
        from tools.search_services import search_services
        search_fn = search_services

    try:
        cands = search_fn(name_ar, k=3)
    except Exception:  # noqa: BLE001 — retrieval failure must abstain, never raise into a node
        return ResolvedDocument(name_ar=name_ar, resolution="unresolved", needs_human_review=True)

    if not cands:
        return ResolvedDocument(name_ar=name_ar, resolution="unresolved", needs_human_review=True)

    top, score = cands[0], _cos(cands[0])
    second = _cos(cands[1]) if len(cands) > 1 else 0.0

    # too weak, or two candidates too close to tell apart -> abstain rather than guess
    if score < THETA_DOC or (score - second) < TIE_BAND:
        return ResolvedDocument(name_ar=name_ar, resolution="unresolved",
                                match_score=round(score, 4), needs_human_review=True)

    pid = getattr(top, "post_id", None) or top["post_id"]
    title = getattr(top, "title_ar", None) or top.get("title_ar", "")

    from tools.search_services import get_record
    rec = get_record(pid) or {}
    sec = rec.get("sections") or {}

    return ResolvedDocument(
        name_ar=name_ar,
        resolution="corpus",
        match_score=round(score, 4),
        where_to_obtain=sec.get("where_to_apply") or sec.get("authority") or title,
        fees=sec.get("fees"),
        source_url=rec.get("url"),
        needs_human_review=False,
    )


def resolve_document_dict(name_ar: str) -> dict:
    """Dict-returning adapter for the graph's research node."""
    return resolve_document(name_ar).model_dump()
