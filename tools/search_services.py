"""Hybrid retrieval: BM25 over titles + dense over Chroma, fused by RRF (FR2, A10/A12).

Two channels because they fail in opposite directions:
  BM25   exact on Arabic wording, blind to an English query against an Arabic-only title.
  DENSE  cross-lingual and paraphrase-tolerant, but will happily return something plausible for
         a service that does not exist — and 19 of 22 ministries publish nothing, so "does not
         exist" is the COMMON case here, not the rare one.
RRF fuses them without pretending BM25 scores and cosine similarities share a scale.

Chunk scores collapse to the SERVICE by MAX: one strongly-matching chunk should identify its
service, and averaging would punish long services for having many chunks.
"""
from __future__ import annotations

import re
from pathlib import Path

from agents.models import RetrievedCandidate
from tools.indexer import CHROMA_DIR, COLLECTION, clean_title, get_model, load_corpus
from tools.rrf import rrf_fuse
from tools.text_norm import normalize_ar

ROOT = Path(__file__).resolve().parents[1]

_bm25 = None
_bm25_ids: list[int] = []
_records: dict[int, dict] = {}
_collection = None


# Interrogative boilerplate. Users ask «شو المستندات المطلوبة لتسجيل ولادة؟» but the index holds
# «تسجيل ولادة» — the question wrapper is 60% of the query and dilutes the embedding until the
# service name stops dominating. Measured before this was added: «شو المستندات المطلوبة لإعادة
# قيد مطلقة؟» retrieved the WRONG service at cos 0.483, while the bare title «إعادة قيد مطلقة»
# scored 1.000 on the right one. Stripping is applied as an EXTRA channel, never as a
# replacement — if the pattern misfires, the raw query still votes.
_BOILERPLATE = re.compile(
    r"^\s*(?:"
    r"شو\s+(?:هي\s+)?(?:المستندات|الأوراق|الاوراق|الوثائق)\s+(?:المطلوبة|اللازمة)?\s*(?:ل|لـ)?"
    r"|ما\s+هي\s+(?:المستندات|الأوراق|الوثائق)\s+(?:المطلوبة|اللازمة)?\s*(?:ل|لـ)?"
    r"|شو\s+بدي\s*(?:ل|لـ)?"
    r"|كيف\s+(?:بسجل|أسجل|اسجل|بطلع|أطلع|بقدر|يمكنني|احصل|أحصل\s+على)\s*(?:ل|لـ)?"
    r"|ما\s+هي\s+إجراءات\s*"
    r"|what\s+documents?\s+(?:do\s+i\s+need\s+)?(?:to|for)\s+"
    r"|what\s+(?:do\s+)?i\s+need\s+(?:to|for)\s+"
    r"|how\s+(?:do|can)\s+i\s+(?:get|register|obtain|apply\s+for)\s+"
    r"|how\s+to\s+(?:get|register|obtain|apply\s+for)\s+"
    r")", re.I)
_TRAILING_Q = re.compile(r"[?؟\s]+$")


def strip_boilerplate(query: str) -> str:
    """Reduce a natural question toward the service name. Returns '' if nothing was stripped."""
    q = _TRAILING_Q.sub("", query or "")
    stripped = _BOILERPLATE.sub("", q).strip()
    return stripped if stripped and stripped != q.strip() else ""


def _tokens(text: str) -> list[str]:
    """Normalise, then strip the Arabic definite article «ال» from each token (light stemming).

    Without this, «بطاقة الهوية» in a query does not match «بطاقة هوية» in the title, because
    «الهويه» and «هويه» are different BM25 terms. Measured: stripping the article moved the
    flagship ID-card query from a MISS to a top-1 hit. Tokens of 3 characters or fewer are left
    alone — «ال» is most of a short word, and stripping it there destroys the term (e.g. «الام»).
    """
    out: list[str] = []
    for t in normalize_ar(text).split():
        if len(t) > 3 and t.startswith("ال"):
            t = t[2:]
        if t:
            out.append(t)
    return out


