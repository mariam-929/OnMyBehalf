"""Assemble the LIVE agent: real retriever + real tools + real record lookup (G6).

One place builds the live wiring so the UI, the eval harness and check_g6 all exercise the SAME
graph. If the demo ran a differently-wired graph from the one the eval measured, neither number
would mean anything.

The two EXTERNAL tool calls the brief requires are both here and both hit dawlati.gov.lb live:
  check_freshness      GET /wp-json/wp/v2/{type}/{id}  -> modified_gmt vs our snapshot
  live_service_lookup  GET /wp-json/wp/v2/...?search=  -> does this service still exist
They appear in `trace_events`, which is what makes them visible on screen during the demo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_curated_core() -> set[int]:
    p = ROOT / "data" / "curated_core.json"
    if not p.exists():
        return set()
    return {c["post_id"] for c in json.loads(p.read_text(encoding="utf-8")).get("core", [])
            if c.get("post_id")}


def get_adapter_or_none():
    """Groq adapter, or None if no key is configured.

    None is a supported mode, not an error: the graph's fixture path keeps every terminal branch
    reachable without a key, which is what lets the offline demo and the unit tests run.
    """
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        from groq import Groq
        from agents.adapters import get_adapter
        model_id = os.environ.get("MODEL_ID", "openai/gpt-oss-120b")
        # max_retries=0 is what makes the adapters' per-request `timeout` an actual wall-clock
        # bound. The SDK default of 2 retries re-issues a timed-out or 429'd call with exponential
        # backoff, so a 6 s timeout was really taking 20-35 s — measured 18.6 s and 34.0 s on the
        # demo queries once the free tier started rate-limiting. Every model call here has a
        # deterministic fallback, so failing fast costs a plainer sentence; retrying costs the demo.
        return get_adapter(model_id, Groq(api_key=key, max_retries=0))
    except Exception:  # noqa: BLE001 — a bad key must degrade to fixture mode, not crash the UI
        return None


def build_tools() -> dict:
    """The tool dict the research node executes. Each entry is called at most a bounded number
    of times per run (A02/N3)."""
    from tools.check_freshness import check_freshness
    from tools.live_service_lookup import live_service_lookup
    from tools.resolve_document import resolve_document_dict
    from tools.search_services import get_record

    def _freshness(post_id: int):
        rec = get_record(post_id) or {}
        return check_freshness(
            post_id=post_id,
            post_type=rec.get("type", "ministry_service_ser"),
            snapshot_modified_gmt=rec.get("modified_gmt_at_crawl") or rec.get("modified_gmt", ""),
        ).model_dump()

    return {
        "resolve_document": resolve_document_dict,
        "check_freshness": _freshness,
        "live_service_lookup": lambda q: live_service_lookup(q).model_dump(),
    }


def answer(query: str, messages: list[dict] | None = None, offline: bool = False) -> dict:
    """Run one query through the live agent. Returns the final AgentState.

    Two phases. The graph is deliberately record-agnostic — it reads `service_record` from state —
    which is what let G5 verify every branch on fixtures with no index. Live, something has to
    load the record retrieval chose, and this is the only place those two phases are stitched
    together. Phase 1 identifies the service; if it abstains or clarifies, that result is already
    terminal and correct, so phase 2 never runs.

    `offline=True` drops the external tools (the outage drill, G11) while keeping retrieval and
    composition: the answer still comes from the local corpus with citations, it simply cannot
    re-check the source, so freshness degrades to `unverified` and the answer says so.
    """
    from agents.graph import run
    from tools.search_services import get_record, search_fn

    adapter = None if offline else get_adapter_or_none()
    tools = None if offline else build_tools()
    core = load_curated_core()

    # phase 1 — identify
    first = run(query, adapter=adapter, search_fn=lambda q, k=5: search_fn(q, k),
                curated_core=core, messages=messages or [])
    if first.get("retrieval_outcome") != "found":
        return first  # abstained / clarified / invalid — already terminal and correct

    top = (first.get("retrieved") or [])[0]
    pid = top["post_id"] if isinstance(top, dict) else top.post_id
    record = get_record(pid)

    # phase 2 — research + compose against the real record
    return run(query, adapter=adapter, search_fn=lambda q, k=5: search_fn(q, k),
               tools=tools, curated_core=core, messages=messages or [],
               retrieved=first["retrieved"], service_record=record)
