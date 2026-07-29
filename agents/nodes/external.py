"""The external-source branch: one last look before the graph tells a citizen "not found".

Sits between `retrieve` and `respond_not_found` and NOWHERE ELSE. Every path that produces an
answer today reaches `research` directly from `retrieve`, so this node is unreachable from all of
them — no currently-passing case can regress through it. That is wiring, not a test result.

`external_fn=None` is the default and makes the node a pure pass-through, so the fixture path,
`--offline`, and any caller that does not opt in behave exactly as they did before this existed.

What it does NOT do: decide anything with a model, or invent a record. `tools/external_source.py`
matches the query against a hand-curated three-URL registry and extracts deterministically. If
nothing matches, the graph proceeds to `respond_not_found` unchanged.
"""
from __future__ import annotations

from agents.nodes.trace import with_trace


def external_lookup_node(state: dict, external_fn=None) -> dict:
    """Try the curated external sources. Sets `service_record` on a hit, changes nothing on a miss.

    On a hit it also sets `service_freshness` to the external source's own honest label
    (`unverified` — that site publishes no modification timestamp), because the deterministic
    freshness step in `research` is skipped for records with no Dawlati `post_id`.
    """
    if external_fn is None:
        return with_trace(state, "external_lookup", {}, mode="disabled", hit=False)

    # agents/runtime.py runs the graph TWICE (identify, then research against the real record).
    # On the second pass retrieval still says not_found, so we arrive here again — with the record
    # already in state. Re-fetching would double the HTTP cost and, worse, could serve the second
    # pass a different snapshot than the first if the site changed between them.
    if state.get("service_record"):
        record = state["service_record"]
        if not record.get("source_domain"):
            return with_trace(state, "external_lookup", {}, mode="already_resolved", hit=False)
        # Re-assert freshness and the flag. Returning {} here dropped both on the second pass, and
        # compose fell back to its default "not checked in this run" — so the answer stopped saying
        # whether the bytes came off the live site or the snapshot, which is the one thing an
        # unverifiable source MUST disclose.
        from tools.external_source import external_freshness

        return with_trace(state, "external_lookup",
                          {"service_freshness": external_freshness(record),
                           "external_source_used": True},
                          mode="already_resolved", hit=True,
                          source_domain=record.get("source_domain"),
                          served_from=record.get("served_from"))

    query = state.get("query", "") or ""
    language = state.get("language", "ar")

    try:
        record = external_fn(query, language)
    except Exception as exc:  # noqa: BLE001 — the fallback must never turn a miss into a crash
        return with_trace(state, "external_lookup", {}, mode="error", hit=False,
                          error=str(exc)[:120])

    if not record:
        return with_trace(state, "external_lookup", {}, mode="live", hit=False,
                          note="no curated external source matches this query")

    from tools.external_source import external_freshness

    n_docs = len((record.get("sections") or {}).get("required_documents") or [])
    return with_trace(
        state, "external_lookup",
        {"service_record": record,
         "service_freshness": external_freshness(record),
         "external_source_used": True},
        mode="live", hit=True,
        source_domain=record.get("source_domain"),
        source_url=record.get("url"),
        served_from=record.get("served_from"),
        n_documents=n_docs,
    )


def route_after_external(state: dict) -> str:
    """A record means we can answer after all; otherwise the original not-found response stands."""
    return "found" if state.get("service_record") else "not_found"
