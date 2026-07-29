"""Coarse trip ordering over document-issuing offices — PROTOTYPE (demo path only).

WHAT THIS IS NOT: geocoding. There are no coordinates anywhere in this project and none are used
here. Ordering is over hand-declared coarse REGIONS with a hand-declared adjacency graph, which is
enough to answer "which of these two do I visit first" without pretending to compute travel time.

WHAT IT REFUSES TO DO: invent a location. Every office locality carries a `locality_source`, and
anything not sourced or explicitly declared comes back as `unknown` and is reported as unknown
rather than guessed. An invented office address in a citizen-facing itinerary is exactly the class
of fabrication the rest of this system is built to make impossible.

THE ONE CASE THAT NEEDS NO DATA: أقلام النفوس (civil registry offices) are per-locality — a citizen
uses the registry where their family is registered, not a fixed address. So the correct instruction
is "your own local registry", which is both more accurate and cheaper than any lookup. Those
offices are declared `kind: "citizen_local"` and are placed in the citizen's own region.

Coverage is deliberately partial: `data/office_locality.seed.json` covers the offices the demo
services touch. The corpus has 67 distinct authority strings; filling them is human work.
"""
from __future__ import annotations

import json
import re
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Any

from tools.text_norm import normalize_ar

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "office_locality.seed.json"

# Coarse regions and a hand-declared adjacency graph. This is a travel-ORDERING aid, not a map:
# "adjacent" means a Lebanese resident would consider them one manageable hop, which is a judgement
# recorded here explicitly so a reviewer can disagree with a specific edge.
REGION_ADJACENCY: dict[str, set[str]] = {
    "beirut": {"mount_lebanon_south", "mount_lebanon_north"},
    "mount_lebanon_south": {"beirut", "mount_lebanon_north", "south", "bekaa"},
    "mount_lebanon_north": {"beirut", "mount_lebanon_south", "north", "bekaa"},
    "north": {"mount_lebanon_north", "bekaa"},
    "south": {"mount_lebanon_south", "nabatieh"},
    "nabatieh": {"south", "bekaa"},
    "bekaa": {"mount_lebanon_south", "mount_lebanon_north", "north", "nabatieh"},
}

# Cities a citizen may pick, mapped to a region. Arabic and Latin spellings both accepted because
# the UI is bilingual and users type either.
CITY_REGION: dict[str, str] = {
    "بيروت": "beirut", "beirut": "beirut",
    "عرمون": "mount_lebanon_south", "aaramoun": "mount_lebanon_south",
    "بعبدا": "mount_lebanon_south", "baabda": "mount_lebanon_south",
    "عاليه": "mount_lebanon_south", "aley": "mount_lebanon_south",
    "الشوف": "mount_lebanon_south", "chouf": "mount_lebanon_south",
    "المتن": "mount_lebanon_north", "metn": "mount_lebanon_north",
    "جونية": "mount_lebanon_north", "jounieh": "mount_lebanon_north",
    "كسروان": "mount_lebanon_north", "kesrouan": "mount_lebanon_north",
    "جبيل": "mount_lebanon_north", "jbeil": "mount_lebanon_north",
    "طرابلس": "north", "tripoli": "north",
    "الكورة": "north", "koura": "north",
    "صيدا": "south", "sidon": "south",
    "صور": "south", "tyre": "south",
    "النبطية": "nabatieh", "nabatieh": "nabatieh",
    "زحلة": "bekaa", "zahle": "bekaa",
    "بعلبك": "bekaa", "baalbek": "bekaa",
}

REGION_LABEL = {
    "beirut": "Beirut", "mount_lebanon_south": "Mount Lebanon (south of Beirut)",
    "mount_lebanon_north": "Mount Lebanon (north of Beirut)", "north": "North Lebanon",
    "south": "South Lebanon", "nabatieh": "Nabatieh", "bekaa": "Bekaa",
}

_TIME_RANGE = re.compile(r"^\s*\d{1,2}\s*(?:AM|PM)?\s*[-–]\s*\d{1,2}\s*(?:AM|PM)?\s*$", re.I)


