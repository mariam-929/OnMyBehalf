"""Retrieval node (FR2): RRF-fused candidates -> found | ambiguous | not-found.

Thresholds are DEV-calibrated at G4 against a holdout (A12). The defaults here are placeholders
so the graph is traversable at G5; G4 overwrites them from `data/retrieval_thresholds.json`.
They are named and loaded rather than inlined precisely so that a calibrated value cannot be
mistaken for a hand-picked one in the report.
"""
from __future__ import annotations

import json
from pathlib import Path

from agents.nodes.trace import with_trace

_THRESH_PATH = Path(__file__).resolve().parents[2] / "data" / "retrieval_thresholds.json"

# placeholders until G4 calibration writes the file (SCOPE FR2)
DEFAULT_THETA_ABS = 0.010   # below this top-1 score => service_not_found
DEFAULT_THETA_AMB = 0.002   # margin(top1, top2) below this => clarification_needed


def load_thresholds() -> tuple[float, float, bool]:
    """Returns (theta_abs, theta_amb, calibrated). `calibrated` is reported in the trace so an
    uncalibrated run can never be mistaken for a calibrated one in the eval."""
    if _THRESH_PATH.exists():
        try:
            d = json.loads(_THRESH_PATH.read_text(encoding="utf-8"))
            return float(d["theta_abs"]), float(d["theta_amb"]), True
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return DEFAULT_THETA_ABS, DEFAULT_THETA_AMB, False


def retrieve(state: dict, search_fn=None) -> dict:
    """Populate `retrieved` and decide the routing outcome.

    `search_fn=None` is the fixture path: candidates are read straight from state, so the graph
    and all its branches are exercisable before the Chroma index exists (G4).
    """
    from tools.rrf import margin  # local import: tools.rrf has no heavy deps, keep it lazy anyway

    query = state.get("query", "") or ""
    if search_fn is None:
        candidates = list(state.get("retrieved") or [])
        mode = "fixture"
    else:
        candidates = search_fn(query, k=5)
        mode = "live"

    theta_abs, theta_amb, calibrated = load_thresholds()

    if not candidates:
        return with_trace(state, "retrieve", {"retrieved": [], "retrieval_outcome": "not_found"},
                          mode=mode, n=0, outcome="not_found", calibrated=calibrated)

    scored = [(c["post_id"] if isinstance(c, dict) else c.post_id,
               c["rrf_score"] if isinstance(c, dict) else c.rrf_score) for c in candidates]
    scored.sort(key=lambda kv: (-kv[1], kv[0]))
    top_score = scored[0][1]
    gap = margin(scored)

    if top_score < theta_abs:
        outcome = "not_found"
    elif gap < theta_amb:
        outcome = "ambiguous"
    else:
        outcome = "found"

    return with_trace(
        state, "retrieve",
        {"retrieved": candidates, "retrieval_outcome": outcome},
        mode=mode, n=len(candidates), outcome=outcome, top_score=round(top_score, 5),
        margin=(None if gap == float("inf") else round(gap, 5)),
        theta_abs=theta_abs, theta_amb=theta_amb, calibrated=calibrated,
    )
