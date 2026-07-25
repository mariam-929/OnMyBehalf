"""G1: enumerate the Dawlati service catalog from the public WordPress REST API.

Verified working 2026-07-25: browser UA required (Cloudflare 403s default clients); all records
carry modified_gmt. Frozen denominators (SCOPE §6): ministry_service_ser 195 + services 24 +
useful-numbers-post 30 = 249 posts (219 are service pages).

Usage: python tools/crawler/enumerate.py  ->  data/catalog.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://dawlati.gov.lb/wp-json/wp/v2"
TYPES = ["ministry_service_ser", "services", "useful-numbers-post"]
FIELDS = "id,link,title,modified_gmt,ministry_services_min"


def fetch_type(t: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = requests.get(f"{BASE}/{t}", headers={"User-Agent": UA},
                         params={"per_page": 100, "page": page, "_fields": FIELDS}, timeout=30)
        if r.status_code == 400:  # past last page
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for d in batch:
            out.append({
                "post_id": d["id"], "type": t, "url": d["link"],
                "title_ar": d["title"]["rendered"], "title_en": None,
                "ministry_term": (d.get("ministry_services_min") or [None])[0],
                "modified_gmt": d.get("modified_gmt"),
            })
        page += 1
        time.sleep(0.5)
    return out


def main():
    catalog = []
    for t in TYPES:
        rows = fetch_type(t)
        print(f"{t}: {len(rows)}")
        catalog.extend(rows)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total: {len(catalog)} -> data/catalog.json")


if __name__ == "__main__":
    sys.exit(main())