def repair_swapped_contact_fields(row: dict) -> dict:
    """Undo the address/opening_hours transposition seen in the G1b crawl.

    `وزارة الداخلية والبلديات` was stored with address='8AM-2PM' and
    opening_hours='الحمرا، بيروت، لبنان'. Only some records are affected, so detect rather than
    swap blindly: an address that is only a time range, paired with hours that are not.
    Fixed here (read side) so the shipped data works, and separately in the crawler.
    """
    addr, hours = row.get("address"), row.get("opening_hours")
    if addr and _TIME_RANGE.match(str(addr)) and hours and not _TIME_RANGE.match(str(hours)):
        return {**row, "address": hours, "opening_hours": addr}
    return row


def region_distance(a: str, b: str) -> int:
    """Hops between regions on the adjacency graph. Same region = 0. Unknown region sorts last."""
    if a == b:
        return 0
    if a not in REGION_ADJACENCY or b not in REGION_ADJACENCY:
        return 99
    seen, q = {a}, deque([(a, 0)])
    while q:
        node, d = q.popleft()
        for nxt in REGION_ADJACENCY.get(node, ()):
            if nxt == b:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return 99


def city_to_region(city: str | None) -> str | None:
    if not city:
        return None
    key = str(city).strip().lower()
    return CITY_REGION.get(key) or CITY_REGION.get(normalize_ar(str(city)).strip())


@lru_cache(maxsize=1)
def _table() -> dict[str, dict]:
    if not SEED.exists():
        return {}
    raw = json.loads(SEED.read_text(encoding="utf-8"))
    return {normalize_ar(k): v for k, v in (raw.get("offices") or {}).items()}


def lookup_office(office: str | None) -> dict:
    """Declared locality for an office, or an explicit unknown. Never a guess."""
    if not office:
        return {"kind": "unknown", "locality": None, "region": None, "locality_source": None}
    hit = _table().get(normalize_ar(office))
    if not hit:
        return {"kind": "unknown", "locality": None, "region": None, "locality_source": None}
    return {"kind": hit.get("kind", "fixed"), "locality": hit.get("locality"),
            "region": hit.get("region"), "locality_source": hit.get("locality_source"),
            "note": hit.get("note")}


def plan_itinerary(offices: list[str], origin_city: str | None) -> dict[str, Any]:
    """Group offices into trips and order them by coarse distance from the citizen's city.

    Returns trips plus an explicit `unknown` bucket. One trip == one region: every office in the
    same region is one journey, which is the "fewest trips" question actually answerable without a
    map. `citizen_local` offices are placed in the citizen's own region because that is where they
    are, by definition.
    """
    origin = city_to_region(origin_city)
    groups: dict[str, list[dict]] = {}
    unknown: list[dict] = []

    for office in dict.fromkeys(o for o in offices if o):   # de-dupe, keep order
        info = lookup_office(office)
        entry = {"office": office, **info}
        if info["kind"] == "citizen_local":
            region = origin or "citizen_local"
            entry["locality"] = "your own local registry office"
            groups.setdefault(region, []).append(entry)
        elif info["region"]:
            groups.setdefault(info["region"], []).append(entry)
        else:
            unknown.append(entry)

    def sort_key(region: str) -> tuple[int, str]:
        if origin is None:
            return (0 if region == "citizen_local" else 1, region)
        return (region_distance(origin, region), region)

    trips = []
    for i, region in enumerate(sorted(groups, key=sort_key), 1):
        stops = groups[region]
        trips.append({
            "order": i,
            "region": region,
            "region_label": REGION_LABEL.get(region, "Your own locality"),
            "hops_from_origin": None if origin is None else region_distance(origin, region),
            "stops": stops,
            "n_stops": len(stops),
        })

    return {
        "origin_city": origin_city, "origin_region": origin,
        "trips": trips, "n_trips": len(trips),
        "unknown_offices": unknown,
        "ordered": origin is not None,
        # Opening hours are NOT used: every contact record in the source publishes the identical
        # "8AM-2PM", so there is nothing to schedule around. Stated rather than silently skipped.
        "hours_considered": False,
    }
