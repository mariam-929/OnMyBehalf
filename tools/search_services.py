"""RRF-fused hybrid retrieval: BM25(titles) + BGE-M3 dense over Chroma (SCOPE FR2, A10/A12).
Stub — implemented at G4 (Jul 26 DATA track). Returns list[RetrievedCandidate].
"""
from __future__ import annotations

# TODO(G4): BM25 over titles + Chroma dense; fuse by RRF(k=60); θ_abs/θ_amb from DEV set.
def search_services(query: str, k: int = 5):
    raise NotImplementedError("G4")
