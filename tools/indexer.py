"""Build the Chroma index over the corpus (SCOPE §6, TECH_PLAN §3) — G4.

The retrieval unit is the SERVICE, not the chunk: FR2 asks "which service does this query mean",
so chunk scores are aggregated back to a service by MAX. Long services (up to 29 documents) are
still chunked, because embedding a 29-document blob into one vector dilutes it until the
distinctive documents stop mattering.

Chunking is sentence-aware with a CHARACTER budget rather than a token budget. BGE-M3's tokenizer
would give exact counts, but loading it purely to measure costs more than the precision is worth
— the cap exists to bound dilution, not to fit a context window.

Embeddings: BAAI/bge-m3, chosen for Arabic + cross-lingual retrieval (an English query has to
reach an Arabic-only title). Model load is slow when cold, so it is cached at module level and
the index is persisted — the demo must never pay that cost twice. MODEL_ID is overridable so the
G4 human check can compare encoders without editing code.
"""
from __future__ import annotations

import html as htmllib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "data" / "chroma"
CORPUS_DIR = ROOT / "data" / "corpus"
COLLECTION = "dawlati_v1"
# LaBSE is the DEFAULT because it is what the reported numbers were measured with and what is
# actually installed. BGE-M3 was the planned encoder but is a ~2.3 GB download that never
# completed on the build machine (and saturated the connection badly enough to time out our live
# REST calls). Defaulting to a model that is not present would make `streamlit run` fail or
# silently start a multi-gigabyte download — the default must be the thing that works.
# Override with EMBED_MODEL to compare encoders; the index must be rebuilt after changing it.
MODEL_ID = os.environ.get("EMBED_MODEL", "sentence-transformers/LaBSE")

CHUNK_CHARS = 1200      # ~500 tokens of Arabic
CHUNK_OVERLAP = 120     # ~50 tokens

_model = None
_model_id_loaded: str | None = None


def get_model(model_id: str | None = None):
    """Load the encoder once per process. Cold load is slow; the demo depends on this cache."""
    global _model, _model_id_loaded
    want = model_id or MODEL_ID
    if _model is None or _model_id_loaded != want:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(want)
        _model_id_loaded = want
    return _model


_SENT_END = re.compile(r"(?<=[.!?؟\n])\s+|(?<=[،؛])\s+")


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split on sentence boundaries, packing up to `size` chars, carrying `overlap` forward.

    A single sentence longer than `size` is kept WHOLE rather than cut mid-word: a truncated
    Arabic document name is worse than an oversized chunk, because it can silently become a
    different document.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    sentences = [s.strip() for s in _SENT_END.split(text) if s and s.strip()]
    chunks: list[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > size:
            chunks.append(cur)
            cur = ((cur[-overlap:] + " " + s).strip() if overlap else s)
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def clean_title(text: str | None) -> str:
    """Decode HTML entities that survive into catalog titles (e.g. «… ولادة &#8211; وفاة …»).

    Double-unescape: a few titles are double-encoded (&amp;#8211;). These reach the UI and the
    embeddings, so an entity here becomes a visible artefact on screen during the demo.
    """
    return htmllib.unescape(htmllib.unescape(text or "")).strip()


def record_text(rec: dict) -> str:
    """The text representing a service to the retriever.

    Title first because most queries name the service. Authority and where-to-apply are included
    because users ask "where do I go for X" as often as "what do I need for X".
    """
    sec = rec.get("sections") or {}
    parts = [clean_title(rec.get("title_ar")), clean_title(rec.get("title_en"))]
    for key in ("authority", "where_to_apply"):
        if sec.get(key):
            parts.append(sec[key])
    parts.extend(sec.get("required_documents") or [])
    return "\n".join(p for p in parts if p)


def load_corpus() -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CORPUS_DIR.glob("*.json"))]


def load_curated_core() -> set[int]:
    """G3's output. Absent until Job C lands — indexing proceeds with in_curated_core=False."""
    p = ROOT / "data" / "curated_core.json"
    if not p.exists():
        return set()
    data = json.loads(p.read_text(encoding="utf-8"))
    return {c["post_id"] for c in data.get("core", []) if c.get("post_id")}


def build_index(curated_core: set[int] | None = None, reset: bool = True,
                model_id: str | None = None) -> dict:
    """Chunk -> embed -> upsert. Returns build stats for the G4 evidence file."""
    import chromadb

    core = curated_core if curated_core is not None else load_curated_core()
    records = load_corpus()
    if not records:
        raise RuntimeError("data/corpus is empty — run tools/crawler/fetch_service_directory.py")

    ids, docs, metas = [], [], []
    for rec in records:
        # A TITLE-ONLY vector alongside the full-text chunks, and it is load-bearing.
        # Nearly every civil-registry service REQUIRES an ID card as one of its documents, so a
        # query about OBTAINING an ID ("شو الأوراق المطلوبة لبطاقة الهوية") matches the document
        # lists of dozens of unrelated services. Measured: without this, «بطاقة هوية» (#11464)
        # lost top-1 to a building-restoration permit whose document list happens to mention an
        # ID. The title vector is undiluted, so what a service IS can outrank what it REQUIRES.
        title_text = " ".join(p for p in (clean_title(rec.get("title_ar")),
                                              clean_title(rec.get("title_en"))) if p)
        chunks = [title_text] + chunk_text(record_text(rec))
        for i, chunk in enumerate(chunks):
            ids.append(f"{rec['post_id']}:{i}")
            docs.append(chunk)
            metas.append({
                "is_title": i == 0,
                "post_id": rec["post_id"],
                "title_ar": clean_title(rec.get("title_ar")),
                "url": rec.get("url", ""),
                "ministry": rec.get("ministry_term") or "",
                "record_status": rec.get("record_status", "incomplete"),
                "in_curated_core": rec["post_id"] in core,
                "chunk": i,
            })

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:  # noqa: BLE001 — absent on a first build
            pass
    coll = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    model = get_model(model_id)
    embeddings = model.encode(docs, batch_size=16, show_progress_bar=False,
                              normalize_embeddings=True).tolist()
    coll.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)

    return {
        "services": len(records),
        "chunks": len(ids),
        "chunks_per_service": round(len(ids) / len(records), 2),
        "in_curated_core_services": len(core),
        "model": model_id or MODEL_ID,
        "collection": COLLECTION,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    core = load_curated_core()
    print(f"curated core: {len(core)} services"
          + ("" if core else "  (data/curated_core.json absent — G3 not done yet)"))
    for k, v in build_index(curated_core=core).items():
        print(f"  {k}: {v}")
    print(f"\nindex written -> {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
