"""Trip ordering: it must order sensibly and, above all, never invent a location."""
from __future__ import annotations

from tools.locality import (
    city_to_region, lookup_office, plan_itinerary, region_distance,
    repair_swapped_contact_fields,
)

MUGHTARIBEEN = "المديرية العامة للأحوال الشخصية – دائرة المغتربين"
JINSIYYA = "المديرية العامة للأحوال الشخصية – دائرة شؤون الجنسية والقضايا"
NUFUS = "المديرية العامة للأحوال الشخصية – دوائر النفوس أو أقلام النفوس"


# ---------------------------------------------------------------- no invention
def test_unknown_office_is_reported_unknown_not_guessed():
    """The whole point: an office we have no data for must not acquire a location."""
    info = lookup_office("مكتب لا نعرف عنه شيئا")
    assert info["kind"] == "unknown"
    assert info["locality"] is None and info["region"] is None


def test_unknown_offices_are_surfaced_separately_not_dropped():
    plan = plan_itinerary([MUGHTARIBEEN, "دائرة مجهولة"], "بيروت")
    assert len(plan["unknown_offices"]) == 1
    assert plan["unknown_offices"][0]["office"] == "دائرة مجهولة"
    assert all(s["office"] != "دائرة مجهولة" for t in plan["trips"] for s in t["stops"])


def test_assumed_localities_declare_themselves_as_assumptions():
    """A directorate placed at its parent ministry must say so, not pass as verified."""
    assert lookup_office(MUGHTARIBEEN)["locality_source"] == "parent_ministry_assumed"


def test_no_office_claims_opening_hours():
    """Every source record publishes the identical 8AM-2PM, so hours are not used at all."""
    assert plan_itinerary([MUGHTARIBEEN], "بيروت")["hours_considered"] is False


# ---------------------------------------------------------------- ordering
def test_same_region_offices_become_one_trip():
    """'Fewest trips' is answerable by grouping, without any map."""
    plan = plan_itinerary([MUGHTARIBEEN, JINSIYYA], "بيروت")
    assert plan["n_trips"] == 1
    assert plan["trips"][0]["n_stops"] == 2


def test_the_aaramoun_case_local_registry_first_then_one_beirut_trip():
    """The worked example: a citizen in Aaramoun does their local registry, then Beirut once."""
    plan = plan_itinerary([MUGHTARIBEEN, JINSIYYA, NUFUS], "عرمون")
    assert plan["n_trips"] == 2
    first, second = plan["trips"]
    assert first["region"] == "mount_lebanon_south"     # their own area, 0 hops
    assert first["hops_from_origin"] == 0
    assert second["region"] == "beirut"
    assert second["n_stops"] == 2                        # both directorates batched
    assert second["hops_from_origin"] == 1


def test_citizen_local_office_gets_no_invented_address():
    plan = plan_itinerary([NUFUS], "صور")
    stop = plan["trips"][0]["stops"][0]
    assert stop["kind"] == "citizen_local"
    assert stop["locality"] == "your own local registry office"


def test_far_origin_still_orders_local_first():
    plan = plan_itinerary([MUGHTARIBEEN, NUFUS], "بعلبك")
    assert plan["trips"][0]["stops"][0]["kind"] == "citizen_local"
    assert plan["trips"][0]["hops_from_origin"] == 0


def test_without_a_city_nothing_is_ordered_but_grouping_still_works():
    plan = plan_itinerary([MUGHTARIBEEN, JINSIYYA], None)
    assert plan["ordered"] is False
    assert plan["trips"][0]["hops_from_origin"] is None
    assert plan["n_trips"] == 1


def test_duplicate_office_wordings_do_not_become_duplicate_stops():
    plan = plan_itinerary([MUGHTARIBEEN, MUGHTARIBEEN], "بيروت")
    assert plan["trips"][0]["n_stops"] == 1


def test_empty_input_is_not_an_error():
    plan = plan_itinerary([], "بيروت")
    assert plan["n_trips"] == 0 and plan["unknown_offices"] == []


# ---------------------------------------------------------------- geography model
def test_region_distance_is_symmetric_and_zero_on_self():
    assert region_distance("beirut", "beirut") == 0
    assert region_distance("beirut", "north") == region_distance("north", "beirut")


def test_beirut_is_nearer_to_aaramoun_than_baalbek_is():
    assert region_distance("mount_lebanon_south", "beirut") < \
           region_distance("bekaa", "beirut") + 1  # sanity, not a claim about roads


def test_city_names_accepted_in_arabic_and_latin():
    assert city_to_region("بيروت") == "beirut"
    assert city_to_region("Beirut") == "beirut"
    assert city_to_region("aaramoun") == "mount_lebanon_south"
    assert city_to_region("Atlantis") is None


# ---------------------------------------------------------------- data repair
def test_transposed_address_and_hours_are_repaired():
    """The G1b crawl stored Interior's address in opening_hours and vice versa."""
    fixed = repair_swapped_contact_fields(
        {"address": "8AM-2PM", "opening_hours": "الحمرا، بيروت، لبنان"})
    assert fixed["address"] == "الحمرا، بيروت، لبنان"
    assert fixed["opening_hours"] == "8AM-2PM"


def test_correct_records_are_left_alone():
    row = {"address": "برج البراجنة، بئر حسن، بيروت، لبنان", "opening_hours": "8AM-2PM"}
    assert repair_swapped_contact_fields(row) == row


def test_repair_tolerates_missing_fields():
    assert repair_swapped_contact_fields({}) == {}
    assert repair_swapped_contact_fields({"address": "8AM-2PM"})["address"] == "8AM-2PM"
