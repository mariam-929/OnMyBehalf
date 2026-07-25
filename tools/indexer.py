"""G4: embed the corpus with BGE-M3 and load it into Chroma (SCOPE §6, TECH_PLAN §3).

Indexing unit is the SERVICE, not a chunk. The original plan specified sentence-aware chunking at
a 500-token cap, which was written when the corpus was expected to be long crawled pages. It is
not: the ajax corpus is short structured records (median `raw_text` is a few hundred characters,
the longest well under the model's window), so chunking would only fragment a document list away
from the title that identifies it — the opposite of what retrieval needs here. One vector per
service, built from title + authority + where + documents + fees.

Embeddings: BAAI/bge-m3 (multilingual, strong on Arabic — arXiv 2402.03216, 2506.06339), cosine.
Fallback `--model intfloat/multilingual-e5-base` per TECH_PLAN if bge-m3 is too slow or too large.

Usage:  python tools/indexer.py                 -> data/chroma/ collection 'dawlati_v1'
        python tools/indexer.py --model intfloat/multilingual-e5-base --collection dawlati_e5
        python tools/indexer.py --probe "بطاقة هوية"   (quick sanity query after building)
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import CorpusRecord  # noqa: E402

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_COLLECTION = "dawlati_v1"
CHROMA_DIR = ROOT / "data" / "chroma"


def load_corpus() -> list[CorpusRecord]:
    files = sorted(glob.glob(str(ROOT / "data" / "corpus" / "*.json")))
    if not files:
        raise SystemExit("FAIL: data/corpus/ is empty — run tools/crawler/fetch_service_directory.py")
    return [CorpusRecord.model_validate_json(Path(f).read_text(encoding="utf-8")) for f in files]


def embed_text(rec: CorpusRecord) -> str:
    """What actually gets embedded.

    Title first and once more at the end: queries are overwhelmingly title-shaped ("how do I
    register a marriage"), and repeating it keeps the title dominant in a pooled representation
    without dropping the document/fee terms that disambiguate near-identical civil-registry titles
    (`وثيقة زواج لزوجين لبنانيين` vs `... لزوجة لبنانية وزوج أجنبي`).
    """
    s = rec.sections
    parts = [rec.title_ar]
    if s.authority:
        parts.append(s.authority)
    if s.where_to_apply:
        parts.append(s.where_to_apply)
    if s.required_documents:
        parts.append(" ".join(s.required_documents))
    if s.fees:
        parts.append(s.fees)
    parts.append(rec.title_ar)
    return "\n".join(parts)


def build_index(model_name: str = DEFAULT_MODEL, collection_name: str = DEFAULT_COLLECTION,
                batch_size: int = 16) -> dict:
    import chromadb
    from sentence_transformers import SentenceTransformer

    records = load_corpus()
    print(f"corpus: {len(records)} records")

    t0 = time.time()
    model = SentenceTransformer(model_name)
    print(f"model {model_name} loaded in {time.time()-t0:.1f}s "
          f"(dim {model.get_sentence_embedding_dimension()})")

    texts = [embed_text(r) for r in records]
    t0 = time.time()
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                           show_progress_bar=False, convert_to_numpy=True)
    embed_s = time.time() - t0
    print(f"embedded {len(texts)} docs in {embed_s:.1f}s ({embed_s/len(texts)*1000:.0f} ms/doc)")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(collection_name)   # full rebuild; the corpus is small
    except Exception:
        pass
    coll = client.create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    coll.add(
        ids=[str(r.post_id) for r in records],
        embeddings=[v.tolist() for v in vectors],
        documents=texts,
        metadatas=[{
            "post_id": r.post_id,
            "title_ar": r.title_ar,
            "url": r.url,
            "ministry_term": r.ministry_term or "",
            "record_status": r.record_status,
            "n_documents": len(r.sections.required_documents or []),
            "has_fees": bool(r.sections.fees),
        } for r in records],
    )
    print(f"collection '{collection_name}' -> {coll.count()} vectors in {CHROMA_DIR}")
    return {"model": model_name, "collection": collection_name, "n": coll.count(),
            "embed_seconds": round(embed_s, 2), "dim": model.get_sentence_embedding_dimension()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--probe", help="run a sanity query after building")
    args = ap.parse_args()

    info = build_index(args.model, args.collection)

    if args.probe:
        import chromadb
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(args.model)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        coll = client.get_collection(args.collection)
        t0 = time.time()
        qv = model.encode([args.probe], normalize_embeddings=True)[0]
        res = coll.query(query_embeddings=[qv.tolist()], n_results=5)
        print(f"\nprobe '{args.probe}'  ({time.time()-t0:.2f}s)")
        for md, dist in zip(res["metadatas"][0], res["distances"][0]):
            print(f"   cos={1-dist:.3f}  {md['post_id']}  {md['title_ar'][:60]}")

    (ROOT / "data" / "index_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
