"""External call #1: freshness = source-change detection via REST modified_gmt (SCOPE FR6, A08).

Verified 2026-07-25: GET /wp-json/wp/v2/{type}/{post_id}?_fields=id,modified_gmt returns 200 with
the timestamp. This detects whether the SOURCE changed since our snapshot — NOT substantive
currency. 5 s HTTP timeout in code (not a LangGraph node timeout — those are async-only, F33).
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from agents.models import FreshnessResult

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://dawlati.gov.lb/wp-json/wp/v2"


def check_freshness(post_id: int, post_type: str, snapshot_modified_gmt: str) -> FreshnessResult:
    now = datetime.now(timezone.utc).isoformat()
    try:
        r = requests.get(f"{BASE}/{post_type}/{post_id}",
                         headers={"User-Agent": UA},
                         params={"_fields": "id,modified_gmt"}, timeout=5)
        if r.status_code != 200:
            raise requests.HTTPError(r.status_code)
        live = r.json().get("modified_gmt")
    except Exception:  # noqa: BLE001  timeout / 403 / network -> unverified
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt=snapshot_modified_gmt, checked_at=now,
                               note=f"source unreachable; snapshot {snapshot_modified_gmt}; "
                                    "currency not guaranteed")
    status = "changed" if (live and live > snapshot_modified_gmt) else "unchanged"
    return FreshnessResult(status=status, source_modified_gmt=live,
                           snapshot_modified_gmt=snapshot_modified_gmt, checked_at=now,
                           note=f"{status} since snapshot {snapshot_modified_gmt}; "
                                "change-detection only, substantive currency not guaranteed")
