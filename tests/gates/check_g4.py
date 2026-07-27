"""G4 gate: retrieval calibrated, measured without leakage (VERIFICATION.md G4, A12).

Auto:
  - thresholds calibrated on the DEV set only, then MEASURED ON THE HOLDOUT;
  - holdout top-1 >= 90% (or a correct clarification), abstain on known-out queries,
    clarify on genuinely ambiguous ones;
  - embed latency <= 2 s.

The dev/holdout split is the point of this gate. Calibrating and reporting on the same queries
would produce a number that means nothing, and with a gold set this small (n=12 holdout) the
temptation to tune until it passes is exactly what the split exists to prevent. The confidence
interval is printed because n is small and a bare percentage would overstate the precision.

Usage:  python tests/gates/check_g4.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from agents.nodes.retrieve import classify_outcome  # noqa: E402
from tools.search_services import search_services  # noqa: E402

GOLD = ROOT / "tests" / "retrieval_gold.json"
THRESH_OUT = ROOT / "data" / "retrieval_thresholds.json"
TARGET_TOP1 = 0.90
MAX_EMBED_S = 2.0


_OUTCOME_TO_GOLD = {"not_found": "abstain", "ambiguous": "clarify", "found": "found"}


def outcome(cands, theta_abs: float, theta_amb: float) -> str:
    """Delegate to the SAME function the live retrieve node uses, then map to gold vocabulary.

    Not duplicated on purpose. These two diverged once — the gate scored on cosine while the node
    still thresholded on rrf_score — so the gate reported PASS while the live agent abstained on
    a valid demo query. A gate that measures different logic from the runtime measures nothing.
    """
    return _OUTCOME_TO_GOLD[classify_outcome(cands, theta_abs, theta_amb)]


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson interval — honest about small n, unlike a bare proportion."""
    if n == 0:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def evaluate(cases: list[dict], results: dict, theta_abs: float, theta_amb: float) -> dict:
    hits = {"found": 0, "abstain": 0, "clarify": 0}
    totals = {"found": 0, "abstain": 0, "clarify": 0}
    misses: list[str] = []
    for case in cases:
        want = case["expect"]
        totals[want] += 1
        cands = results[case["query"]]
        got = outcome(cands, theta_abs, theta_amb)
        ok = got == want and (want != "found" or (cands and cands[0].post_id == case["post_id"]))
        if ok:
            hits[want] += 1
        else:
            top = f"#{cands[0].post_id}" if cands else "none"
            misses.append(f"{case['query'][:44]!r} want={want}"
                          + (f"(#{case['post_id']})" if case["post_id"] else "")
                          + f" got={got}({top})")
    return {"hits": hits, "totals": totals, "misses": misses}


def main() -> int:
    if not GOLD.exists():
        print(f"FAIL: {GOLD.relative_to(ROOT)} missing")
        return 2
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    dev, holdout = gold["dev"], gold["holdout"]

    # --- run retrieval ONCE per query, reuse for every threshold trial ----------
    t0 = time.time()
    results: dict[str, list] = {}
    for case in dev + holdout:
        results[case["query"]] = search_services(case["query"], k=5)
    n_q = len(results)
    per_query = (time.time() - t0) / n_q

    # --- calibrate on DEV ONLY -------------------------------------------------
    best, best_score = (0.45, 0.02), -1.0
    grid_abs = [0.0, 0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50, 0.55, 0.60]
    grid_amb = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12]
    for ta in grid_abs:
        for tm in grid_amb:
            r = evaluate(dev, results, ta, tm)
            # BALANCED accuracy (mean of per-class recall), not raw hits. The dev classes are
            # imbalanced (5 found vs 2 abstain), and raw hits let "never abstain" tie with a
            # genuinely calibrated threshold — then the first-wins tie-break picked θ=0, i.e. a
            # system that answers everything. Per-class recall makes abstention count for as
            # much as retrieval, which is the behaviour we actually need: a wrong confident
            # answer is worse than an admitted miss.
            recalls = [r["hits"][c] / r["totals"][c] for c in r["totals"] if r["totals"][c]]
            score = sum(recalls) / len(recalls) if recalls else 0.0
            if score > best_score:
                best, best_score = (ta, tm), score
    theta_abs, theta_amb = best
    dev_res = evaluate(dev, results, theta_abs, theta_amb)

    # --- MEASURE on holdout ----------------------------------------------------
    hold = evaluate(holdout, results, theta_abs, theta_amb)
    n_found = hold["totals"]["found"]
    top1 = hold["hits"]["found"] / n_found if n_found else 0.0
    lo, hi = wilson(hold["hits"]["found"], n_found)

    checks = {
        f"holdout top-1 >= {TARGET_TOP1:.0%}": top1 >= TARGET_TOP1,
        "holdout abstains on known-out queries":
            hold["hits"]["abstain"] == hold["totals"]["abstain"],
        "holdout clarifies on ambiguous queries":
            hold["hits"]["clarify"] == hold["totals"]["clarify"],
        f"retrieval latency <= {MAX_EMBED_S}s/query": per_query <= MAX_EMBED_S,
    }

    dev_hits = sum(dev_res["hits"].values())
    print(f"  calibrated on DEV (n={len(dev)}): theta_abs={theta_abs}  theta_amb={theta_amb}"
          f"   dev balanced-acc {best_score:.2f} ({dev_hits}/{len(dev)} exact)")
    print(f"  MEASURED on HOLDOUT (n={len(holdout)}) — never used for calibration\n")
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\n  info: top-1 {hold['hits']['found']}/{n_found} = {top1:.0%} "
          f"(95% CI {lo:.0%}-{hi:.0%}; n is small, treat the point estimate with care)")
    print(f"  info: abstain {hold['hits']['abstain']}/{hold['totals']['abstain']}   "
          f"clarify {hold['hits']['clarify']}/{hold['totals']['clarify']}")
    print(f"  info: {per_query*1000:.0f} ms/query over {n_q} queries")
    for m in hold["misses"]:
        print(f"  MISS  {m}")

    ok = all(checks.values())
    if ok or True:  # always persist: the graph reports `calibrated` from this file's presence
        THRESH_OUT.write_text(json.dumps({
            "theta_abs": theta_abs, "theta_amb": theta_amb,
            "calibrated_on": "dev", "dev_n": len(dev), "holdout_n": len(holdout),
            "holdout_top1": round(top1, 4), "holdout_top1_ci": [round(lo, 4), round(hi, 4)],
        }, indent=2), encoding="utf-8")

    print(f"\nAUTO GATE: {'PASS' if ok else 'FAIL'}")
    print("HUMAN CHECK: inspect the misses above and give a verdict; compare encoders "
          "(EMBED_MODEL=... python tools/indexer.py). Reviewer: __")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
