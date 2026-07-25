"""G7: re-harvest the directory, diff on canonical hash, queue what changed (SCOPE §6, A09/F02).

Complements `check_freshness`, which asks the *source* whether a post's `modified_gmt` moved.
That signal is necessary but not sufficient: the directory payload we actually answer from is not
the post, so a service's documents or fees can change while `modified_gmt` says nothing, and
`modified_gmt` can move on an edit that changes nothing we extract. This compares the **content we
extracted**, via the canonical hash stored on every CorpusRecord.

Hashing is over normalised text (F02: never hash raw HTML) and reuses `canonical_hash` from
`extract.py` and `harvest()` from `fetch_service_directory.py`, so a diff can never be an artefact
of two parsers drifting apart.

Emitted QueueEvents:
  changed_on_recrawl     — content hash moved for a service we hold
  extraction_incomplete  — a service that had documents now has none (a regression worth a human)
  unreachable_source     — the re-harvest itself failed

Usage:  python tools/crawler/diff_recrawl.py            (diff + queue)
        python tools/crawler/diff_recrawl.py --dry      (report only, queue nothing)
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import CorpusRecord  # noqa: E402
from tools.crawler.fetch_service_directory import harvest  # noqa: E402
from tools.review_queue import append_event  # noqa: E402


def load_stored() -> dict[int, CorpusRecord]:
    out = {}
    for f in sorted(glob.glob(str(ROOT / "data" / "corpus" / "*.json"))):
        rec = CorpusRecord.model_validate_json(Path(f).read_text(encoding="utf-8"))
        out[rec.post_id] = rec
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="report only; queue nothing")
    args = ap.parse_args()

    stored = load_stored()
    if not stored:
        print("FAIL: data/corpus/ empty — run fetch_service_directory.py first.")
        return 1
    print(f"stored corpus: {len(stored)} records")

    try:
        fresh_records = harvest(verbose=False)["records"]
    except Exception as e:  # noqa: BLE001  source down -> one queue event, not 193
        print(f"re-harvest FAILED: {type(e).__name__}: {e}")
        if not args.dry:
            append_event("unreachable_source", subject_label="services directory (re-harvest)",
                         source="recrawl", details=f"{type(e).__name__}: {e}")
        return 2

    fresh = {r.post_id: r for r in fresh_records}
    print(f"re-harvested : {len(fresh)} records\n")

    changed, vanished, appeared, regressed = [], [], [], []
    for post_id, old in stored.items():
        new = fresh.get(post_id)
        if new is None:
            vanished.append(old)
            continue
        if new.content_hash != old.content_hash:
            changed.append((old, new))
        if old.record_status == "complete" and new.record_status == "incomplete":
            regressed.append((old, new))
    appeared = [r for pid, r in fresh.items() if pid not in stored]

    print(f"changed content hash : {len(changed)}")
    print(f"no longer returned   : {len(vanished)}")
    print(f"newly appeared       : {len(appeared)}")
    print(f"documents regressed  : {len(regressed)}")

    for old, new in changed[:20]:
        n_old = len(old.sections.required_documents or [])
        n_new = len(new.sections.required_documents or [])
        print(f"   [changed] {old.post_id} {old.title_ar[:44]}  docs {n_old}->{n_new}")
    for rec in vanished[:10]:
        print(f"   [gone]    {rec.post_id} {rec.title_ar[:44]}")
    for rec in appeared[:10]:
        print(f"   [new]     {rec.post_id} {rec.title_ar[:44]}")

    if args.dry:
        print("\n--dry: nothing queued")
        return 0

    queued = 0
    for old, new in changed:
        n_old = len(old.sections.required_documents or [])
        n_new = len(new.sections.required_documents or [])
        ev = append_event(
            "changed_on_recrawl", subject_label=old.title_ar, subject_post_id=old.post_id,
            source="recrawl", source_url=old.url,
            details=f"content hash {old.content_hash[:12]} -> {new.content_hash[:12]}; "
                    f"documents {n_old} -> {n_new}; fees "
                    f"{'set' if old.sections.fees else 'null'} -> "
                    f"{'set' if new.sections.fees else 'null'}")
        queued += ev is not None
    for old, _new in regressed:
        ev = append_event(
            "extraction_incomplete", subject_label=old.title_ar, subject_post_id=old.post_id,
            source="recrawl", source_url=old.url,
            details="service previously had required_documents and now has none")
        queued += ev is not None
    for rec in vanished:
        ev = append_event(
            "unreachable_source", subject_label=rec.title_ar, subject_post_id=rec.post_id,
            source="recrawl", source_url=rec.url,
            details="service no longer returned by the directory endpoint")
        queued += ev is not None

    print(f"\nqueued {queued} new event(s) "
          f"(duplicates of still-open events are suppressed — A09)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
