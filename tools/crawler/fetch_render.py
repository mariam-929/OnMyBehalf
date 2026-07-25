"""Playwright render of JS-rendered service detail pages (SCOPE §6, A13). Stub — G2 (Jul 26).
10-page spike FIRST (save data/spike_gold.json), score field recall, then full crawl.
"""
# TODO(G2): playwright chromium; goto->networkidle->inner_text; concurrency 3, 1s delay, retry x2.
def fetch_render(url: str) -> str:
    raise NotImplementedError("G2")
