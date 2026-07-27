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


def _cos(c) -> float:
    v = getattr(c, "dense_cos", None)
    if v is None and isinstance(c, dict):
        v = c.get("dense_cos")
    return float(v or 0.0)


def classify_outcome(candidates, theta_abs: float, theta_amb: float) -> str:
    """found | ambiguous | not_found — THE single decision function.

    Both this node and `tests/gates/check_g4.py` call it, and that is the point: they diverged
    once (the gate scored on cosine while the node still thresholded on rrf_score), so the gate
    passed while the live agent abstained on a valid demo query. A gate that measures different
    logic from the runtime measures nothing.

    Abstention reads COSINE, not the RRF score. RRF depends only on RANK, so its top-1 value is
    ~constant (0.016-0.033 measured across the whole gold set) whether the match is perfect or
    nonsense — no RRF threshold can separate in-scope from out-of-scope.
    """
    if not candidates:
        return "not_found"
    top = _cos(candidates[0])
    if top < theta_abs:
        return "not_found"
    gap = top - (_cos(candidates[1]) if len(candidates) > 1 else 0.0)
    return "ambiguous" if gap < theta_amb else "found"


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

    outcome = classify_outcome(candidates, theta_abs, theta_amb)
    top_cos = _cos(candidates[0])
    gap = top_cos - (_cos(candidates[1]) if len(candidates) > 1 else 0.0)
    rrf = [(c["post_id"] if isinstance(c, dict) else c.post_id,
            c["rrf_score"] if isinstance(c, dict) else c.rrf_score) for c in candidates]

    return with_trace(
        state, "retrieve",
        {"retrieved": candidates, "retrieval_outcome": outcome},
        mode=mode, n=len(candidates), outcome=outcome,
        top_cos=round(top_cos, 4), cos_gap=round(gap, 4),
        top_rrf=round(rrf[0][1], 5) if rrf else None,
        rrf_margin=(None if margin(rrf) == float("inf") else round(margin(rrf), 5)),
        theta_abs=theta_abs, theta_amb=theta_amb, calibrated=calibrated,
    )
