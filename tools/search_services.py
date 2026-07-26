"""RRF-fused hybrid retrieval: BM25(titles) + BGE-M3 dense over Chroma (SCOPE FR2, A12).

Returns `RetrievedCandidate[]` plus an FR2 outcome — `found` / `ambiguous` / `not_found` — so the
graph's `retrieve` node never has to re-derive the decision.

Fusion is Reciprocal Rank Fusion at k=60 (TECH_PLAN §1): score = Σ 1/(k + rank_i). RRF is used
for RANKING because BM25 scores and cosine similarities are not on a comparable scale.

**RRF ranks; cosine decides.** Thresholding on the RRF score was tried first and does not work:
the score is bounded (max 2/61 ≈ 0.0328 with two channels) and encodes mostly *whether both
channels returned the document at all*, not how relevant it is. Measured failures of that design:
an out-of-scope English query ("how do I apply for a French visa") scored 0.0284 — higher than
many correct Arabic hits — and "passport renewal" confidently returned `إصدار جواز سفر للخيل`,
a horse passport. Dense cosine is comparable across queries, so **abstention and ambiguity are
decided on cosine**, while RRF still orders the list.

**The lexical channel is gated to positive BM25 scores.** With an English query, BM25 over Arabic
titles matches nothing yet still emits a full ranking; those zero-relevance documents entered the
fusion at rank 1 and outscored a dense hit at cos 0.61. Documents scoring 0 now contribute no
lexical rank at all.

Thresholds are calibrated on a DEV set and measured on a separate HOLDOUT (A12) by
`tests/gates/check_g4.py`; the values here are that script's output, not guesses.

Usage:
    from tools.search_services import search_services
    result = search_services("كيف أسجل زواج؟")
    result.outcome, result.candidates
"""
from __future__ import annotations

import functools
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.models import RetrievedCandidate  # noqa: E402
from tools.text_norm import normalize_ar  # noqa: E402

CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "dawlati_v1"
MODEL_NAME = "BAAI/bge-m3"
RRF_K = 60

# Calibrated at G4 on the DEV split; see report/evidence/retrieval.md. Overridden by
# data/retrieval_thresholds.json when that file exists, so recalibration needs no code change.
# Both operate on DENSE COSINE, not on the RRF score — see the module docstring.
THETA_ABS = 0.55    # best dense cosine below this -> not_found (abstain)
THETA_AMB = 0.06    # cosine gap between top-1 and top-2 below this -> ambiguous -> clarify


def _thresholds() -> tuple[float, float]:
    p = ROOT / "data" / "retrieval_thresholds.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        return float(d.get("theta_abs", THETA_ABS)), float(d.get("theta_amb", THETA_AMB))
    return THETA_ABS, THETA_AMB


@dataclass
class SearchResult:
    query: str
    outcome: str                       # "found" | "ambiguous" | "not_found"
    candidates: list[RetrievedCandidate] = field(default_factory=list)
    margin: float = 0.0                # cosine gap top1 - top2 (drives `ambiguous`)
    top_score: float = 0.0             # best dense cosine (drives `not_found`)
    top_rrf: float = 0.0               # best fused score — ordering only, never a threshold


@functools.lru_cache(maxsize=1)
def _load():
    """Model + Chroma collection + BM25 over titles. Cached: loading BGE-M3 costs seconds."""
    import chromadb
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    coll = client.get_collection(COLLECTION)

    got = coll.get(include=["metadatas"])
    metas = got["metadatas"]
    ids = got["ids"]
    # BM25 over TITLES only (TECH_PLAN §1): the body is mostly document lists whose shared
    # boilerplate ("نسخة عن", "صورة طبق الأصل") would otherwise dominate the lexical channel.
    corpus_tokens = [normalize_ar(m["title_ar"]).split() for m in metas]
    bm25 = BM25Okapi(corpus_tokens)
    return model, coll, bm25, ids, metas


def _rrf(rank_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked in rank_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def search_services(query: str, k: int = 5, pool: int = 20) -> SearchResult:
    """Hybrid retrieve. `pool` is the per-channel depth fused before truncating to k."""
    model, coll, bm25, ids, metas = _load()
    theta_abs, theta_amb = _thresholds()
    by_id = {i: m for i, m in zip(ids, metas)}

    # dense channel
    qv = model.encode([query], normalize_embeddings=True)[0]
    dense = coll.query(query_embeddings=[qv.tolist()], n_results=min(pool, len(ids)))
    dense_ids = dense["ids"][0]
    dense_cos = {i: 1.0 - d for i, d in zip(dense_ids, dense["distances"][0])}

    # lexical channel — gated to POSITIVE scores. An English query matches no Arabic title, but
    # BM25 still returns a full ranking of zero-scoring documents; letting those in at rank 1
    # outranked genuine dense hits (measured: an ISBN request beat `بطاقة هوية` at cos 0.61).
    scores = bm25.get_scores(normalize_ar(query).split())
    bm25_ranked = [ids[i] for i in sorted(range(len(ids)), key=lambda x: -scores[x])[:pool]
                   if scores[i] > 0]
    bm25_rank = {doc_id: r for r, doc_id in enumerate(bm25_ranked, start=1)}

    fused = _rrf([dense_ids, bm25_ranked])
    ordered = sorted(fused.items(), key=lambda kv: -kv[1])[:k]

    candidates = [
        RetrievedCandidate(
            post_id=int(by_id[doc_id]["post_id"]),
            title_ar=by_id[doc_id]["title_ar"],
            title_en=None,
            rrf_score=round(score, 6),
            dense_cos=round(dense_cos.get(doc_id, 0.0), 4),
            bm25_rank=bm25_rank.get(doc_id),
        )
        for doc_id, score in ordered
    ]

    # FR2 outcome on DENSE COSINE (comparable across queries), not the RRF score.
    # Deliberately the cosine of the TOP-RANKED candidate, not the best cosine in the list: we
    # abstain when the document we would actually answer with is not similar enough. These differ
    # when the two channels disagree — for "تجديد جواز السفر" RRF ranks the horse passport first
    # (cos 0.508) while `بطاقة هوية` has a higher cosine (0.554) but no lexical support. Taking the
    # max there would have answered with an unrelated service instead of abstaining, so a negative
    # margin is a real signal that the channels disagree, not a bug.
    top_cos = candidates[0].dense_cos if candidates else 0.0
    second_cos = candidates[1].dense_cos if len(candidates) > 1 else 0.0
    margin = top_cos - second_cos

    # Exact-title equality short-circuits to `found`: if the user typed the service name verbatim,
    # a thin margin against a near-identical sibling is not real ambiguity.
    exact = bool(candidates) and normalize_ar(candidates[0].title_ar) == normalize_ar(query)
    if not candidates or top_cos < theta_abs:
        outcome = "not_found"
    elif exact:
        outcome = "found"
    elif margin < theta_amb:
        outcome = "ambiguous"
    else:
        outcome = "found"

    return SearchResult(query=query, outcome=outcome, candidates=candidates,
                        margin=round(margin, 4), top_score=round(top_cos, 4),
                        top_rrf=round(candidates[0].rrf_score, 6) if candidates else 0.0)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "كيف أسجل زواج؟"
    res = search_services(q)
    print(f"query   : {res.query}")
    print(f"outcome : {res.outcome}   top_cos={res.top_score}  cos_margin={res.margin}"
          f"  (rrf={res.top_rrf})")
    for c in res.candidates:
        print(f"   {c.rrf_score:.5f}  cos={c.dense_cos:.3f}  bm25#{c.bm25_rank}  "
              f"{c.post_id}  {c.title_ar[:60]}")
