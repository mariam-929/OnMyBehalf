"""Extract Sections from rendered text via Arabic/EN heading heuristics (SCOPE §6). Stub — G2.
Also the CANONICAL normalize+sha256 used by BOTH crawl and recrawl-diff (F02 — never hash raw HTML).
"""
# TODO(G2): match مستندات/رسوم/مدة/مكان/خطوات + EN; missing section -> None -> record_status incomplete.
def extract_sections(raw_text: str):
    raise NotImplementedError("G2")

def canonical_hash(raw_text: str) -> str:
    import hashlib, re
    norm = re.sub(r"\s+", " ", raw_text).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()
