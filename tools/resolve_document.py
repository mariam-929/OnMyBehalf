"""Per-document resolution: normalize → corpus → lookup table → abstain (SCOPE FR4, A11).
Stub — implemented at G6 (Jul 27). Returns ResolvedDocument.
"""
from __future__ import annotations

# TODO(G6): Arabic normalize (strip diacritics/tatweel, unify alef/ya); dense+BM25 corpus match;
# lookup-table fuzzy match; θ_doc gate + tie-band => "unresolved" (never attach a doubtful source).
def resolve_document(name_ar: str):
    raise NotImplementedError("G6")
