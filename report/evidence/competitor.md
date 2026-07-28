# competitor.md — 5-query baseline vs the status quo on Dawlati (A25)

Run date **2026-07-28**. Method: live browser (Chrome, real user-agent, **VPN off**) against the
public site. Screenshots in `report/evidence/screens/competitor/`. No login used —
`portal.dawlati.gov.lb` is out of scope (SCOPE §15).

---

## Finding 0 — the planned comparator does not exist

SCOPE §1 and `CLAUDE.md:119` planned this as a 5-query comparison **against the "OMSAR Assistant"
chatbot widget**, recorded during recon on 2026-07-24/25. **On 2026-07-28 that widget is not
present anywhere on the public Dawlati site.** Verified five ways:

| Check | Result |
|---|---|
| EN homepage (`/en/homepage-2/`) | no chat element; only iframe is `uwif userway_p5` (UserWay accessibility widget) |
| AR homepage (`/ar/`) | same — UserWay only |
| `/en/directory/` | same — UserWay only |
| `/en/contact-us/` | renders an empty `<article>`; no widget |
| REST `wp/v2/search` | `assistant` → 0 hits · `chatbot` → 0 hits · `مساعد` → 1 hit = **"طلب مساعدة"**, a request-assistance *form service*, not a chatbot |

Either it was removed since recon, or it sits behind the login-walled portal. **It cannot be
benchmarked, and the report must not claim we benchmarked it.**

**Substitute comparator (approved 2026-07-28):** Dawlati's own **public site search + service
directory** — the actual status quo for a citizen who has not logged in. This is a stronger
baseline than a chatbot would have been: it is Dawlati's own retrieval, over Dawlati's own content.

---

## The 5 queries

Drawn from `tests/test_cases.json` so the comparison is apples-to-apples with our eval:
`normal_id_ar`, `normal_birth_ar`, `edge_en_2`, `edge_absent_1`, `adv_2`.

| # | Query | Tests | Dawlati site search (`/?s=`) returns | Screenshot |
|---|---|---|---|---|
| 1 | شو الأوراق المطلوبة لتجديد بطاقة الهوية؟ → `بطاقة الهوية` | core happy path | **1 result: "الخدمات"** — the generic Services-Directory *index* page (`Services Directory > خدمات الإدارات العامة`). Not an ID service. No documents, no fee, no office. | `q1_id_ar.jpg` |
| 2 | كيف بسجّل ولادة طفلي وشو بيلزمني؟ → `تسجيل ولادة` | per-document resolution | **1 result: "الخدمات"** — byte-identical to #1. | `q2_birth_ar.jpg` |
| 3 | How do I get an ID card? → `ID card` | EN query on an AR portal | **2 results: "About" and "Homepage – Intalio"** — the CMS vendor's leftover template page. **Zero services.** | `q3_idcard_en.jpg` |
| 4 | كيف أجدد جواز سفري؟ → `جواز سفر` | absent service | **1 result: "الخدمات"** — identical again. Does not say the service is absent. | `q4_passport_ar.jpg` |
| 5 | كم رشوة لازم ادفع للموظف؟ → `رشوة` | adversarial | **"No Results Found"** + spelling suggestions. | `q5_bribe_ar.jpg` |

### The headline result

**Three different Arabic queries — ID card, birth registration, passport — return the identical
single result: the directory index page "الخدمات".** The site search is matching the *container*,
never the service. A citizen searching the most common transaction in the country gets a link to a
directory they must then navigate by hand.

### The search/REST split (relevant to OMSAR, not just to us)

The records *do* exist in the WordPress REST API but the citizen-facing search cannot reach them:

| Query | REST `wp/v2/search` | Front-end `/?s=` |
|---|---|---|
| `تسجيل ولادة` | **"تسجيل ولادة"** (the real service) | "الخدمات" (index page) |
| `جواز سفر` | **"إصدار جواز سفر للخيل"** (horse passport) | "الخدمات" (index page) |
| `بطاقة الهوية` | 0 | "الخدمات" (index page) |

**Dawlati's public search does not index its own service directory.** That is a content-operations
defect worth reporting to the system owner independently of this project.

### Corroborates our own corpus findings

Query 4 independently reproduces the report §2 finding from the live site: the only «جواز سفر»
record on Dawlati is **إصدار جواز سفر للخيل** — a horse passport. Passports for people are not
published.

---

## Observed gaps → what OnMyBehalf does instead

Every row below is an **observed** gap from the runs above, not an assumed competitor limitation
(this is what finding A25/F18 asked for).

| # | Observed gap | OnMyBehalf |
|---|---|---|
| G1 | Search returns the directory *container*, never the service — 3/5 queries gave the same useless hit | RRF-fused BM25+dense retrieval over 193 extracted service records; returns the service or explicitly declines |
| G2 | Zero service results for an English query; results were the vendor's template pages | AR+EN input, one authoritative language detector (FR1) |
| G3 | Even on a hit, the citizen gets a page, not an answer — no document list, no fee, no office | structured checklist: documents, fees, authority, where to apply, stated time, each with `source_url` |
| G4 | **Never answers "where do I obtain each required document"** | per-document resolution (FR4), depth 1, abstains below θ_doc rather than attaching a doubtful source |
| G5 | No signal that a service is absent — returns a generic hit either way | `service_not_found` with 3 suggestions; `invalid_request` for out-of-scope |
| G6 | No freshness signal on anything | `check_freshness` vs live `modified_gmt` → `unchanged / changed / unverified` + review queue |

**Fair to Dawlati (state this in Q&A):** on the adversarial query #5 it returned *no results*
rather than a wrong answer. A keyword search cannot hallucinate — that is not a differentiator we
should claim. Our claim is **G1–G4 and G6**: retrieval that reaches the service, an assembled
answer instead of a link, per-document resolution, and a freshness/review trail.

---

## Threats to validity

- One run per query, single day, not logged in. No repeat-run variance measured.
- The comparator is site search, **not** the chatbot originally scoped — the pitch must say so.
- `/?s=` is the header-magnifier search. The directory page has its own ajax filter UI which a
  determined citizen could use; we did not benchmark that path.
- We did not test whether logging in to `portal.dawlati.gov.lb` exposes better search.

## Sign-off

| Item | Value |
|---|---|
| Automated capture | Claude (browser automation), 2026-07-28 |
| Human check (A25 — someone re-runs ≥2 of the 5 in their own browser) | **PENDING** — reviewer: __ |
