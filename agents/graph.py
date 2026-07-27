"""LangGraph wiring (SCOPE §5) — the perceive -> plan -> act -> observe loop the brief requires.

    detect_language -> validate_input -> classify_intent -> retrieve
      -> research (plan -> execute [+ deterministic per-doc freshness] -> <=1 replan)
      -> compose -> validate_schema -> respond

Five terminal branches bypass the happy path: invalid_request, service_not_found,
clarification_needed, error, follow_up.

Every node appends to `state['trace_events']`; that list is the ONLY source for the UI trace
panel and the eval harness (SCOPE §10).

Node timeouts are NOT used: LangGraph's node-level `timeout` is async-only (F33) and this graph
runs sync so the demo stays debuggable. HTTP timeouts live in the tool functions instead.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.nodes import (
    classify_intent, compose, detect_language, research, respond, respond_clarify,
    respond_error, respond_invalid, respond_not_found, retrieve, validate_input, validate_schema,
)
from agents.state import AgentState


# ---------------------------------------------------------------- routing
def route_after_validate(state: dict) -> str:
    """The deterministic guardrail fires before any model call."""
    return "invalid" if state.get("invalid") else "ok"


def route_after_intent(state: dict) -> str:
    intent = (state.get("intent") or {}).get("intent", "service_query")
    if intent == "invalid_request":
        return "invalid"
    return "follow_up" if intent == "follow_up" else "service_query"


def route_after_retrieve(state: dict) -> str:
    return {"found": "found", "ambiguous": "ambiguous"}.get(
        state.get("retrieval_outcome", "not_found"), "not_found")


def route_after_schema(state: dict) -> str:
    return "ok" if state.get("schema_ok") else "error"


def build_graph(adapter=None, search_fn=None, tools=None, curated_core=None):
    """Compile the graph.

    All four dependencies default to None — the FIXTURE path. That is deliberate: G5 must be
    fully traversable, and the offline demo fully runnable, with no API key, no network and no
    Chroma index. Passing real ones switches the same graph to the live path, so the thing
    demoed is the thing that was tested.
    """
    g = StateGraph(AgentState)

    g.add_node("detect_language", detect_language)
    g.add_node("validate_input", validate_input)
    g.add_node("classify_intent", lambda s: classify_intent(s, adapter=adapter))
    g.add_node("retrieve", lambda s: retrieve(s, search_fn=search_fn))
    g.add_node("research", lambda s: research(s, tools=tools))
    g.add_node("compose", lambda s: compose(s, curated_core=curated_core))
    g.add_node("validate_schema", validate_schema)
    g.add_node("respond", respond)
    # terminal branches
    g.add_node("respond_invalid", respond_invalid)
    g.add_node("respond_not_found", respond_not_found)
    g.add_node("respond_clarify", respond_clarify)
    g.add_node("respond_error", respond_error)

    g.set_entry_point("detect_language")
    g.add_edge("detect_language", "validate_input")

    g.add_conditional_edges("validate_input", route_after_validate,
                            {"invalid": "respond_invalid", "ok": "classify_intent"})
    g.add_conditional_edges("classify_intent", route_after_intent,
                            {"invalid": "respond_invalid",
                             "follow_up": "retrieve",      # follow-ups re-retrieve with history
                             "service_query": "retrieve"})
    g.add_conditional_edges("retrieve", route_after_retrieve,
                            {"found": "research",
                             "ambiguous": "respond_clarify",
                             "not_found": "respond_not_found"})

    g.add_edge("research", "compose")
    g.add_edge("compose", "validate_schema")
    g.add_conditional_edges("validate_schema", route_after_schema,
                            {"ok": "respond", "error": "respond_error"})

    for terminal in ("respond", "respond_invalid", "respond_not_found",
                     "respond_clarify", "respond_error"):
        g.add_edge(terminal, END)

    return g.compile()


def run(query: str, **kwargs) -> dict:
    """Convenience entry point used by the UI, the eval harness and check_g5."""
    graph = build_graph(**{k: v for k, v in kwargs.items()
                           if k in {"adapter", "search_fn", "tools", "curated_core"}})
    initial: dict = {"query": query, "trace_events": [],
                     "messages": kwargs.get("messages") or []}
    for k in ("retrieved", "service_record", "resolved_documents", "candidates", "suggestions"):
        if k in kwargs:
            initial[k] = kwargs[k]
    return graph.invoke(initial)
