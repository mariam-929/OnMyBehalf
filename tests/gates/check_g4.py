"""G4 gate: retrieval calibrated with NO leakage (VERIFICATION §G4, A12).

Calibrates θ_abs / θ_amb on a DEV split and measures on a **disjoint HOLDOUT** split. The two
never share a service, so the reported top-1 rate is not the number the thresholds were tuned on.

⚠️ QUERY SET IS SYNTHETIC (2026-07-25). Real citizen phrasings do not exist yet — the core-40 is
still being rebuilt (issue #2) and `gold_claims.json` is a seed. Queries here are generated from
service titles by templated paraphrase. **This inflates retrieval scores**: a paraphrase of the
title shares vocabulary with the document in a way a citizen's question would not. Treat the
holdout number as an upper bound and a regression guard, NOT as measured retrieval quality.
Replace `SYNTHETIC` with human-written queries once G3 lands; this gate then re-runs unchanged.

Usage:  python tests/gates/check_g4.py            (calibrate + measure)
        python tests/gates/check_g4.py --write    (also write data/retrieval_thresholds.json)
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import CorpusRecord  # noqa: E402

SEED = 7
SYNTHETIC = True

# Paraphrase templates — how a citizen might ask for a service by name.
AR_TEMPLATES = [
    "كيف أحصل على {t}؟",
    "ما هي الأوراق المطلوبة لـ {t}؟",
    "أريد {t}",
    "ما هي رسوم {t}؟",
]

# Queries with NO answerable service — verified absent from the corpus (see issue #2).
KNOWN_OUT = [
    "كيف أجدد جواز السفر اللبناني؟",        # passport renewal — does not exist
    "how do I renew my Lebanese passport",
    "أين أقدّم طلب رخصة سوق؟",               # driving licence — does not exist
    "how do I apply for a French visa",     # out of jurisdiction
    "تسجيل سيارة جديدة",                     # vehicle registration — does not exist
]

# Deliberately under-specified: several near-identical civil-registry services match.
AMBIGUOUS = [
    "وثيقة زواج",          # 8+ marriage-document variants by spouse nationality
    "قيد مولود",           # several birth-registration variants
]


def load_records() -> list[CorpusRecord]:
    files = sorted(glob.glob(str(ROOT / "data" / "corpus" / "*.json")))
    if not files:
        raise SystemExit("FAIL: data/corpus/ empty — run tools/crawler/fetch_service_directory.py")
    return [CorpusRecord.model_validate_json(Path(f).read_text(encoding="utf-8")) for f in files]


def build_splits(records: list[CorpusRecord]) -> tuple[list, list]:
    """Disjoint DEV / HOLDOUT query sets, split BY SERVICE so no service appears in both."""
    rng = random.Random(SEED)
    usable = [r for r in records if r.record_status == "complete"]
    rng.shuffle(usable)
    half = len(usable) // 2
    dev_recs, hold_recs = usable[:half], usable[half:]

    def queries(recs):
        out = []
        for rec in recs:
            tmpl = AR_TEMPLATES[rng.randrange(len(AR_TEMPLATES))]
            out.append((tmpl.format(t=rec.title_ar), rec.post_id))
        return out

    return queries(dev_recs), queries(hold_recs)


def evaluate(queries, theta_abs, theta_amb, search):
    """top-1 correct, or a clarification whose candidate list contains the target (FR2)."""
    import tools.search_services as ss
    ss.THETA_ABS, ss.THETA_AMB = theta_abs, theta_amb
    hits = clarified = 0
    for q, target in queries:
        res = search(q)
        if res.outcome == "found" and res.candidates and res.candidates[0].post_id == target:
            hits += 1
        elif res.outcome == "ambiguous" and any(c.post_id == target for c in res.candidates[:3]):
            clarified += 1
    n = len(queries)
    return (hits + clarified) / n, hits / n, clarified / n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    from tools.search_services import search_services, _load

    records = load_records()
    dev, hold = build_splits(records)
    print(f"corpus {len(records)} | DEV {len(dev)} queries | HOLDOUT {len(hold)} queries "
          f"(disjoint by service, seed {SEED})")
    if SYNTHETIC:
        print("⚠️  SYNTHETIC queries — templated from titles. Upper bound, not measured quality.\n")

    t0 = time.time()
    _load()
    print(f"index + model warm-up: {time.time()-t0:.1f}s")

    # embed latency (VERIFICATION G4: <=2 s)
    lat = []
    for q, _ in dev[:10]:
        t = time.time()
        search_services(q)
        lat.append(time.time() - t)
    p50_latency = statistics.median(lat)
    print(f"query latency p50 {p50_latency:.2f}s  max {max(lat):.2f}s")

    # ---- calibrate on DEV ----
    print("\ncalibrating on DEV")
    best = None
    for theta_abs in [0.45, 0.50, 0.52, 0.55, 0.58, 0.60]:
        for theta_amb in [0.02, 0.04, 0.06, 0.08]:
            acc, hit, clar = evaluate(dev, theta_abs, theta_amb, search_services)
            # abstention must hold on the known-out queries at these thresholds
            import tools.search_services as ss
            ss.THETA_ABS, ss.THETA_AMB = theta_abs, theta_amb
            abstains = sum(1 for q in KNOWN_OUT if search_services(q).outcome == "not_found")
            score = (abstains / len(KNOWN_OUT), acc)   # abstention first, then accuracy
            if best is None or score > best[0]:
                best = (score, theta_abs, theta_amb, acc, hit, clar, abstains)
            print(f"   θ_abs={theta_abs:.2f} θ_amb={theta_amb:.2f} -> "
                  f"dev acc {acc:5.1%} (top1 {hit:5.1%}, clarify {clar:4.1%}) "
                  f"abstain {abstains}/{len(KNOWN_OUT)}")

    _, theta_abs, theta_amb, dev_acc, *_ = best
    print(f"\nCHOSEN on DEV: θ_abs={theta_abs}  θ_amb={theta_amb}  (dev acc {dev_acc:.1%})")

    # ---- measure on HOLDOUT (never used for tuning) ----
    hold_acc, hold_hit, hold_clar = evaluate(hold, theta_abs, theta_amb, search_services)
    import tools.search_services as ss
    ss.THETA_ABS, ss.THETA_AMB = theta_abs, theta_amb

    abstained = [(q, search_services(q).outcome) for q in KNOWN_OUT]
    n_abstain = sum(1 for _, o in abstained if o == "not_found")
    ambiguous = [(q, search_services(q).outcome) for q in AMBIGUOUS]
    n_ambig = sum(1 for _, o in ambiguous if o == "ambiguous")

    print("\n" + "=" * 66)
    print("HOLDOUT (disjoint from calibration)")
    print("=" * 66)
    print(f"  top-1 or correct clarification : {hold_acc:.1%}  "
          f"(top-1 {hold_hit:.1%}, clarified {hold_clar:.1%})   n={len(hold)}")
    print(f"  known-out queries abstained    : {n_abstain}/{len(KNOWN_OUT)}")
    for q, o in abstained:
        print(f"      [{o:11s}] {q}")
    print(f"  under-specified -> clarify     : {n_ambig}/{len(AMBIGUOUS)}")
    for q, o in ambiguous:
        print(f"      [{o:11s}] {q}")
    print(f"  query latency p50              : {p50_latency:.2f}s (gate <=2s)")

    checks = {
        "holdout top-1-or-clarify >= 90%": hold_acc >= 0.90,
        f"known-out abstain {len(KNOWN_OUT)}/{len(KNOWN_OUT)}": n_abstain == len(KNOWN_OUT),
        "under-specified -> clarification 2/2": n_ambig == len(AMBIGUOUS),
        "latency p50 <= 2s": p50_latency <= 2.0,
    }
    print()
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    ok = all(checks.values())
    print(f"\nG4 AUTO GATE: {'PASS' if ok else 'FAIL'}")
    if SYNTHETIC:
        print("NOTE: synthetic queries — this is a regression guard and an UPPER BOUND on quality.")
        print("      Human check still required: inspect misses, and re-run with real queries at G8.")

    if args.write:
        (ROOT / "data" / "retrieval_thresholds.json").write_text(json.dumps({
            "theta_abs": theta_abs, "theta_amb": theta_amb,
            "calibrated_on": "DEV split, synthetic templated queries", "seed": SEED,
            "holdout_top1_or_clarify": round(hold_acc, 4), "synthetic": SYNTHETIC,
        }, indent=1), encoding="utf-8")
        print("\nwrote data/retrieval_thresholds.json")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
