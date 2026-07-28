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
from functools import lru_cache
from pathlib import Path

from agents.models import RetrievedCandidate
from tools.indexer import (CHROMA_DIR, COLLECTION, clean_title, get_model, load_corpus,
                           load_curated_core)
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


# Possessive / attached pronoun suffixes. «تسجيل زواجي» ("registering MY marriage") must match
# the title «تسجيل زواج» — measured: without this, Ghina's own demo question
# «كيف يمكنني تسجيل زواجي في لبنان؟» retrieved the wrong marriage service.
_SUFFIXES = ("هما", "كما", "هم", "هن", "كم", "كن", "نا", "ها", "ي", "ه", "ك")


def _stem(token: str) -> str:
    """Light Arabic stemming: strip the definite article and one attached pronoun suffix.

    Length guards are load-bearing in both directions — «ال» is most of a short word and
    stripping it destroys the term (الام), and a 1-char suffix off a 3-char token leaves noise.
    This is deliberately shallow: a real stemmer would also strip verb prefixes, which would
    collide «تسجيل» with unrelated forms across a corpus this small.
    """
    if len(token) > 3 and token.startswith("ال"):
        token = token[2:]
    for suf in _SUFFIXES:
        if len(token) - len(suf) >= 3 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def _tokens(text: str) -> list[str]:
    """Normalise, then light-stem each token for BM25 matching."""
    return [s for t in normalize_ar(text).split() if (s := _stem(t))]


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


@lru_cache(maxsize=512)
def _encode(query: str) -> tuple[float, ...]:
    """Cache query embeddings — the same string is encoded many times per answer.

    Measured: one answer triggered 10-20 encoder calls. `answer()` runs the graph twice (identify,
    then compose with the record attached) so the user's query is encoded twice, and
    `resolve_document` runs a full retrieval for EVERY required document — five documents means
    five more, each of which may also encode a boilerplate-stripped variant. Encoding is the
    dominant cost per answer; caching it is free correctness-wise because the encoder is
    deterministic for a given string.
    """
    return tuple(get_model().encode([query], normalize_embeddings=True)[0].tolist())


def dense_ranked(query: str, k: int) -> tuple[list[int], dict[int, float]]:
    """Returns (service ids best-first, best cosine per service)."""
    coll = _get_collection()
    vec = [list(_encode(query))]
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

    stripped = strip_boilerplate(query)
    if stripped:
        bm_c = bm25_ranked(stripped, k * 2)
        dn_c, cos_c = dense_ranked(stripped, k * 2)
        channels += [bm_c, dn_c]
        # report the BEST cosine seen for a service across both phrasings — the stripped form is
        # the one that actually resembles the indexed title, so it is usually the honest score
        for pid, c in cos_c.items():
            cos[pid] = max(cos.get(pid, 0.0), c)

    # CORE BOOST as an extra RRF channel, not a filter. The 44 core services were each judged
    # KEEP by a domain expert working her own procedure cluster, so "a human vouched for this
    # service" is real evidence and belongs in the ranking. It was being stored as metadata and
    # then ignored: Ghina's own question «أين يمكنني الحصول على بيان قيد عائلي؟» lost to #11474,
    # a service SHE had explicitly marked SKIP for having zero documents.
    # A channel rather than a filter because non-core services must stay reachable — 149 of 193
    # are non-core and a citizen may legitimately ask about one.
    core = load_curated_core()
    if core:
        channels.append([pid for pid, _ in rrf_fuse(*channels) if pid in core])

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
