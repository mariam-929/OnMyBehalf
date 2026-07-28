"""Graph nodes (SCOPE §5). Each node takes AgentState and returns a partial state update.

Every node appends to `state['trace_events']` — that list is the ONLY source for the UI trace
panel and the eval harness (SCOPE §10), so a node that does work without tracing it is invisible
to both the demo and the metrics.
"""
from agents.nodes.compose import (
    compose, respond, respond_clarify, respond_error, respond_invalid, respond_not_found,
    validate_schema,
)
from agents.nodes.intake import classify_intent, detect_language, validate_input
from agents.nodes.research import plan_research, research
from agents.nodes.retrieve import retrieve

__all__ = [
    "detect_language", "validate_input", "classify_intent",
    "retrieve", "plan_research", "research", "compose", "validate_schema", "respond",
    "respond_invalid", "respond_not_found", "respond_clarify", "respond_error",
]
