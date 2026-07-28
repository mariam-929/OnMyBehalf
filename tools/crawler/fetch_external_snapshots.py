"""Capture the committed snapshots for tools/external_source.py.

Six pages: three registry entries x {ar, en}. Written to data/external/ and COMMITTED (unlike
data/corpus/, which is gitignored and rebuilt) because the offline demo and a fresh clone must
both be able to answer a passport question with no network.

Usage:  python tools/crawler/fetch_external_snapshots.py
        python tools/crawler/fetch_external_snapshots.py --verify   (extract only, no write)

Re-run when the source pages change. `--verify` re-extracts from what is already on disk and
prints the document counts, which is the cheap check that a snapshot is still parseable.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.external_source import (  # noqa: E402
    REGISTRY, SNAPSHOT_DIR, UA, extract_sections,
)

# Generous compared to the 4 s runtime timeout: this is an offline capture step, not the demo
# path, and the site has been measured at up to 7.7 s.
CAPTURE_TIMEOUT_S = 20.0


def capture(entry: dict, language: str) -> tuple[bool, str]:
    url = entry[f"url_{language}"]
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=CAPTURE_TIMEOUT_S)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"

    html = r.text
    sections = extract_sections(html)
    n = len(sections["required_documents"] or [])
    if n == 0:
        return False, "extracted 0 documents — NOT written (a snapshot that parses to nothing "
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{entry['key']}.{language}.html"
    path.write_text(f"<!-- captured_at: {stamp} -->\n<!-- source: {url} -->\n{html}",
                    encoding="utf-8")
    return True, f"{n} documents, fees={'yes' if sections['fees'] else 'no'} -> {path.name}"


def verify(entry: dict, language: str) -> tuple[bool, str]:
    path = SNAPSHOT_DIR / f"{entry['key']}.{language}.html"
    if not path.exists():
        return False, "missing"
    sections = extract_sections(path.read_text(encoding="utf-8", errors="replace"))
    n = len(sections["required_documents"] or [])
    return n > 0, f"{n} documents, fees={'yes' if sections['fees'] else 'no'}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="re-extract from disk, write nothing")
    args = ap.parse_args()

    failures = 0
    for entry in REGISTRY:
        for language in ("ar", "en"):
            ok, detail = (verify if args.verify else capture)(entry, language)
            print(f"[{'ok ' if ok else 'FAIL'}] {entry['key']}.{language}: {detail}")
            failures += 0 if ok else 1
            if not args.verify:
                time.sleep(1.0)  # the site is slow and this is not a race
    print(f"\n{'verified' if args.verify else 'captured'}: "
          f"{len(REGISTRY) * 2 - failures}/{len(REGISTRY) * 2}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
