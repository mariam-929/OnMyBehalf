# contacts_coverage.md — G1b contact catalogue (2026-07-25, owner Ali)

Required artifact for **G1b** (SCOPE §6 / A27, VERIFICATION §G1b). Produced by
`tools/crawler/fetch_directory.py` → `data/contacts.json` (gitignored, regenerated).

## Correction to the plan: no Playwright needed

The stub recorded the directory as client-rendered and required Playwright. It is not. Both
datasets are embedded in the page HTML and plain `requests` retrieves them — the same lesson as
the services probe: check the transport before assuming a render.

| Source | What | Where |
|---|---|---|
| `var directoryEntityData` | ministries 26 · public-institutions 46 · municipalities 39 · governorates **0** | JS object literal in the page |
| `article.directory-number-card` | 15 national hotlines, title + `tel:` | "Useful Numbers" tab markup |

Both the EN (`/en/directory/`) and AR (`/دليل/`) pages carry the blob, which is how each record
gets an Arabic name plus an English alias. The bilingual join is on `official_domain` (minus
`www.`), **not** on `key`: Polylang gives the translations different post ids (Ministry of
Agriculture is 9773 EN / 9784 AR). One entity failed the domain join.

## Result

**126 ContactRecords, all Pydantic-valid** (111 `ministires_directory` + 15 `useful-numbers-post`).

| Field | Filled | Note |
|---|---|---|
| `address` | 23 / 126 | ministries only — 21 of them joined to a taxonomy slug |
| `phones` | 15 / 126 | **only the national hotlines** |
| `authority_term` | 21 / 126 | joins a contact to a service's `ministry_term` |

## ⚠️ MEASURED LIMITATION: the directory publishes no per-authority phone numbers

There is no ministry switchboard, no directorate line, no department extension anywhere in the
directory. The only phones on the site are 15 national hotlines (Civil Defence 125, Consumer
Protection 1739, Ogero 1515, Internal Security 1717, Red Cross 140 …), which belong to no
specific service. Ministries have addresses but no numbers.

`ContactRecord.phones` is therefore empty for every ministry. This is the source's limitation,
not the crawl's, and it lands exactly where SCOPE §15 anticipated: *"contacts thin (verified
risk) → answer still valid without contacts; enrichment is best-effort."* Do not describe the
agent as returning phone numbers for a service.

## Gate check (VERIFICATION §G1b)

The gate reads "≥1 ContactRecord per ≥60% of distinct authorities referenced by **the 40 core
services**". The core-40 does not exist yet, and its seed list was invalidated by the ajax probe
(passport/driving-licence are absent from Dawlati). Two substitute denominators, both reported
rather than picking the flattering one:

| Denominator | Covered | % |
|---|---|---|
| Authorities referenced by the 193 corpus records (agriculture, culture, interior) | **3 / 3** | **100%** |
| All ministry taxonomy terms (22) | **21 / 22** | **95%** |

Both clear ≥60%. **Auto part: PASS.** The 3-authority denominator is small because only 3
ministries publish services — re-run this check once the core-40 is rebuilt.

`governorates` is empty (0 entries) and `public-institutions` / `municipalities` carry only a
title and an official URL — no address, no phone. Useful for authority-name normalisation, not
for citizen contact detail.

## Human check outstanding (reviewer ≠ producer; Ghina per the owners table)

Open https://dawlati.gov.lb/en/directory/ and confirm 3 records against the live page:

| Authority (AR) | Address in our record | Taxonomy join |
|---|---|---|
| وزارة الزراعة | برج البراجنة، بئر حسن، بيروت، لبنان | `agriculture` |
| وزارة السياحة | الحمرا، مقابل مصرف لبنان ،بيروت ،لبنان | `tourism` |
| وزارة الاتصالات | شارع رياض الصلح، بيروت، لبنان | `telecommunications` |

Also confirm the phone finding by spot-checking any ministry card for a number — expected: none.

**VPN must be OFF** (see PROGRESS Findings).

---

## Update 2026-07-25 — two enhancements after Mariam's G1b review

Mariam's live review found two things the first crawl missed; both are now captured (data already
in hand — no new source, no scraping of ministry sites).

1. **`opening_hours`** added to `ContactRecord` + `ContactOut`. It is a field in the same
   `directoryEntityData` blob we already parse — **23 ministries now carry opening hours**
   (e.g. وزارة الزراعة "8AM-2PM"). Recovers the "opening times" item from the original vision.
2. **Ministry hotlines joined from the Useful Numbers tab.** The popups still have no phone, but
   the Useful Numbers tab lists ministry-specific hotlines; these are now matched onto the ministry
   record by the distinctive name part (conservative substring, min len 4, no false matches).
   **6 ministries gained a hotline:** الاتصالات 1775, البيئة 1789, التربية 1747, الشؤون الاجتماعية
   1714, الصحة العامة 1214, العمل 1740. Interior-Complaints (1744) deliberately did NOT join Interior
   — it is a *complaints* line, not a switchboard, so it stays a standalone Useful-Numbers record.
   `phones` filled: 15 → **21/126**. When surfaced in an answer, label these as the national
   Useful-Numbers hotline, not a service switchboard.

Note the source conflict Mariam spotted: Agriculture's own site advertises 1789 as its hotline,
which Dawlati's Useful Numbers assigns to Environment — a real example for the HITL/review-queue story.
