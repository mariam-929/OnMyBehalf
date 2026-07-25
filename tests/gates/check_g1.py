"""G1 gate: service catalog complete & clean (VERIFICATION.md G1).

Auto-PASS: exactly the 3 frozen post types; counts vs 195/24/30 (>5% miss fails); no dup post_ids;
every row has modified_gmt + title_ar + url.
Human check (separate): spot-check 5 random URLs in a browser.

Usage:  python tests/gates/check_g1.py   (run enumerate.py first)
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EXPECTED = {"ministry_service_ser": 195, "services": 24, "useful-numbers-post": 30}
SAMPLE_SEED = 7  # matches the 5 URLs recorded in report/evidence/coverage.md


def main():
    path = ROOT / "data" / "catalog.json"
    if not path.exists():
        print("FAIL: data/catalog.json missing — run tools/crawler/enumerate.py first.")
        sys.exit(1)
    c = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["post_id"] for r in c]
    counts = Counter(r["type"] for r in c)

    checks = {
        "types are exactly the 3 frozen": set(counts) == set(EXPECTED),
        "no duplicate post_ids": len(ids) == len(set(ids)),
        "all rows have modified_gmt": all(r.get("modified_gmt") for r in c),
        "all rows have title_ar + url": all(r.get("title_ar") and r.get("url") for r in c),
    }
    for t, exp in EXPECTED.items():
        got = counts.get(t, 0)
        checks[f"{t} count ~{exp} (got {got})"] = abs(got - exp) <= max(1, exp * 0.05)

    ok = all(checks.values())
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nAUTO GATE: {'PASS' if ok else 'FAIL'}  (total {len(c)})")
    # Seeded so the sample is REPRODUCIBLE: the reviewer's 5 URLs must be the same 5 recorded in
    # report/evidence/coverage.md, or the sign-off can't be re-verified or cited in the report.
    print("\nHUMAN CHECK — open these 5 URLs in a browser; confirm each is a real service")
    print("page whose title matches the catalog (reviewer: Mariam — producer is Ali):")
    for r in random.Random(SAMPLE_SEED).sample(c, 5):
        print(f"  - {r['title_ar'][:40]}  ->  {r['url']}")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
