# ajax_probe.md — admin-ajax probe result (2026-07-25, owner Ali, 1 h timebox)

**Decision: crawl the directory admin-ajax endpoint. Do NOT crawl the 219 service pages.**

## What the probe was for

TECH_PLAN §1.4 sequenced `enumerate → admin-ajax probe (1 h) → 10-page spike → full crawl`, with
the crawl assumed to be a Playwright render of each service page (detail pages were recorded as
JS-rendered on 2026-07-24). The probe had to establish whether a JSON route existed before that
work started.

## What was found

**1. The service pages are empty — there is nothing to render.**

| Check | Result |
|---|---|
| REST `content.rendered` on a `ministry_service_ser` post | **0 chars** (`acf: []`) |
| REST content census across **all 249** posts | **0 / 249** have body text > 50 chars |
| Rendered page (Playwright, networkidle) body text | 431 chars — nav, date, title, share, footer |
| Section keywords (المستندات / الرسوم / الجهة …) in rendered DOM | **absent, all of them** |
| XHR fetching content during render | none (only Cloudflare, GA, accessibility widget) |

A per-page crawl of the 219 service pages would have produced 219 empty records. The 10-page
spike would have scored ~0% recall and triggered the 40-core manual fallback — a wasted day.

**2. All 26 post types were checked** (the plan froze 3 without verifying no others existed).
Only `post` (2 news articles) carries content. Four service-ish types the plan never enumerated
exist but are empty: `governorates` 0, `public_institution_s` 0, `governorate_services` 0,
`municipality_service` 0. Also present and empty: `ministires` 52, `public_institutions` 92,
`municipalities` 78.

**3. The content lives in a directory admin-ajax endpoint.** The services guide
(`/دليل-الخدمات/`, nav "معلومات الخدمات") loads each ministry's services over admin-ajax:

```
POST https://dawlati.gov.lb/wp-admin/admin-ajax.php
  action=omsar_load_directory_ministry_services
  nonce=<from `var ajaxConfig` on the guide page>
  ministry=<taxonomy slug>
  directory_type=ministry-services
  post_type=ministry_service_ser
  taxonomy=ministry_services_min
  relationship_field=ministry
```

Returns `{"success":true,"data":{"services":[…]}}` with per-service fields:
`code, title, directorate, sub_directorate, department, unit, description_html,`
**`required_documents_html`**, **`fees_html`**, `notes_html`, `doc_title`, `doc_url`.

The nonce sits in `var ajaxConfig = { url: …, nonce: "…" }` and was **identical from a fresh
`requests` session and from the browser** — it is not per-user, so plain `requests` works and
Playwright is not needed for this endpoint.

## Coverage (harvested from all 22 ministry terms, 2026-07-25)

| Field | Filled | % |
|---|---|---|
| `required_documents_html` | **181 / 195** | **92.8%** |
| `fees_html` | 136 / 195 | 69.7% |
| `notes_html` | 111 / 195 | 56.9% |
| docs **and** fees | 134 / 195 | 68.7% |
| any field at all | 185 / 195 | 94.9% |
| `description_html` | 0 / 195 | **0.0% — always empty, dead field** |

195 services, 195 unique titles — exactly the frozen `ministry_service_ser` denominator, so the
directory *is* the catalog, reached a different way.

**Only 3 of 22 ministries are populated:** agriculture 115, interior 53, culture 27. The other 19
return 0. This is the site's own stated position, shown on the guide page:
> «نعمل تدريجياً على إضافة النماذج الرسمية والوثائق المطلوبة» — *"we are gradually adding the
> official forms and required documents"*.

Coverage is a property of Dawlati, not of our crawl. Report it as such.

## Consequence for the core-40 and the eval gold (ACTION REQUIRED)

`data/curated_core.seed.json` lists candidates — passport issue/renewal, national ID, driving
licence, vehicle registration, work permit, residence permit, NSSF, building permit. Checked
against the directory:

| Planned core service | In the directory? |
|---|---|
| passport issue / renewal | **NO** — the only "جواز سفر" match is `إصدار جواز سفر للخيل` (a horse passport, agriculture) |
| driving licence | **NO** — 0 matches |
| national ID | YES — `بطاقة هوية` |
| individual / family civil extract | YES — `بيان قيد عائلي وإفرادي` |
| birth / marriage / death / divorce registration | YES — `تسجيل ولادة / زواج / وفاة / طلاق` |

`tests/gold_claims.seed.json` case `normal_passport_en` ("How do I renew my Lebanese passport?")
has **no answerable service**, and the same query is one of the G0 bakeoff fixtures and the
SCOPE §9 demo script. The core-40, the gold cases and the demo queries must be rebuilt from the
195 that exist — realistically a civil-registry (interior) + agriculture set.

## Open issue for FR6 (freshness)

The ajax payload carries **no `post_id` and no `modified_gmt`**. `check_freshness(post_id)` needs
both. The directory services must be joined to `data/catalog.json` on normalised title to recover
`post_id`; unmatched services get `unverified`. Needs deciding at G2/G7.

## Cost change

22 POSTs, ~30 seconds, no browser — replacing a 219-page Playwright crawl at concurrency 3 with a
1 s delay. `tools/crawler/fetch_render.py` and the HTML `extract.py` are no longer needed for
services; `fetch_directory.py` becomes the main ingester.

## Reproduce

Probe scripts (throwaway, not committed): `probe1`–`probe12` in the session scratchpad.
The decisive ones are `probe5_content_census.py` (0/249 have content) and
`probe12_full_harvest.py` (fill rates above).
