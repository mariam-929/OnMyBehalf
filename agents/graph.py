"""LangGraph wiring — SKELETON (built at G5, Jul 26 BUILD track).

Graph (SCOPE §5):
  detect_language -> validate_input -> classify_intent -> retrieve
    -> research(plan -> execute[+ system per-doc freshness] -> <=1 replan)
    -> compose -> validate_schema -> respond
  terminal branches: invalid_request, service_not_found, clarification_needed, error, follow_up

Each node appends to state['trace_events']; that list is the ONLY source for the UI trace panel
and the eval harness (SCOPE §10). Nodes are stubs until G5.
"""
from __future__ import annotations

# from langgraph.graph import StateGraph, END
# from agents.state import AgentState

# def build_graph():
#     g = StateGraph(AgentState)
#     g.add_node("detect_language", detect_language)
#     g.add_node("validate_input", validate_input)
#     g.add_node("classify_intent", classify_intent)
#     g.add_node("retrieve", retrieve)
#     g.add_node("research", research)          # bounded loop (A02) + system per-doc freshness (N3)
#     g.add_node("compose", compose)
#     g.add_node("validate_schema", validate_schema)
#     g.add_node("respond", respond)
#     ... edges + conditional routing ...
#     return g.compile()

# TODO(G5): implement nodes in agents/nodes/, wire routing, add unit tests.
