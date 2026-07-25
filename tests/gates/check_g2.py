"""G2 gate: corpus quality (VERIFICATION.md G2 — ajax-ingested, reframed by PR #1).

The service DETAIL pages are empty, so there is no page crawl. The corpus comes structured from
the services-directory admin-ajax endpoint. The risk is not "can we render" but "is the
extraction / document-splitting correct" — fill-rate is NOT correctness.

Auto:
  - data/corpus/*.json exist; all Pydantic-valid; #files == #distinct post_ids (fail-loud);
    >=150 complete (required_documents non-empty); every record has modified_gmt_at_crawl +
    content_hash; unmatched <= ~5%.
  - If data/spike_gold.json has verified entries, score machine extraction vs human gold
    (document recall >= 0.85). If none verified yet -> reports PENDING (not a hard fail).
Human: Maria/Ghina diff 3 civil-registry core services field-by-field vs the live guide + skim 7.

Usage:  python tests/gates/check_g2.py   (run fetch_service_directory.py first)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import CorpusRecord  # noqa: E402
from tools.text_norm import normalize_ar  # noqa: E402


def doc_recall(machine: list[str], gold: list[str]) -> float:
    if not gold:
        return 1.0
    g = {normalize_ar(x) for x in gold}
    m = {normalize_ar(x) for x in machine}
    hit = sum(1 for x in g if any(x in y or y in x for y in m))
    return hit / len(g)


def main():
    cdir = ROOT / "data" / "corpus"
    files = list(cdir.glob("*.json"))
    if not files:
        print("FAIL: data/corpus/*.json missing — run tools/crawler/fetch_service_directory.py first.")
        return 1

    recs, invalid = [], 0
    for f in files:
        try:
            recs.append(CorpusRecord.model_validate_json(f.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            invalid += 1
            print(f"  invalid record {f.name}: {e}")
    ids = {r.post_id for r in recs}
    complete = sum(1 for r in recs if r.record_status == "complete")
    has_meta = all(r.modified_gmt_at_crawl and r.content_hash for r in recs)

    checks = {
        "all records Pydantic-valid": invalid == 0,
        "#files == #distinct post_ids (no overwrite)": len(files) == len(ids) == len(recs),
        ">=150 complete (have documents)": complete >= 150,
        "every record has modified_gmt_at_crawl + content_hash": has_meta,
    }
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"  info: {len(recs)} records, {complete} complete ({100*complete/len(recs):.1f}%)")

    # extraction recall vs human-verified gold
    sg = ROOT / "data" / "spike_gold.json"
    recall_ok = None
    if sg.exists():
        gold = json.loads(sg.read_text(encoding="utf-8"))
        verified = [s for s in gold.get("services", []) if s.get("verified")]
        if verified:
            recalls = [doc_recall(s["machine_documents"], s["gold_documents"]) for s in verified]
            avg = sum(recalls) / len(recalls)
            recall_ok = avg >= 0.85
            print(f"  [{'PASS' if recall_ok else 'FAIL'}] extraction recall {avg:.0%} on "
                  f"{len(verified)} human-verified services (>=85%)")
        else:
            print("  [PENDING] spike_gold.json exists but 0 services verified — "
                  "Maria/Ghina must correct gold_documents + set verified=true.")
    else:
        print("  [PENDING] data/spike_gold.json missing — no extraction-correctness ground truth.")

    auto_ok = all(checks.values()) and recall_ok is not False
    print(f"\nAUTO GATE: {'PASS' if auto_ok else 'FAIL'}"
          f"{' (recall verification still PENDING)' if recall_ok is None else ''}")
    print("\nHUMAN CHECK (Maria/Ghina, reviewer Ghina): open the live guide, diff 3 civil-registry")
    print("core services field-by-field (e.g. 11464 بطاقة هوية, 11554 تسجيل ولادة) + skim 7;")
    print("correct data/spike_gold.json and set verified=true, then re-run.")
    return 0 if auto_ok else 2


if __name__ == "__main__":
    sys.exit(main())
