"""LOCAL best-effort contact enrichment from the crawled /en/directory store (SCOPE §5, A06/A27).
NOT an external call (contacts are not in Dawlati REST — verified 2026-07-25). Stub — G1b/G6.
"""
from __future__ import annotations

# TODO(G1b): load ContactRecord store; match authority_term; return list[ContactOut] or [].
def enrich_contacts(authority_term: str | None):
    return []
