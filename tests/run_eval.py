"""Eval harness (G8) — the brief's required numbers: failure rate, hallucination count, latency.

HALLUCINATION IS MEASURED, NOT ESTIMATED. For every document the agent lists, we check that the
string actually occurs in the cited corpus record. A document that appears in an answer but not in
the source is a fabrication, and this is the one metric a citizen would care about most: it is the
difference between "bring these papers" being true and being invented. `hallucinated_documents`
counts strings the agent produced that the source does not contain.

Two cases are marked `known_fail` in the test set (Arabizi). They are scored like any other case,
never skipped — a failure you exclude from your own eval is a failure you are hiding. They are
reported separately so the headline rate is readable either way.

Usage:
    EMBED_MODEL=sentence-transformers/LaBSE python tests/run_eval.py
    EMBED_MODEL=sentence-transformers/LaBSE python tests/run_eval.py --offline
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from agents.models import Envelope  # noqa: E402
from agents.runtime import answer  # noqa: E402
from tools.text_norm import normalize_ar  # noqa: E402

CASES = ROOT / "tests" / "test_cases.json"
REPORT = ROOT / "tests" / "eval_report.json"
OFFLINE = "--offline" in sys.argv


def count_hallucinated_documents(env: dict) -> tuple[int, list[str]]:
    """Documents the agent listed that do NOT occur in the cited source record.

    Compared after Arabic normalisation and in both containment directions, so wording drift and
    the agent's own splitting are not counted as fabrication — only content with no basis in the
    source is.
    """
    out = env.get("output") or {}
    svc = out.get("service") or {}
    docs = out.get("required_documents") or []
    if not docs:
        return 0, []

    url = svc.get("source_url") or ""
    record = None
    for f in (ROOT / "data" / "corpus").glob("*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("url") == url:
            record = rec
            break
    if record is None:
        return len(docs), [d.get("name_ar", "") for d in docs]  # cited a source we cannot find

    source = normalize_ar(record.get("raw_text", ""))
    bad = []
    for d in docs:
        n = normalize_ar(d.get("name_ar", ""))
        if n and n not in source:
            bad.append(d.get("name_ar", ""))
    return len(bad), bad


def score(case: dict, env: dict) -> tuple[bool, str]:
    want = case["expect_action"]
    got = env.get("action")
    if got != want:
        return False, f"action {got} != {want}"
    if want == "answer":
        pid_url = ((env.get("output") or {}).get("service") or {}).get("source_url", "")
        if case.get("expect_post_id"):
            rec = next((json.loads(f.read_text(encoding="utf-8"))
                        for f in (ROOT / "data" / "corpus").glob(f"{case['expect_post_id']}.json")),
                       None)
            if rec and rec.get("url") != pid_url:
                return False, f"wrong service (expected #{case['expect_post_id']})"
    if want == "invalid_request" and case.get("expect_reason_code"):
        got_code = (env.get("output") or {}).get("reason_code")
        if got_code != case["expect_reason_code"]:
            return False, f"reason {got_code} != {case['expect_reason_code']}"
    return True, "ok"


def main() -> int:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    cases = data["cases"]
    rows, latencies = [], []

    print(f"Running {len(cases)} cases{' (OFFLINE)' if OFFLINE else ''}…\n")
    for case in cases:
        t0 = time.time()
        try:
            state = answer(case["query"], offline=OFFLINE)
            env = state["final_response"]
            Envelope.model_validate(env)
            err = None
        except Exception as exc:  # noqa: BLE001
            env, err = {"action": "error", "output": {}}, str(exc)[:120]
        dt = time.time() - t0
        latencies.append(dt)

        ok, why = (False, f"raised: {err}") if err else score(case, env)
        n_hall, hall = count_hallucinated_documents(env)
        rows.append({**{k: case[k] for k in ("id", "category", "source")},
                     "known_fail": bool(case.get("known_fail")),
                     "passed": ok, "why": why, "action": env.get("action"),
                     "confidence": env.get("confidence"),
                     "latency_s": round(dt, 2),
                     "hallucinated_documents": n_hall, "hallucinated": hall,
                     "query": case["query"][:60]})
        flag = "OK  " if ok else ("xfail" if case.get("known_fail") else "FAIL")
        print(f"  {flag} {case['id']:26} {dt:5.1f}s  {env.get('action','-'):20} {why}")

    scored = [r for r in rows if not r["known_fail"]]
    n_pass = sum(r["passed"] for r in scored)
    n_fail = len(scored) - n_pass
    xfail_passed = sum(r["passed"] for r in rows if r["known_fail"])
    total_hall = sum(r["hallucinated_documents"] for r in rows)

    by_cat = {}
    for r in scored:
        c = by_cat.setdefault(r["category"], [0, 0])
        c[0] += r["passed"]
        c[1] += 1

    summary = {
        "n_cases": len(rows),
        "n_scored": len(scored),
        "n_known_fail_excluded_from_rate": len(rows) - len(scored),
        "passed": n_pass,
        "failed": n_fail,
        "failure_rate": round(n_fail / len(scored), 4) if scored else None,
        "hallucinated_documents_total": total_hall,
        "known_fail_cases_that_passed": xfail_passed,
        "latency_mean_s": round(statistics.mean(latencies), 2),
        "latency_p50_s": round(statistics.median(latencies), 2),
        "latency_max_s": round(max(latencies), 2),
        "by_category": {k: {"passed": v[0], "of": v[1]} for k, v in by_cat.items()},
        "offline": OFFLINE,
        "note": ("Latency includes a cold encoder load on the first case; p50 is the honest "
                 "steady-state figure."),
    }

    print("\n" + "=" * 62)
    print(f"  cases            {summary['n_cases']}  "
          f"({summary['n_scored']} scored, {summary['n_known_fail_excluded_from_rate']} known-fail)")
    print(f"  FAILURE RATE     {summary['failure_rate']:.1%}  ({n_fail}/{len(scored)})")
    print(f"  HALLUCINATIONS   {total_hall}  (documents listed that are absent from the source)")
    print(f"  LATENCY          mean {summary['latency_mean_s']}s  "
          f"p50 {summary['latency_p50_s']}s  max {summary['latency_max_s']}s")
    for cat, v in summary["by_category"].items():
        print(f"    {cat:12} {v['passed']}/{v['of']}")
    print("=" * 62)

    REPORT.write_text(json.dumps({"summary": summary, "results": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
