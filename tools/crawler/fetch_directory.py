"""G1b: crawl the Dawlati directory into ContactRecord[] (SCOPE §6, A27).

CORRECTION to the original plan: this stub assumed the directory was client-rendered and needed
Playwright. It is not. Both datasets are embedded in the page HTML, so plain `requests` works:

  1. `var directoryEntityData` — a JS object literal with `ministries` (26), `public-institutions`
     (46), `municipalities` (39), `governorates` (0). Carries title, official_url, official_domain,
     `location` (address) and `opening_hours`. Present on BOTH the EN (/en/directory/) and AR
     (/دليل/) pages, which is how each record gets an Arabic name and an English alias.
  2. `article.directory-number-card` — the "Useful Numbers" tab: 15 national hotlines
     (Consumer protection 1739, …) as title + `tel:` link.

MEASURED LIMITATION (2026-07-25): the directory publishes **no ministry switchboard numbers**.
The ministry popups carry location, official site, opening hours and portal links — no phone.
The only phones on the site are the 15 national Useful-Numbers hotlines.

Updated after Mariam's G1b review: 6 of those hotlines are ministry-specific and are now joined
onto their ministry record (`phones` filled 15 → 21/126). **They remain national hotlines, not
service switchboards, and must be labelled that way when surfaced in an answer.** The Interior
complaints line (1744) is deliberately NOT joined to Interior — it is a complaints channel, not a
contact point for a procedure. Contact enrichment therefore stays best-effort exactly as SCOPE §15
anticipated: an answer is still valid without contacts.

Bilingual join is on `official_domain` (minus `www.`), NOT on `key`: Polylang gives the EN and AR
translations different post ids (Ministry of Agriculture is 9773 EN / 9784 AR).

Usage:  python tools/crawler/fetch_directory.py        -> data/contacts.json
        python tools/crawler/fetch_directory.py --dry
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.models import ContactRecord  # noqa: E402
from tools.text_norm import normalize_key  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DIR_EN = "https://dawlati.gov.lb/en/directory/"
DIR_AR = "https://dawlati.gov.lb/%D8%AF%D9%84%D9%8A%D9%84/"
TAXONOMY = "https://dawlati.gov.lb/wp-json/wp/v2/ministry_services_min"
TIMEOUT_S = 60

_NUMBER_CARD = re.compile(
    r'<article class="directory-number-card".*?'
    r'directory-number-title[^>]*>(?P<title>.*?)</h3>'
    r'(?P<rest>.*?)</article>',
    re.S)
_TEL = re.compile(r'href="tel:([^"]+)"')


def extract_entity_data(html: str) -> dict:
    """Pull `var directoryEntityData = {...};` out of the page and parse it as JSON.

    It is a JS object literal, not JSON: keys are bare or single-quoted and trailing commas
    appear, so it is normalised before json.loads. Brace matching is string-aware so a `}`
    inside an address never ends the object early.
    """
    i = html.find("var directoryEntityData")
    if i < 0:
        raise SystemExit("FAIL: directoryEntityData not found — directory markup changed?")
    start = html.index("{", i)
    depth, in_str, esc, end = 0, False, False, None
    for j in range(start, len(html)):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end is None:
        raise SystemExit("FAIL: unbalanced directoryEntityData object")
    blob = html[start:end]
    blob = re.sub(r"(\{|,)(\s*)'([^']+)'(\s*):", r'\1\2"\3"\4:', blob)   # 'key':
    blob = re.sub(r"(\{|,)(\s*)([A-Za-z_]\w*)(\s*):", r'\1\2"\3"\4:', blob)  # key:
    blob = re.sub(r",(\s*[}\]])", r"\1", blob)                            # trailing commas
    return json.loads(blob)


def domain_key(entity: dict) -> str:
    """Join key across languages: official_domain without www./scheme/trailing slash."""
    dom = (entity.get("official_domain") or entity.get("official_url") or "").strip().lower()
    dom = re.sub(r"^https?://", "", dom).rstrip("/")
    return re.sub(r"^www\.", "", dom)


def clean(text: str | None) -> str | None:
    if not text:
        return None
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", text))
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse_useful_numbers(html: str, page_url: str) -> list[dict]:
    """article.directory-number-card -> {title, phones}. The only phones the site publishes."""
    out = []
    for m in _NUMBER_CARD.finditer(html):
        title = clean(m.group("title"))
        phones = [unquote(p).strip() for p in _TEL.findall(m.group("rest"))]
        if title and phones:
            out.append({"title": title, "phones": phones, "url": page_url})
    return out


def fetch(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    html_en = fetch(session, DIR_EN)
    html_ar = fetch(session, DIR_AR)
    data_en = extract_entity_data(html_en)
    data_ar = extract_entity_data(html_ar)

    print("groups (EN):", {k: len(v) for k, v in data_en.items()})
    print("groups (AR):", {k: len(v) for k, v in data_ar.items()})

    # ministry taxonomy slugs, so a contact can be joined to a service's ministry_term
    slug_by_title: dict[str, str] = {}
    page = 1
    while True:
        r = session.get(TAXONOMY, timeout=TIMEOUT_S,
                        params={"per_page": 100, "page": page, "_fields": "slug,name"})
        if r.status_code != 200 or not r.json():
            break
        for t in r.json():
            slug_by_title[normalize_key(t["name"])] = t["slug"]
        page += 1

    crawled_at = datetime.now(timezone.utc).isoformat()
    records: list[ContactRecord] = []

    # ---- entities (ministries / public institutions / municipalities) ----
    for group, items_ar in data_ar.items():
        items_en = {domain_key(e): e for e in data_en.get(group, [])}
        for ent_ar in items_ar:
            key = domain_key(ent_ar)
            ent_en = items_en.get(key, {})
            name_ar = clean(ent_ar.get("title"))
            if not name_ar:
                continue
            name_en = clean(ent_en.get("title"))
            # ministry taxonomy slug via the EN name ("Ministry of Agriculture" -> agriculture)
            term = None
            if name_en:
                stripped = re.sub(r"^ministry of\s+", "", name_en, flags=re.I)
                term = slug_by_title.get(normalize_key(stripped)) or slug_by_title.get(
                    normalize_key(name_en))
            records.append(ContactRecord(
                source="ministires_directory",
                authority_name_ar=name_ar,
                authority_term=term,
                phones=[],   # popups publish no phone; hotlines joined from Useful Numbers below
                address=clean(ent_ar.get("location")) or clean(ent_en.get("location")),
                opening_hours=clean(ent_ar.get("opening_hours")) or clean(ent_en.get("opening_hours")),
                url=(ent_ar.get("official_url") or ent_en.get("official_url") or DIR_AR),
                crawled_at=crawled_at,
            ))

    # ---- useful numbers (the only phones on the site) ----
    numbers_ar = parse_useful_numbers(html_ar, DIR_AR)
    numbers_en = {normalize_key(n["phones"][0]): n for n in parse_useful_numbers(html_en, DIR_EN)}
    for num in numbers_ar:
        records.append(ContactRecord(
            source="useful-numbers-post",
            authority_name_ar=num["title"],
            authority_term=None,
            phones=num["phones"],
            address=None,
            url=num["url"],
            crawled_at=crawled_at,
        ))

    # ---- join ministry hotlines from the Useful Numbers list onto ministry records ----
    # Mariam (G1b review): the popups have no phone, but ~7 ministry hotlines live in the Useful
    # Numbers tab (Education 1747, Environment 1789, Health 1214 …). Match conservatively on the
    # ministry-distinctive name part (strip the "وزارة" word); substring both ways, min len 4, so a
    # municipality/institution can't false-match. Non-ministry hotlines (Ogero, Red Cross) don't match.
    hotlines = [r for r in records if r.source == "useful-numbers-post"]
    joined = 0
    for m in records:
        if m.source != "ministires_directory" or m.phones:
            continue
        mkey = normalize_key(m.authority_name_ar)
        if "وزاره" not in mkey:          # only ministries have a hotline in the list
            continue
        mc = mkey.replace("وزاره", "")
        if len(mc) < 4:
            continue
        for h in hotlines:
            hc = normalize_key(h.authority_name_ar).replace("وزاره", "")
            if len(hc) >= 4 and (hc in mc or mc in hc):
                m.phones = list(h.phones)
                joined += 1
                break
    print(f"  ministry hotlines joined from Useful Numbers: {joined}")

    # ---- coverage ----
    total = len(records)
    with_phone = sum(1 for r in records if r.phones)
    with_addr = sum(1 for r in records if r.address)
    with_term = sum(1 for r in records if r.authority_term)
    print(f"\nContactRecords: {total}")
    print(f"  with phone(s)     {with_phone:>4}/{total}")
    print(f"  with address      {with_addr:>4}/{total}")
    print(f"  joined to a ministry taxonomy slug {with_term:>4}/{total}")
    print(f"  (EN alias unmatched on domain: "
          f"{sum(1 for g, items in data_ar.items() for e in items if domain_key(e) not in {domain_key(x) for x in data_en.get(g, [])})})")

    # coverage against the authorities our corpus actually cites
    corpus_dir = ROOT / "data" / "corpus"
    if corpus_dir.exists():
        terms = {json.loads(p.read_text(encoding="utf-8")).get("ministry_term")
                 for p in corpus_dir.glob("*.json")}
        terms.discard(None)
        covered = {r.authority_term for r in records if r.authority_term} & terms
        print(f"\n  authorities referenced by the corpus: {len(terms)} {sorted(terms)}")
        print(f"  of those with >=1 ContactRecord:      {len(covered)} {sorted(covered)}")
        if terms:
            print(f"  coverage: {100*len(covered)/len(terms):.0f}% (G1b gate: >=60%)")

    if args.dry:
        print("\n--dry: nothing written")
        return 0

    out = ROOT / "data" / "contacts.json"
    out.write_text(json.dumps([json.loads(r.model_dump_json()) for r in records],
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {total} ContactRecords -> data/contacts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
