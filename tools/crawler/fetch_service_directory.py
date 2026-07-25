"""G2 ingester: harvest the Dawlati services directory into CorpusRecord[].

REPLACES the planned per-page crawl. The service pages are empty — 0 of 249 posts carry any
content in REST, and a fully rendered page yields ~430 chars of chrome. The corpus lives behind
the services-guide admin-ajax endpoint, one call per ministry, already structured:

    POST /wp-admin/admin-ajax.php
        action=omsar_load_directory_ministry_services
        nonce=<from `var ajaxConfig` on the guide page>
        ministry=<ministry_services_min taxonomy slug>
        directory_type=ministry-services
        post_type=ministry_service_ser
        taxonomy=ministry_services_min
        relationship_field=ministry

    -> {"success":true,"data":{"services":[{title, directorate, sub_directorate, department,
        unit, code, description_html, required_documents_html, fees_html, notes_html,
        doc_title, doc_url}, ...]}}

Evidence + fill rates: report/evidence/ajax_probe.md. Measured 2026-07-25: 195 services,
181 (92.8%) with required documents, 136 (69.7%) with fees.

The payload carries NO post_id and NO modified_gmt, both of which FR6 check_freshness needs, so
each service is joined to data/catalog.json on a normalised title key. Unmatched services are
written to data/corpus_unmatched.json rather than being given a guessed post_id.

Usage:  python tools/crawler/fetch_service_directory.py        (run enumerate.py first)
        python tools/crawler/fetch_service_directory.py --dry  (no files written)
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import CorpusRecord, Sections  # noqa: E402
from tools.crawler.extract import canonical_hash  # noqa: E402  (one hash impl, F02)
from tools.text_norm import normalize_key  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
GUIDE = "https://dawlati.gov.lb/%d8%af%d9%84%d9%8a%d9%84-%d8%a7%d9%84%d8%ae%d8%af%d9%85%d8%a7%d8%aa/"
AJAX = "https://dawlati.gov.lb/wp-admin/admin-ajax.php"
TAXONOMY = "https://dawlati.gov.lb/wp-json/wp/v2/ministry_services_min"
DELAY_S = 0.5           # politeness between ministry calls
TIMEOUT_S = 60

# a NUMBERED/bulleted top-level entry: "1.", "2-", "3 –", "•"
_ITEM_NUM = re.compile(r"^\s*(?:\d+\s*[.\-–)]|[•●▪◦*])")
# a dash-led SUB-item: continuation of the entry above (e.g. the pest species under one document)
_SUB_ITEM = re.compile(r"^\s*[-–—]\s*")
# heading line that introduces the list rather than being a document
_HEADING = re.compile(r"(المستندات|الوثائق|المرفقات|المطلوب)\s*.*:\s*$")


def html_to_lines(fragment: str | None) -> list[str]:
    """<p>a<br/>b</p> -> ['a', 'b'], entities decoded, tags dropped, blanks removed."""
    if not fragment:
        return []
    t = re.sub(r"<\s*br\s*/?\s*>", "\n", fragment, flags=re.I)
    t = re.sub(r"</\s*(p|li|div|tr)\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = htmllib.unescape(t)
    lines = []
    for raw in t.split("\n"):
        line = re.sub(r"[ \t ]+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines


def html_to_text(fragment: str | None) -> str | None:
    lines = html_to_lines(fragment)
    return "\n".join(lines) if lines else None


def parse_documents(fragment: str | None) -> list[str] | None:
    """required_documents_html -> list of document strings, or None if the field is empty.

    None means EXTRACTION FAILED / nothing published (FR12 -> record_status incomplete). It is
    never an empty list, so a caller can distinguish "no documents published" from "zero required".

    Splitting rule, driven by how the source actually behaves (measured, not assumed):
      * numbered/bulleted line ("1.", "2-", "•")  -> new document;
      * dash-led line ("– MELOIDOGYNE spp")       -> SUB-item, appended to the document above;
      * unmarked line                             -> new document.

    The last case matters: Dawlati frequently omits numbering entirely (e.g. `بطاقة هوية` lists
    four unnumbered requirements before jumping to "6."). Treating unmarked lines as
    continuations merged four separate documents into one blob and hid requirements from the
    citizen, so each <br/>-separated line is its own document unless it is dash-led.

    Splitting is heuristic and the source text is uneven (it contains its own typos and
    mid-word breaks). The G2 human field-check must verify document lists against the live guide.
    """
    lines = html_to_lines(fragment)
    if not lines:
        return None

    # drop a leading "المستندات المطلوبة:" style heading
    if lines and _HEADING.search(lines[0]):
        lines = lines[1:]
    if not lines:
        return None

    docs: list[str] = []
    for line in lines:
        if docs and _SUB_ITEM.match(line):
            docs[-1] = f"{docs[-1]} {line}".strip()
            continue
        cleaned = _ITEM_NUM.sub("", line).strip() or line.strip()
        docs.append(cleaned)
    return [d for d in docs if d] or None


def join_where(svc: dict) -> str | None:
    """directorate / sub_directorate / department / unit -> the administrative path to apply at."""
    parts = [svc.get(k, "").strip() for k in
             ("directorate", "sub_directorate", "department", "unit")]
    parts = [p for p in parts if p]
    return " – ".join(parts) if parts else None


def build_raw_text(svc: dict, sections: Sections, authority: str | None) -> str:
    """The text the indexer embeds. Title first (it carries most of the retrieval signal)."""
    chunks = [svc["title"].strip()]
    if authority:
        chunks.append(authority)
    if sections.where_to_apply:
        chunks.append(sections.where_to_apply)
    if sections.required_documents:
        chunks.append("المستندات المطلوبة: " + " | ".join(sections.required_documents))
    if sections.fees:
        chunks.append("الرسوم: " + sections.fees)
    notes = html_to_text(svc.get("notes_html"))
    if notes:
        chunks.append("ملاحظات: " + notes)
    return "\n".join(chunks)


def build_title_index(catalog: list[dict]) -> dict[str, list[dict]]:
    """normalised title -> candidate catalog rows, `ministry_service_ser` first.

    Two source quirks make a plain dict wrong:
      * hamza variants — `…و/أو…` (11698) and `…و/او…` (11598) are SEPARATE posts whose titles
        normalise identically, so a dict silently keeps one and both directory services join to
        it, overwriting a corpus file;
      * cross-type duplicates — the same procedure exists as `ministry_service_ser` 11595 and
        `services` 11378. The directory queries post_type=ministry_service_ser, so that type wins.
    """
    index: dict[str, list[dict]] = {}
    for row in catalog:
        index.setdefault(normalize_key(row["title_ar"]), []).append(row)
    for rows in index.values():
        rows.sort(key=lambda r: 0 if r["type"] == "ministry_service_ser" else 1)
    return index


def pick_match(candidates: list[dict], title: str, used: set[int]) -> dict | None:
    """Choose one catalog row per directory service, never reusing a post_id.

    Exact title equality (after entity-unescaping) wins over a merely normalised match, so the
    hamza pair resolves to the right post rather than to whichever sorted first.
    """
    if not candidates:
        return None
    free = [c for c in candidates if c["post_id"] not in used]
    pool = free or candidates
    want = htmllib.unescape(htmllib.unescape(title or "")).strip()
    for cand in pool:
        if htmllib.unescape(htmllib.unescape(cand["title_ar"])).strip() == want:
            return cand
    return pool[0]


def fetch_nonce(session: requests.Session) -> str:
    html = session.get(GUIDE, timeout=TIMEOUT_S).text
    m = re.search(r"var\s+ajaxConfig\s*=\s*\{[^}]*?nonce\s*:\s*[\"']([a-f0-9]+)[\"']", html, re.S)
    if not m:
        raise SystemExit("FAIL: could not find ajaxConfig nonce on the guide page — markup changed?")
    return m.group(1)


def fetch_ministries(session: requests.Session) -> list[dict]:
    terms, page = [], 1
    while True:
        r = session.get(TAXONOMY, timeout=TIMEOUT_S,
                        params={"per_page": 100, "page": page, "_fields": "id,slug,name,count"})
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        terms.extend(batch)
        page += 1
    return terms


def fetch_ministry_services(session: requests.Session, nonce: str, slug: str) -> list[dict]:
    r = session.post(AJAX, timeout=TIMEOUT_S, data={
        "action": "omsar_load_directory_ministry_services",
        "nonce": nonce,
        "ministry": slug,
        "directory_type": "ministry-services",
        "post_type": "ministry_service_ser",
        "taxonomy": "ministry_services_min",
        "relationship_field": "ministry",
    })
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"ajax success=false for {slug}: {str(payload)[:200]}")
    return payload.get("data", {}).get("services", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args()

    catalog_path = ROOT / "data" / "catalog.json"
    if not catalog_path.exists():
        print("FAIL: data/catalog.json missing — run tools/crawler/enumerate.py first.")
        return 1
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    by_title = build_title_index(catalog)
    used_post_ids: set[int] = set()
    collisions: list[dict] = []

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "X-Requested-With": "XMLHttpRequest",
                            "Referer": GUIDE})

    nonce = fetch_nonce(session)
    print(f"nonce: {nonce}")
    terms = fetch_ministries(session)
    print(f"ministry terms: {len(terms)}\n")

    crawled_at = datetime.now(timezone.utc).isoformat()
    records: list[CorpusRecord] = []
    unmatched: list[dict] = []
    empty_ministries: list[str] = []

    print(f"{'ministry':36s} {'svcs':>5} {'docs':>5} {'fees':>5} {'joined':>7}")
    print("-" * 64)
    for term in terms:
        slug, name = term["slug"], term.get("name", "")
        try:
            services = fetch_ministry_services(session, nonce, slug)
        except Exception as e:  # noqa: BLE001
            print(f"{slug[:35]:36s} ERROR {type(e).__name__}: {e}")
            continue
        if not services:
            empty_ministries.append(slug)
            print(f"{slug[:35]:36s} {0:>5}")
            time.sleep(DELAY_S)
            continue

        n_docs = n_fees = n_join = 0
        for svc in services:
            docs = parse_documents(svc.get("required_documents_html"))
            fees = html_to_text(svc.get("fees_html"))
            sections = Sections(
                required_documents=docs,
                fees=fees,
                processing_time=None,   # not published in the directory payload — never invented
                where_to_apply=join_where(svc),
                authority=name or None,
                steps=None,             # description_html is empty on every record (measured 0/195)
            )
            if docs:
                n_docs += 1
            if fees:
                n_fees += 1

            candidates = by_title.get(normalize_key(svc.get("title")), [])
            match = pick_match(candidates, svc.get("title"), used_post_ids)
            if not match:
                unmatched.append({"title": svc.get("title"), "ministry": slug,
                                  "has_documents": bool(docs)})
                continue
            if match["post_id"] in used_post_ids:
                # every candidate already taken: a genuine 1:N source duplicate, not a bug here.
                collisions.append({"title": svc.get("title"), "ministry": slug,
                                   "post_id": match["post_id"], "has_documents": bool(docs)})
                continue
            used_post_ids.add(match["post_id"])
            n_join += 1

            raw_text = build_raw_text(svc, sections, name)
            records.append(CorpusRecord(
                post_id=match["post_id"],
                type=match["type"],
                url=match["url"],
                title_ar=match["title_ar"],
                title_en=match.get("title_en"),
                ministry_term=slug,
                modified_gmt=match["modified_gmt"],
                raw_text=raw_text,
                sections=sections,
                crawled_at=crawled_at,
                modified_gmt_at_crawl=match["modified_gmt"],
                content_hash=canonical_hash(raw_text),
                record_status="complete" if docs else "incomplete",
            ))
        print(f"{slug[:35]:36s} {len(services):>5} {n_docs:>5} {n_fees:>5} {n_join:>7}")
        time.sleep(DELAY_S)

    total = len(records)
    print("\n" + "=" * 64)
    print(f"CorpusRecords built: {total}   unmatched (no catalog post_id): {len(unmatched)}"
          f"   collisions (source duplicate): {len(collisions)}")
    if len(used_post_ids) != total:
        print(f"FAIL: {total} records but {len(used_post_ids)} distinct post_ids — "
              f"records would overwrite each other on write.")
        return 2
    if total:
        with_docs = sum(1 for r in records if r.sections.required_documents)
        with_fees = sum(1 for r in records if r.sections.fees)
        complete = sum(1 for r in records if r.record_status == "complete")
        print(f"  required_documents  {with_docs:>4}/{total} ({100*with_docs/total:5.1f}%)")
        print(f"  fees                {with_fees:>4}/{total} ({100*with_fees/total:5.1f}%)")
        print(f"  record_status=complete {complete:>4}/{total} ({100*complete/total:5.1f}%)")
        docs_per = [len(r.sections.required_documents or []) for r in records
                    if r.sections.required_documents]
        if docs_per:
            print(f"  documents per service: min {min(docs_per)}, max {max(docs_per)}, "
                  f"mean {sum(docs_per)/len(docs_per):.1f}")
    print(f"  ministries returning 0 services: {len(empty_ministries)}/{len(terms)}")

    if args.dry:
        print("\n--dry: nothing written")
        return 0

    outdir = ROOT / "data" / "corpus"
    outdir.mkdir(parents=True, exist_ok=True)
    for stale in outdir.glob("*.json"):   # never leave a previous run's records behind
        stale.unlink()
    for rec in records:
        (outdir / f"{rec.post_id}.json").write_text(
            rec.model_dump_json(indent=1), encoding="utf-8")
    (ROOT / "data" / "corpus_unmatched.json").write_text(
        json.dumps({"unmatched": unmatched, "collisions": collisions},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    written = len(list(outdir.glob("*.json")))
    print(f"\nwrote {written} records -> data/corpus/*.json")
    print(f"wrote {len(unmatched)} unmatched + {len(collisions)} collisions "
          f"-> data/corpus_unmatched.json")
    if written != total:
        print(f"FAIL: built {total} records but {written} files exist on disk.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
