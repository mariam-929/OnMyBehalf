"""External call #2: live REST search — confirms the service still exists / catches a newer match
(SCOPE §5, N6). Verified 2026-07-25: /wp-json/wp/v2/ministry_service_ser?search=... returns live
matches with modified_gmt.
"""
from __future__ import annotations

import requests

from agents.models import LiveLookupResult

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://dawlati.gov.lb/wp-json/wp/v2/ministry_service_ser"


def live_service_lookup(query: str, snapshot_modified_gmt: str | None = None) -> LiveLookupResult:
    try:
        r = requests.get(BASE, headers={"User-Agent": UA},
                         params={"search": query, "per_page": 3,
                                 "_fields": "id,title,modified_gmt"}, timeout=5)
        r.raise_for_status()
        hits = r.json()
    except Exception:  # noqa: BLE001
        return LiveLookupResult(query=query, exists=False)
    if not hits:
        return LiveLookupResult(query=query, exists=False)
    newest = max(hits, key=lambda h: h.get("modified_gmt") or "")
    is_newer = bool(snapshot_modified_gmt and (newest.get("modified_gmt") or "") > snapshot_modified_gmt)
    return LiveLookupResult(query=query, exists=True, newest_post_id=newest["id"],
                            newest_modified_gmt=newest.get("modified_gmt"), is_newer=is_newer)
