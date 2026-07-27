"""Reciprocal Rank Fusion (F10/A12) — pure, so it is testable before the index exists.

RRF fuses two ranked lists (BM25 over titles, dense over Chroma) without needing their scores to
be on a comparable scale — which is why it is used here: BM25 scores and cosine similarities are
not commensurable, and normalising them would invent a relationship that isn't there.

    score(d) = Σ_lists 1 / (k + rank_list(d))       k = 60 (standard)

`k` damps the influence of top ranks so a single list cannot dominate the fusion.
"""
from __future__ import annotations

RRF_K = 60


def rrf_fuse(*ranked_lists: list[int], k: int = RRF_K) -> list[tuple[int, float]]:
    """Fuse ranked ID lists into one list of (id, score), best first.

    Each input is ranked BEST FIRST. An item absent from a list simply contributes nothing from
    that list — it is not penalised, which is what lets a strong dense hit survive a BM25 miss
    (the cross-lingual case: an English query against an Arabic-only title).
    """
    scores: dict[int, float] = {}
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    # deterministic: score desc, then id asc, so equal scores never reorder between runs
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def margin(fused: list[tuple[int, float]]) -> float:
    """Score gap between top-1 and top-2 — drives the θ_amb ambiguity branch (FR2).

    A single candidate is unambiguous by definition, so the margin is infinite.
    """
    if len(fused) < 2:
        return float("inf")
    return fused[0][1] - fused[1][1]
