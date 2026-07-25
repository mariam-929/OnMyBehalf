"""External call #1: freshness = source-change detection via REST modified_gmt (SCOPE FR6, A08).

Verified 2026-07-25: GET /wp-json/wp/v2/{type}/{post_id}?_fields=id,modified_gmt returns 200 with
the timestamp. This detects whether the SOURCE changed since our snapshot — NOT substantive
currency. 5 s HTTP timeout in code (not a LangGraph node timeout — those are async-only, F33).

Status is `unchanged | changed | unverified` (A08). `unverified` is not a failure of ours: an
unreachable source is a real state the citizen is told about, with a snapshot-date caveat.

`session` is injectable so the G7/A14 drill can simulate a dead Dawlati **while Groq stays up** —
that drill must not be "turn off the wifi", which would take both down at once.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from agents.models import FreshnessResult

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://dawlati.gov.lb/wp-json/wp/v2"
TIMEOUT_S = 5
LOOKUP_TTL_DAYS = 180   # FR6b: a lookup-table row older than this is treated as unverified


def check_freshness(post_id: int, post_type: str, snapshot_modified_gmt: str,
                    session: requests.Session | None = None) -> FreshnessResult:
    now = datetime.now(timezone.utc).isoformat()
    get = (session or requests).get
    try:
        r = get(f"{BASE}/{post_type}/{post_id}", headers={"User-Agent": UA},
                params={"_fields": "id,modified_gmt"}, timeout=TIMEOUT_S)
        if r.status_code != 200:
            raise requests.HTTPError(r.status_code)
        live = r.json().get("modified_gmt")
    except Exception:  # noqa: BLE001  timeout / 403 / network -> unverified
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt=snapshot_modified_gmt, checked_at=now,
                               note=f"source unreachable; snapshot {snapshot_modified_gmt}; "
                                    "currency not guaranteed")
    if not live:
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt=snapshot_modified_gmt, checked_at=now,
                               note="source returned no modified_gmt; snapshot "
                                    f"{snapshot_modified_gmt}; currency not guaranteed")

    # ANY difference is a change, not just a later timestamp. A source that moves BACKWARDS
    # (restore from backup, reverted edit, or a corrupt snapshot on our side) is exactly the case
    # a reviewer needs to see; `live > snapshot` silently reported those as `unchanged`.
    status = "unchanged" if live == snapshot_modified_gmt else "changed"
    return FreshnessResult(status=status, source_modified_gmt=live,
                           snapshot_modified_gmt=snapshot_modified_gmt, checked_at=now,
                           note=f"{status} since snapshot {snapshot_modified_gmt}; "
                                "change-detection only, substantive currency not guaranteed")


def lookup_row_freshness(verified_on: str | None, now: datetime | None = None) -> FreshnessResult:
    """FR6b: lookup-table rows carry `verified_on`; older than the TTL ⇒ treated as unverified.

    These rows have no live endpoint to poll — they were verified by a human against a source URL.
    Age is the only signal available, so the TTL is the whole check.
    """
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    if not verified_on:
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt="", checked_at=stamp,
                               note="lookup row has no verified_on date")
    try:
        seen = datetime.fromisoformat(verified_on)
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
    except ValueError:
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt=verified_on, checked_at=stamp,
                               note=f"unparseable verified_on {verified_on!r}")
    age = now - seen
    if age > timedelta(days=LOOKUP_TTL_DAYS):
        return FreshnessResult(status="unverified", source_modified_gmt=None,
                               snapshot_modified_gmt=verified_on, checked_at=stamp,
                               note=f"lookup row verified {age.days}d ago, past the "
                                    f"{LOOKUP_TTL_DAYS}d TTL")
    return FreshnessResult(status="unchanged", source_modified_gmt=None,
                           snapshot_modified_gmt=verified_on, checked_at=stamp,
                           note=f"lookup row verified {age.days}d ago, within the "
                                f"{LOOKUP_TTL_DAYS}d TTL")
