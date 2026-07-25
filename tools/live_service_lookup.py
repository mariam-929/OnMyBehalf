"""External call #2: live REST search — confirms the retrieved service still exists and catches a
newer version of IT (SCOPE §5, N6). Verified 2026-07-25:
/wp-json/wp/v2/ministry_service_ser?search=... returns live matches with modified_gmt.

The contract (SCHEMA_AND_CONTRACTS, LiveLookupResult) is explicitly about **the chosen service**:
`exists` = our retrieved service is still live, `is_newer` = its live modified_gmt is ahead of our
snapshot. Consumers turn either signal into `needs_human_review`.

FIXED 2026-07-25 (Ali): the first implementation ignored the chosen service entirely — it took
`max(modified_gmt)` across the top-3 search hits, so `live_service_lookup("بطاقة هوية")` reported
`is_newer=True` from post 11633, `إصدار بطاقة تعريف للخيل` (a horse ID card) that merely happened
to be edited later. Since `is_newer` sets `newer_version_available` + `needs_human_review` (N6),
that would have filled the review queue with false flags — exactly what G7 exists to prevent.
`post_id` is now the anchor for both signals.

`session` is injectable for the G7/A14 outage drill (dead Dawlati, Groq still up).
"""
from __future__ import annotations

import requests

from agents.models import LiveLookupResult

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://dawlati.gov.lb/wp-json/wp/v2/ministry_service_ser"
TIMEOUT_S = 5
PER_PAGE = 10   # deep enough that the searched service appears among its own title's matches


def live_service_lookup(query: str, post_id: int | None = None,
                        snapshot_modified_gmt: str | None = None,
                        session: requests.Session | None = None) -> LiveLookupResult:
    """Live-search Dawlati for `query` and report on the service we actually retrieved.

    `post_id` is the service the agent is about to answer with. Without it the call degrades to
    "did the search match anything at all", which is weaker and must not drive a review flag.
    """
    get = (session or requests).get
    try:
        r = get(BASE, headers={"User-Agent": UA},
                params={"search": query, "per_page": PER_PAGE,
                        "_fields": "id,title,modified_gmt"}, timeout=TIMEOUT_S)
        r.raise_for_status()
        hits = r.json()
    except Exception:  # noqa: BLE001  unreachable -> report as "cannot confirm", never as removed
        return LiveLookupResult(query=query, exists=False)

    if not hits:
        return LiveLookupResult(query=query, exists=False)

    newest = max(hits, key=lambda h: h.get("modified_gmt") or "")
    newest_id = newest.get("id")
    newest_gmt = newest.get("modified_gmt")

    if post_id is None:
        # Degraded mode: no anchor, so `exists` only means the search matched something and
        # `is_newer` stays False — an unanchored comparison is what produced the horse-ID bug.
        return LiveLookupResult(query=query, exists=True, newest_post_id=newest_id,
                                newest_modified_gmt=newest_gmt, is_newer=False)

    mine = next((h for h in hits if h.get("id") == post_id), None)
    if mine is None:
        # Our service did not come back among the live matches for its own title. Report
        # exists=False (N6: the consumer flags this for review) while still surfacing the newest
        # match, which may be the replacement service.
        return LiveLookupResult(query=query, exists=False, newest_post_id=newest_id,
                                newest_modified_gmt=newest_gmt, is_newer=False)

    mine_gmt = mine.get("modified_gmt")
    is_newer = bool(snapshot_modified_gmt and mine_gmt and mine_gmt != snapshot_modified_gmt)
    return LiveLookupResult(query=query, exists=True, newest_post_id=newest_id,
                            newest_modified_gmt=newest_gmt, is_newer=is_newer)
