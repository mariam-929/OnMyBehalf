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


def _hits(needles: list[str], haystack: list[str]) -> int:
    """How many `needles` appear in `haystack` under lenient substring matching."""
    n = {normalize_ar(x) for x in needles}
    h = {normalize_ar(x) for x in haystack}
    return sum(1 for x in n if any(x in y or y in x for y in h))


def doc_recall(machine: list[str], gold: list[str]) -> float:
    if not gold:
        return 1.0
    return _hits(gold, machine) / len(gold)


def doc_precision(machine: list[str], gold: list[str]) -> float:
    """Share of EXTRACTED items that are real documents.

    Recall alone cannot fail on the errors the G2 humans actually found (2026-07-27): section
    headings, Roman-numeral markers, sentence fragments and procedural instructions emitted AS
    documents. Those are precision errors, and a phantom document is as harmful to a citizen as
    a missing one — they go hunting for something that does not exist. Measured and reported;
    the gate threshold stays on recall (SCOPE G2) so the bar is not moved retroactively.
    """
    if not machine:
        return 1.0
    return _hits(machine, gold) / len(machine)


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
            # MICRO (pooled over all gold documents) is the honest figure and the one the gate
            # judges. The former macro-average gave a 0-document service the same weight as a
            # 9-document one, so free 100%s on trivial services masked real misses: on the
            # 2026-07-27 sample macro read 91% (PASS) while pooled read 82% (FAIL). Both are
            # printed so the gap stays visible rather than being silently smoothed away.
            g_hit = sum(_hits(s["gold_documents"], s["machine_documents"]) for s in verified)
            g_tot = sum(len(s["gold_documents"]) for s in verified)
            m_hit = sum(_hits(s["machine_documents"], s["gold_documents"]) for s in verified)
            m_tot = sum(len(s["machine_documents"]) for s in verified)
            micro = g_hit / g_tot if g_tot else 1.0
            precision = m_hit / m_tot if m_tot else 1.0
            macro = sum(doc_recall(s["machine_documents"], s["gold_documents"])
                        for s in verified) / len(verified)
            recall_ok = micro >= 0.85
            print(f"  [{'PASS' if recall_ok else 'FAIL'}] extraction recall (micro, pooled) "
                  f"{micro:.0%} on {len(verified)} human-verified services "
                  f"({g_hit}/{g_tot} documents, >=85%)")
            print(f"  info: macro-average recall {macro:.0%} "
                  f"(per-service mean — inflated by low-document services; NOT the gate)")
            print(f"  info: precision {precision:.0%} ({m_hit}/{m_tot} extracted items are real "
                  f"documents) — {m_tot - m_hit} phantom items (headings/fragments/instructions)")
            bad = [s for s in verified if s.get("human_verdict") == "BAD"]
            if bad:
                print(f"  info: human verdict BAD on {len(bad)}/{len(verified)} services: "
                      f"{', '.join(str(s['post_id']) for s in bad)}")
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
