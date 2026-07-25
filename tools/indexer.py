"""Chunk + embed (BGE-M3) + load Chroma (SCOPE §6, TECH_PLAN §3). Stub — G4 (Jul 26).
Sentence-aware chunking, 500-token cap, 50 overlap; collection 'dawlati_v1', cosine.
"""
from __future__ import annotations

# TODO(G4): sentence-aware chunk CorpusRecords; embed with BAAI/bge-m3; upsert to Chroma by
# post_id:chunk_i; metadata = url, ministry, lang, section, in_curated_core.
def build_index():
    raise NotImplementedError("G4")