def _load_bm25() -> None:
    """BM25 over TITLES only, not full document text.

    Deliberate: document text is long and highly repetitive across civil-registry services (nearly
    every one lists «بيان قيد عائلي»), so BM25 over documents ranks by how many COMMON documents a
    service happens to list rather than by what the service IS. Titles are what users type.
    """
    global _bm25, _bm25_ids, _records
    if _bm25 is not None:
        return
    from rank_bm25 import BM25Okapi

    corpus = load_corpus()
    _records = {r["post_id"]: r for r in corpus}
    _bm25_ids = [r["post_id"] for r in corpus]
    _bm25 = BM25Okapi([_tokens(f"{r.get('title_ar','')} {r.get('title_en') or ''}")
                       for r in corpus])


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection(COLLECTION)
    return _collection


def bm25_ranked(query: str, k: int) -> list[int]:
    _load_bm25()
    scores = _bm25.get_scores(_tokens(query))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    return [_bm25_ids[i] for i in order[:k] if scores[i] > 0]


def dense_ranked(query: str, k: int) -> tuple[list[int], dict[int, float]]:
    """Returns (service ids best-first, best cosine per service)."""
    coll = _get_collection()
    vec = get_model().encode([query], normalize_embeddings=True).tolist()
    # over-fetch: k chunks can collapse into far fewer distinct services
    res = coll.query(query_embeddings=vec, n_results=min(k * 4, 50),
                     include=["metadatas", "distances"])
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    best: dict[int, float] = {}
    order: list[int] = []
    for meta, dist in zip(metas, dists):
        pid = int(meta["post_id"])
        cos = 1.0 - float(dist)          # chroma cosine DISTANCE -> similarity
        if pid not in best:
            order.append(pid)
            best[pid] = cos
        else:
            best[pid] = max(best[pid], cos)
    return order[:k], best


def search_services(query: str, k: int = 5) -> list[RetrievedCandidate]:
    """RRF-fused candidates, best first. This is the `search_fn` the graph's retrieve node takes.

    Up to FOUR channels: BM25 and dense over the raw query, plus BM25 and dense over the
    boilerplate-stripped query when stripping changed anything. RRF is built to fuse exactly this
    kind of heterogeneous evidence, and adding the stripped query as extra votes rather than as a
    replacement means a misfiring strip pattern can never lose a result the raw query found.
    """
    _load_bm25()
    bm = bm25_ranked(query, k * 2)
    dn, cos = dense_ranked(query, k * 2)
    channels = [bm, dn]

    core = strip_boilerplate(query)
    if core:
        bm_c = bm25_ranked(core, k * 2)
        dn_c, cos_c = dense_ranked(core, k * 2)
        channels += [bm_c, dn_c]
        # report the BEST cosine seen for a service across both phrasings — the stripped form is
        # the one that actually resembles the indexed title, so it is usually the honest score
        for pid, c in cos_c.items():
            cos[pid] = max(cos.get(pid, 0.0), c)

    fused = rrf_fuse(*channels)[:k]
    bm_rank = {pid: i + 1 for i, pid in enumerate(bm)}
    return [
        RetrievedCandidate(
            post_id=pid,
            # entity-decoded: raw catalog titles carry «&#8211;» which would otherwise reach the
            # UI and the demo screen verbatim
            title_ar=clean_title(_records.get(pid, {}).get("title_ar")),
            title_en=clean_title(_records.get(pid, {}).get("title_en")) or None,
            rrf_score=score,
            dense_cos=cos.get(pid, 0.0),
            bm25_rank=bm_rank.get(pid),
        )
        for pid, score in fused
    ]


def get_record(post_id: int) -> dict | None:
    _load_bm25()
    return _records.get(post_id)


def search_fn(query: str, k: int = 5) -> list[dict]:
    """Dict-returning adapter for the graph node (which accepts dicts or models)."""
    return [c.model_dump() for c in search_services(query, k)]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    q = " ".join(sys.argv[1:]) or "شو المستندات المطلوبة لتسجيل ولادة؟"
    print(f"query: {q}\n")
    for c in search_services(q):
        print(f"  rrf={c.rrf_score:.5f}  cos={c.dense_cos:.3f}  bm25={c.bm25_rank}  "
              f"#{c.post_id}  {c.title_ar[:60]}")
