# PROGRESS.md — Living status log (update EVERY session, before ending work)

> **Protocol for every Claude session:** (1) Read this file first, then act per "Where we are".
> (2) While working: tick checkboxes, note surprises under Findings, record unplanned choices in
> Decisions, capture report/demo artifacts into the Evidence register. (3) Before the session
> ends: update "Where we are", the gate record, and add a dated Session-log entry. Handoff note,
> not a diary.
> Context: `../CLAUDE.md` → `SCOPE.md` (v3) → `SCHEMA_AND_CONTRACTS.md` → `TECH_PLAN.md` (v3) →
> `VERIFICATION.md` (v3) → `RESOLUTIONS.md` (why v3). This file tracks WHERE WE ARE against those.

## Where we are (keep current)

**Status 2026-07-25 (after SECOND review + v3):** Docs at **v3**. Second reviewer (A01–A30)
verified against primary sources + live Dawlati API; ~26 accepted, 4 partial, folded in
(RESOLUTIONS round 2). New concrete artifacts created: `SCHEMA_AND_CONTRACTS.md`, `prompts/*_v1.md`
(all 3 drafted), `tests/gold_claims.seed.json`. Key changes: per-model adapters (A01 — Groq
structured-output support differs by model); **`get_contacts` replaced by `live_service_lookup`**
after live test proved contacts aren't in REST (A06/A27); bounded research loop (A02); freshness
relabeled unchanged/changed/unverified (A08); gold oracle separated from verification sheet (A03).
**Third review (N1–N6) verdict = START CODING** (0 architectural blockers; prior fixes verified
real). N1–N6 folded (LiveLookupResult + newer_version_available reason; composer few-shot fixed to
never invent durations; IntentResult/ResearchPlan added to schema; per-doc freshness made a
deterministic system step; PROGRESS stale refs fixed). Owners assigned (table below); Groq key
created.

**Update 2026-07-25 (later — build has started):** Repo scaffolded and public. **G0 AUTO PASS**
(gpt-oss-120b; pending Maria's Arabic sign-off). **G1 AUTO PASS** — `data/catalog.json` enumerated,
195+24+30 = **249 exact**, denominators captured to `report/evidence/coverage.md` (pending Mariam's
5-URL check). Second dev env (Ali) up on Python 3.13. Known gotcha: **Dawlati Cloudflare 403s VPN
IPs** — see Findings. **Next action: DATA track — admin-ajax probe (1 h box) → 10-page spike +
`data/spike_gold.json` → field-recall scoring → G2**; BUILD track (graph skeleton on synthetic
fixtures) can start in parallel. Deadline Wed 2026-07-29 (written).

## Gate record (AUTHORITATIVE — defs in `VERIFICATION.md` v3; no step starts before upstream gates
## PASS; Claude runs auto checks but may NOT fill "Human sign-off")

| Gate | What | Status | Date | Evidence | Human sign-off |
|---|---|---|---|---|---|
| G0 | Env + **per-model bakeoff** + synthetic fixtures (blocks all code) | AUTO PASS ×2 | 2026-07-25 | **reproduced independently by Ali**: gpt-oss 10/10@0.523s vs qwen 10/10@1.172s (Mariam: 10/10@0.55s vs 9/10@1.38s). Winner unchanged. report/evidence/bakeoff.md; data/model_limits.json (8K TPM both) | **PENDING: Maria** confirms Arabic (Mariam read them 2026-07-25, but she RAN the bakeoff — producer ≠ reviewer, so it does not close the gate) |
| G1 | Service catalog (249 posts) | ✅ PASS | 2026-07-25 | data/catalog.json — 249 (195/24/30), 0 dup ids, all modified_gmt; `check_g1.py` 7/7; report/evidence/coverage.md | **Mariam 2026-07-25** (5 URLs load, titles match) |
| G1b | Contact catalog (/en/directory crawl) | ✅ PASS | 2026-07-25 | 126 ContactRecords, all valid; coverage 100%/95%; contacts_coverage.md | **Mariam 2026-07-25** (verified live: ministries have location+site+hours+portals, no phone; 15 hotlines in Useful Numbers tab). 2 enhancement findings logged |
| G2 | Corpus quality (REFRAMED: ajax, not crawl) | AUTO PASS (integrity) | 2026-07-25 | 193 corpus records generated, 180 complete, 0 overwrite, check_g2.py | **PENDING: Maria/Ghina** verify spike_gold + field-check 3 |
| G3 | Reference data verified (40-row sheet) | NOT RUN | — | — | — |
| G4 | Retrieval calibrated (top-1 + abstention) | AUTO PASS (synthetic queries) | 2026-07-25 | θ_abs=0.58 θ_amb=0.04; HOLDOUT 96.7% top1-or-clarify, abstain 5/5, clarify 2/2, p50 0.09s; report/evidence/retrieval.md | **PENDING: Ali/Gaby** inspect misses; **re-run on REAL queries at G8** |
| G5 | Graph skeleton (BUILD track, fixtures) | NOT RUN | — | — | n/a |
| G6 | Agent end-to-end (gold + 2 ext calls) | NOT RUN | — | — | — |
| G7 | Freshness & HITL | NOT RUN | — | — | — |
| G8 | Eval (claim-level gold, 24-answer audit) | NOT RUN | — | — | — |
| G9 | UI demo-ready (RTL + offline) | NOT RUN | — | — | — |
| G10 | Repo & report compliant | NOT RUN | — | — | — |
| G11 | Demo readiness (human-only) | NOT RUN | — | — | — |

**Pending human checks queue:**
- **G2 — Maria/Ghina (reviewer Ghina):** corpus generated (193 records, `check_g2.py` integrity
  PASS). Extraction *correctness* still needs a human: open the live guide, diff **3 civil-registry
  core services field-by-field** (11464 بطاقة هوية, 11554 تسجيل ولادة, + one more) + skim 7; in
  `data/spike_gold.json` correct `gold_documents` and set `verified=true`, then re-run
  `python tests/gates/check_g2.py` (target ≥85% recall). Closes G2. **VPN OFF.**
- **G0 — Maria (STILL REQUIRED):** review the 5 Arabic inputs → intent classifications from
  `gpt-oss-120b` in the bakeoff output (all 5 classified correctly: 4 service_query +
  1 invalid_request for the injection). Confirm the model handles Arabic correctly and bless
  `openai/gpt-oss-120b` as the winner. Then G0 is fully signed off. (Auto part already PASS.)
  **Note 2026-07-25:** Mariam marked this signed by herself, but she ran the bakeoff — VERIFICATION
  requires reviewer ≠ producer, and this check is specifically an Arabic-quality read (why the
  owners table names Maria, a designated Arabic expert). Her read is recorded as a producer
  self-check; the gate stays open until Maria signs. Not blocking any work in the meantime.
- ~~G1b — Ghina~~ ✅ **SIGNED by Mariam 2026-07-25** (reviewer ≠ producer; Ali produced). Verified
  live: ministry popups have location + official site + opening hours + portal links but **no phone**;
  the 15 hotlines live in a separate "Useful Numbers" tab. Crawl accurate. **G1b FULLY PASSED.**
  Two enhancement findings logged below (opening hours; ministry hotlines).
- ~~G1 — Mariam~~ ✅ **SIGNED 2026-07-25:** all 5 URLs load, Arabic titles match the catalog
  (pages are sparse — title only — as expected since content is in the ajax endpoint). **G1 FULLY PASSED.**

## Owners (team: Gaby, Mariam, Ali, Ghina, Maria; procedure/Arabic experts = Maria + Ghina)
Gate task owner + independent reviewer (reviewer ≠ producer). Adjust freely — these are proposed
by load-balance + domain fit, not fixed. Individual checklist tasks follow their gate's owner
unless a member picks one up.

| Gate | Owner | Reviewer | Rationale |
|---|---|---|---|
| G0 bakeoff | Gaby | Maria | Maria reads the 5 Arabic outputs to bless the winner |
| G1 catalog | Ali | **Mariam** | reassigned 2026-07-25 (was Gaby) — Gaby not yet a repo collaborator |
| G1b contacts | Ali | Ghina | |
| G2 corpus + field-check | **Maria** | **Ghina** | domain experts verify extraction vs live pages |
| G3 core verification (40) | **Maria + Ghina** | each other | split 40 ≈ 8 each across all 5; experts own accuracy |
| G4 retrieval | Gaby | Ali | |
| G5 graph skeleton | Mariam | Gaby | |
| G6 agent e2e | Gaby | **Maria** | Arabic fluency + usability read |
| G7 freshness/HITL | Ali | Mariam | |
| G8 eval + 2 failure records | Mariam | Ghina | audit = whole team; narratives = whoever hit the failure |
| G9 UI (RTL) | Gaby | **Maria** | Arabic RTL visual check |
| G10 repo + report | Mariam | Gaby | Gaby does the fresh-clone test |
| G11 demo + video | Mariam (coord) | whole team | everyone must justify their decisions in Q&A |

## Task checklist (two parallel tracks after G0 — F29; assign an Owner to each)

### G0 — today (Jul 25) — blocks everything
- [x] repo skeleton + `.gitignore`(secrets-first) + models.py + adapters + G0 harness + prompts → **PUBLIC repo: github.com/mariam-929/OnMyBehalf** (37 files, no secrets tracked)
- [x] Groq key created by Mariam (in local txt OUTSIDE repo)
- [ ] **NEXT: Mariam copies key into `dawlati-agent/.env`** (from `.env.example`), then `pip install -r requirements.txt` + `playwright install chromium`
- [x] **Model bakeoff run (Owner: Mariam)** → **gpt-oss-120b WINS** 10/10@0.55s vs qwen3.6 9/10@1.38s; limits → `data/model_limits.json` (8K TPM)
- [x] MODEL_ID=openai/gpt-oss-120b set in `.env`; recorded in Decisions
- [ ] **PENDING human: Maria** confirms Arabic classifications → G0 fully signed off. (Mariam read
      them 2026-07-25 and found them correct, but she ran the bakeoff — recorded as a producer
      self-check, not the sign-off. Auto part already PASS; nothing is blocked.)
- [ ] freeze `==` pins via `pip freeze` (after Maria signs off)
- [x] venv (outside OneDrive) + deps installed + Playwright chromium

### DATA track (Jul 26)
- [x] `enumerate.py` → `data/catalog.json` (249: 195+24+30 — **exact**) → **G1 AUTO PASS**, confirmed
      independently by `tests/gates/check_g1.py` (7/7) — Owner: **Ali** (pending Mariam's 5-URL check)
- [x] **admin-ajax probe (1 h box) → DECISION recorded** — Owner: **Ali**. Service pages are empty
      (0/249); corpus is in `omsar_load_directory_ministry_services`; 92.8% have required
      documents. Evidence: `report/evidence/ajax_probe.md`. **Supersedes the page-crawl plan.**
- [x] **NEW (replaces spike+crawl): `tools/crawler/fetch_service_directory.py`** → 22 ajax POSTs →
      **193 CorpusRecords written, all Pydantic-valid, 193 distinct post_ids** (docs 93.3%, fees
      69.4%). Joined to `catalog.json` via `tools/text_norm.py` (shared with FR4). 2 directory
      services have no catalog post → `data/corpus_unmatched.json`, not given a guessed id.
      Kept separate from `fetch_directory.py`, which is still the G1b **contacts** crawl — Owner: **Ali**
- [ ] G2 human field-check: 3 core services diffed field-by-field vs the live guide + 7 skimmed.
      **Document splitting is heuristic** (the source mixes numbered/unnumbered items and contains
      its own typos and mid-sentence `<br/>`s) — this check is what validates it — Owner: __
- [ ] **NEW: rebuild core-40 + gold cases + demo queries from the 195 that exist** (passport and
      driving licence are gone) — Owner: __ (needs Maria/Ghina domain input)
- [ ] ~~10-page spike + field-recall scoring~~ **SUPERSEDED by the probe** — there is nothing to
      spike: the pages are empty and the ajax payload is already structured. G2 should instead gate
      on field fill-rate in the harvested directory (measured: docs 92.8%, fees 69.7% — already
      clears the ≥80% documents bar) + a human field-by-field check of 3 core services vs the live
      guide — Owner: __
- [ ] ~~full crawl → `extract.py`~~ **SUPERSEDED** — no HTML extraction needed; `fetch_render.py`
      not needed for services (still needed for the /en/directory contacts crawl, G1b) — Owner: __
- [ ] `core_verification.csv` (40 rows, split across team) + `document_sources.json` (≥20) → G3 — Owner: __
- [x] `indexer.py` → Chroma (193 vectors, BGE-M3, 49.5s build) + `search_services.py` (RRF k=60)
      + `tests/gates/check_g4.py` → **G4 AUTO PASS** on a DEV/HOLDOUT split — Owner: **Ali**
      (nominally Gaby's stream — taken because it was the critical path; **tell Gaby before she
      duplicates it**). e5-base comparison NOT run: bge-m3 cleared every criterion, so the
      fallback was not needed — Owner: __ if anyone wants the comparison for the report

### BUILD track (Jul 26, fixtures from spike)
- [ ] `agents/models.py` — all typed contracts + discriminated responses (F07/F08) — Owner: __
- [ ] All 3 prompts v1 drafted BEFORE nodes (F16): intent_classifier, research_agent, composer — Owner: __
- [ ] graph skeleton + detect_language + validate_input + unit tests → G5 — Owner: __

### Jul 27
- [ ] retrieve (RRF) + research_loop (tool-calling) + compose on real index — Owner: __
- [ ] check_freshness (REST modified_gmt) + live_service_lookup + system per-doc freshness + QueueEvent append — Owner: __
- [ ] smoke 5 (incl. gold case, 2 external calls visible) → G6; ITERATION_LOG first entries — Owner: __
- [ ] `diff_recrawl.py` (canonical hash) + G7 — Owner: __
- [ ] Streamlit shell + RTL wrapper — Owner: __

### Jul 28
- [ ] 24 test cases + `run_eval.py` + claim-level gold + all-24 manual audit → G8 — Owner: __
- [ ] prompt iterations v2/v3 (all three, logged) — Owner: __
- [ ] UI finish + `--offline` mode → G9 — Owner: __
- [ ] competitor 5-query comparison (vs OMSAR Assistant) — Owner: __
- [ ] evidence-capture sweep; report §§1–4 drafted — Owner: __

### Jul 29 (deadline)
- [ ] report finished → PDF (8 sections); repo cleanup + `secret_scan.py` + README + video link → G10 — Owner: __
- [ ] demo rehearsal ×2 + provider-outage drill + backup video → G11; SUBMIT — Owner: __

## Evidence register (F28 — capture DURING build, not reconstructed on Jul 29)

| Report/demo claim | Artifact needed | Capture moment | Path | Captured? |
|---|---|---|---|---|
| Model decision | bakeoff numbers table | G0 | report/evidence/bakeoff.md | [x] both runs + the reproducibility caveat + the French-visa refusal difference |
| Coverage denominators | catalog/fetched/extracted/verified counts | G1–G3 | report/evidence/coverage.md | [~] catalog=249 captured at G1; fetched/extracted/verified pending G2–G3 |
| Retrieval quality | G4 gold results + θ values | G4 | report/evidence/retrieval.md | [x] θ values, holdout numbers, both design corrections, synthetic caveat |
| Agent loop / 2 ext calls | trace excerpt (JSONL) | G6 | report/evidence/trace_normal.json | [ ] |
| 3 prompt iterations | ITERATION_LOG diffs | Jul 27–28 | prompts/ITERATION_LOG.md | [ ] |
| 2 failure analyses | narratives + before/after | as they occur | report/evidence/failures.md | [ ] |
| Eval numbers | eval_report.json + audit.md | G8 | tests/eval_report.json | [ ] |
| Hallucination audit | 24-answer audit notes | G8 | report/evidence/audit.md | [ ] |
| Demo screenshots | UI (EN + AR RTL + failure) | G9 | report/evidence/screens/ | [ ] |
| Competitor comparison | 5-query table | **G0/G1 (moved earlier — A25)** | report/evidence/competitor.md | [ ] |
| Architecture diagram (A20) | final pipeline figure | Jul 28 | report/evidence/architecture.* | [ ] |
| Appendix assembly (A20) | prompt appendix + raw eval logs + AI log collated | Jul 29 | report/appendix/ | [ ] |
| Contact coverage (A27) | authorities-with-contact count | G1b | report/evidence/contacts_coverage.md | [x] 126 records; 3/3 corpus authorities, 21/22 taxonomy; **no per-authority phones exist** |
| Spike ground truth (A13) | per-field annotations, 10 pages | G2 | data/spike_gold.json | [ ] |

## Decisions made mid-implementation (append)

| Date | Decision | Why |
|---|---|---|
| 2026-07-25 | Docs v1→v2 after adversarial review; RESOLUTIONS.md records all 43 dispositions | ~30 findings valid incl. 2 verified blockers (F01 model retirement, F02 freshness) |
| 2026-07-25 | Docs v2→v3 after 2nd review (A01–A30) | ~26 valid; per-model adapters, bounded loop, gold-oracle split |
| 2026-07-25 | **get_contacts → live_service_lookup** | LIVE test: Dawlati REST exposes no contact fields; REST `?search=` verified as the 2nd external call |
| 2026-07-25 | Freshness labels → unchanged/changed/unverified | modified_gmt detects source change, not currency (A08) — honest semantics |
| 2026-07-25 | **Crawl the directory admin-ajax endpoint; do NOT crawl the 219 service pages** (admin-ajax probe, owner Ali, 1 h box) | The service pages are EMPTY: 0/249 posts have REST content, and a rendered page yields 431 chars of nav/title/footer with no section keywords and no content XHR. A page crawl would have produced 219 empty records and failed the G2 spike at ~0% recall. Content lives in `admin-ajax.php action=omsar_load_directory_ministry_services` (nonce from `var ajaxConfig`, not per-user → plain `requests` works), returning `required_documents_html` / `fees_html` / `notes_html` / `doc_url` per service. **181/195 (92.8%) have required documents; 136/195 (69.7%) have fees.** 22 POSTs ≈ 30 s replaces a 219-page Playwright crawl. Evidence: `report/evidence/ajax_probe.md` |
| 2026-07-25 | **Core-40, gold cases and demo queries must be rebuilt from the 195 services that exist** | Only 3/22 ministries are populated (agriculture 115, interior 53, culture 27) — Dawlati's own notice says it is still adding documents. Planned core services **passport renewal and driving licence do not exist** (the only «جواز سفر» hit is a horse passport). `gold_claims.seed.json:normal_passport_en` and the SCOPE §9 demo query are unanswerable as written. Civil-registry services (هوية، تسجيل ولادة/زواج/وفاة، بيان قيد) DO exist and are strong replacements |
| 2026-07-25 | **MODEL_ID = openai/gpt-oss-120b** (G0 bakeoff winner; owner Mariam) | 10/10 schema-valid @0.55s p50 vs qwen3.6 9/10 @1.38s (1 json_validate_failed, Preview). GPT-OSS: strict schema, 2.5× faster, not Preview. Both 8K TPM. Also fixed adapter (strict `additionalProperties`) + UTF-8 console. |
| 2026-07-25 | **Corpus generated (193 records); G2 reframed + `check_g2.py`; G2 integrity AUTO PASS** | Ran the ingester for real → 193 `data/corpus/*.json` (180 complete, 0 overwrite). G2 no longer a page-crawl spike (pages empty) — now extraction-correctness: `check_g2.py` integrity PASS, recall-vs-gold PENDING human. `data/spike_gold.json` pre-filled (8 svcs) for Maria/Ghina to verify. VERIFICATION G2 updated to ajax reality. |
| 2026-07-25 | **Core-40 candidates drafted from the real corpus** → `report/evidence/core40_candidates.md` | 43 civil-registry services exist (بطاقة هوية 9 docs, تسجيل ولادة, personal-status set) + 52 interior/27 culture/101 agriculture complete. Grounds the Maria/Ghina rebuild (verify, not invent). Passport/license confirmed absent across all post types. |

## Findings / surprises

- **2026-07-25 — Dawlati Cloudflare 403s VPN/datacenter IPs (Ali, env setup).** Every dawlati.gov.lb
  path — REST endpoints AND the plain homepage — returned `403 / server: cloudflare` ("Attention
  Required!") from `requests`, `curl`, and real headless Chromium alike, while other sites (incl.
  other Cloudflare-fronted ones) returned 200. Cause was a **VPN connection**, not the User-Agent,
  the code, or the network. VPN off → 200 on all three post types immediately. **If any Dawlati call
   403s, check the VPN before debugging the code.** (The browser-UA header in `enumerate.py` is still
  required — Cloudflare also 403s default clients — so both conditions must hold.)
- **2026-07-25 — the Dawlati service PAGES are empty; the content is in a directory ajax endpoint
  (Ali, admin-ajax probe).** The 2026-07-24 recon recorded detail pages as "JS-rendered", which
  read as *content arrives via JS*. It is not: **0 of 249 posts have any REST content**, and a
  fully rendered page yields 431 chars (nav/title/share/footer) with every section keyword absent
  and no content XHR at all. The real corpus is behind
  `admin-ajax action=omsar_load_directory_ministry_services`, one call per ministry, returning
  structured `required_documents_html` / `fees_html` / `notes_html` / `doc_url`.
  **181/195 (92.8%) carry required documents.** Full numbers: `report/evidence/ajax_probe.md`.
- **2026-07-25 — only 3 of 22 ministries are populated** (agriculture 115, interior 53, culture 27;
  the other 19 return 0). Dawlati says so itself on the guide page: «نعمل تدريجياً على إضافة
  النماذج الرسمية والوثائق المطلوبة». This is a property of the SOURCE, not of our crawl — report
  it that way, and do not present 195 as national coverage.
- **2026-07-25 — passport renewal and driving licence DO NOT EXIST in the directory.** Both are in
  `curated_core.seed.json`; passport renewal is also a `gold_claims.seed.json` case, a G0 bakeoff
  fixture and the SCOPE §9 demo query. The only «جواز سفر» match is `إصدار جواز سفر للخيل` — a
  horse passport. Civil-registry services (بطاقة هوية، تسجيل ولادة/زواج/وفاة/طلاق، بيان قيد عائلي
  وإفرادي) do exist and are the natural replacement set.
- **2026-07-25 — the ajax payload has no `post_id` and no `modified_gmt`**, which FR6
  `check_freshness(post_id)` requires. Directory services must be joined to `data/catalog.json` on
  normalised title; unmatched ⇒ `unverified`. Needs a decision at G2/G7.
- **2026-07-25 — opening hours are published per ministry but NOT captured (Mariam, G1b review).**
  Ministry popups on /en/directory show opening hours, and `opening_hours` IS a field in the
  `directoryEntityData` blob that `fetch_directory.py` already fetches — the crawl just doesn't
  extract it into `ContactRecord`. Relevant: "opening times" was in the original product vision.
  **✅ DONE 2026-07-25:** `opening_hours` added to `ContactRecord` + `ContactOut` + extracted in
  `fetch_directory.py` — **23 ministries carry hours** (e.g. الزراعة "8AM-2PM").
- **2026-07-25 — the "Useful Numbers" tab contains MINISTRY hotlines (Mariam, G1b review),** so
  Ali's "no per-authority phones" is true for the popups but too strong overall: Education 1747,
  Environment 1789, Health 1214, Labor 1740, Social Affairs 1714, Communications 1775,
  Interior-Complaints 1744 are ministry-specific. **✅ DONE 2026-07-25:** `fetch_directory.py` now
  joins the tab hotlines onto ministry records (conservative name match, no false positives) —
  **6 ministries gained a hotline** (phones 15→21/126); Interior-Complaints stays standalone (it's
  a complaints line). Source conflict Mariam spotted (Agriculture site says 1789, Dawlati assigns
  1789 to Environment) logged as a real HITL/review-queue example.
- (nothing else from implementation yet — the F01 model retirement was caught by review, pre-code)

## Blockers

- **NONE blocking G0.** Owners assigned (table above; team confirmed: Gaby, Mariam, Ali, Ghina,
  Maria; experts Maria+Ghina). Groq key created by Mariam (stored in a local txt OUTSIDE the repo;
  goes into `.env` at scaffold, gitignored).
- Bakeoff winner's Arabic quality and crawl extraction quality unknown until G0/G2 (measured, not
  assumed) — expected, not a blocker.

## Session log (newest first)

- **2026-07-25 (Ali — indexer + G4 retrieval):** `tools/indexer.py` (BGE-M3 1024-dim → Chroma,
  193 vectors, 49.5s build), `tools/search_services.py` (BM25 titles + dense, RRF k=60, FR2
  outcome), `tests/gates/check_g4.py` (DEV/HOLDOUT calibration). **G4 AUTO PASS:** θ_abs=0.58,
  θ_amb=0.04, holdout **96.7%** top-1-or-clarify, known-out abstain **5/5**, under-specified
  clarify **2/2**, p50 latency **0.09s**. Evidence: `report/evidence/retrieval.md`.
  **Two design corrections, both forced by measured failures — worth the report's method section:**
  (1) **RRF ranks, cosine decides.** Thresholding on the RRF score (the literal plan) does not
  work: RRF is bounded and encodes *whether both channels returned a doc*, not relevance. Under
  it, "تجديد جواز السفر" returned **`found` → `إصدار جواز سفر للخيل`, a horse passport**, and the
  out-of-jurisdiction French-visa query scored higher than many correct hits. Abstention/ambiguity
  now read dense cosine; both queries correctly abstain.
  (2) **BM25 gated to positive scores.** An English query matches no Arabic title but BM25 still
  ranks every doc, and RRF treated that garbage rank-1 as authoritative — "how do I get an ID card"
  returned an ISBN request, with the correct `بطاقة هوية` at #3 despite cos 0.610, and a doc at
  **cos 0.000** scoring 0.0164. Gated, English queries run dense-only and resolve correctly.
  **Two caveats that MUST reach the report:** the query set is **synthetic** (templated from
  titles — an upper bound and regression guard, not measured quality; re-run on real queries at
  G8), and the objective **counts a clarification as equal to a correct top-1**, which biases the
  agent toward asking rather than answering — θ_amb=0.02 gives 92.2% top-1 vs 84.4% at the chosen
  0.04. That is a product call for the team; it is one value in `data/retrieval_thresholds.json`.
  **Chose bge-m3 without running the e5-base comparison** — it cleared every criterion, so the
  fallback was unnecessary; flagged in case the report wants the comparison anyway.
  **Coordination note: this is Gaby's stream on the owners table.** Taken because it was the
  critical path; Gaby must be told before she duplicates it, as happened with G1.

- **2026-07-25 (Ali — G0 reproduced independently + bakeoff evidence captured):** Groq key wired
  into Ali's `.env` (gitignored; verified never tracked, absent from history). Ran
  `tests/gates/check_g0.py` on the second machine: **gpt-oss-120b 10/10 @0.523s p50 vs qwen3.6
  10/10 @1.172s**, 8K TPM both. **AUTO PASS again; winner unchanged.** Two things this second run
  established that the first could not:
  (1) **The 9/10-vs-10/10 schema gap does NOT reproduce** — Qwen scored 10/10 here, so its single
  `json_validate_failed` was transient (exactly what its retry path exists to absorb). The report
  must rest the model decision on the reproducible grounds — 2.2× latency, strict `json_schema`
  support, non-Preview — and not on the schema-validity difference.
  (2) **A behavioural difference worth reporting:** on the adversarial fixture "How do I apply for
  a French visa?" GPT-OSS returned `invalid_request` (correct per FR8) while **Qwen returned
  `service_query`** — it would have attempted an answer. That maps onto one of the 6 adversarial
  eval cases and is a quality argument for the winner, not just a speed one. n=1, so an
  observation rather than a measured refusal rate.
  Evidence register row "Model decision" now filled: `report/evidence/bakeoff.md`.
  Also fixed a stale docstring in `fetch_directory.py` (it still claimed phones are empty for every
  ministry, which Mariam's hotline-join enhancement superseded). **Key note: the Groq key was
  pasted into a chat transcript — rotate it before submission on Jul 29.**

- **2026-07-25 (corpus generation + G2 setup, after PR #1 merge):** Reviewed + verified Ali's PR
  (independently reproduced 193 records). Generated the corpus for real → 193 `data/corpus/*.json`.
  Reframed G2 (no page crawl; pages empty) → wrote `tests/gates/check_g2.py` (integrity PASS,
  recall-vs-gold pending human) + pre-filled `data/spike_gold.json` (8 svcs) for verification.
  Drafted grounded core-40 list → `report/evidence/core40_candidates.md` (43 civil-registry svcs;
  passport/license confirmed absent). Updated VERIFICATION G2 + PROGRESS. **G0/G1/G1b/G2 all AUTO
  PASS; each awaits its human sign-off (Maria / Mariam / Ghina / Maria+Ghina).** Next: Maria+Ghina
  rebuild core-40 from candidates → G3; BUILD track G5 in parallel.
- **2026-07-25 (Ali — G1b contacts):** `tools/crawler/fetch_directory.py` implemented →
  **126 ContactRecords, all Pydantic-valid**. **No Playwright needed** — the stub assumed the
  directory was client-rendered; both datasets are embedded in the page HTML (`var
  directoryEntityData` for 26 ministries / 46 public institutions / 39 municipalities / 0
  governorates, and `article.directory-number-card` for 15 hotlines). Bilingual join on
  `official_domain`, not `key` — Polylang gives EN/AR translations different post ids.
  **G1b AUTO PASS:** coverage 3/3 corpus authorities (100%) and 21/22 taxonomy terms (95%) vs the
  ≥60% gate — both denominators reported since the core-40 no longer exists.
  **Measured limitation: the directory publishes NO per-authority phone numbers** — only 15
  national hotlines, belonging to no specific service. `ContactRecord.phones` is empty for every
  ministry; addresses exist for 23. This is the source's limit, exactly the SCOPE §15 "contacts
  thin" risk, and the agent must not be described as returning a phone number for a service.
  Evidence: `report/evidence/contacts_coverage.md`. Pending human: **Ghina**, 3 vs live.

- **2026-07-25 (Ali — admin-ajax probe, 1 h box, DECISION recorded):** The probe found the plan's
  crawl target is empty and the real corpus is somewhere else. **0 of 249 posts carry any content**
  in REST; a fully rendered service page gives 431 chars of nav/title/footer, no section keywords,
  no content XHR. Checked **all 26 post types** (the plan froze 3 without verifying): only 2 news
  posts have content. The corpus is behind `admin-ajax
  action=omsar_load_directory_ministry_services`, one POST per ministry, returning structured
  `required_documents_html` / `fees_html` / `notes_html` / `doc_url`. Harvested all 22 ministries:
  **195 services, 181 (92.8%) with required documents, 136 (69.7%) with fees.** Nonce is not
  per-user, so plain `requests` works — 22 POSTs ≈ 30 s replaces the planned 219-page Playwright
  crawl, and the 10-page spike + `extract.py` are moot. **Three consequences needing team input:**
  only 3/22 ministries are populated (source's own limitation, must be reported honestly, not as
  national coverage); **passport renewal and driving licence do not exist**, breaking a gold case,
  a G0 fixture and the demo script; and the ajax payload has no `post_id`/`modified_gmt`, which
  FR6 freshness needs. Evidence: `report/evidence/ajax_probe.md`.
  **Next: `fetch_directory.py` (ajax ingester) + rebuild core-40/gold/demo from what exists.**

- **2026-07-25 (Ali — merged Mariam's G0/G1 work into `data-crawl`):** Mariam and Ali ran G1
  independently and **agree exactly: 249 = 195/24/30, 0 dup ids, all modified_gmt.** Her
  `tests/gates/check_g1.py` passes **7/7 against Ali's `data/catalog.json`** — two independent
  paths to the same result, which is a stronger G1 than either alone. Merged (conflict in this
  file, resolved). Three corrections made in the merge, all open to challenge in PR #1:
  (1) **G0 restored to AUTO PASS + PENDING: Maria** — Mariam had marked the human check signed by
  herself, but she ran the bakeoff; VERIFICATION requires reviewer ≠ producer and this check is an
  Arabic-quality read that the owners table assigns to Maria. Her read is kept in the record as a
  producer self-check. Nothing is blocked by leaving it open.
  (2) **G1 reviewer = Mariam, not Ali** — her version assigned the check to Ali, who produced the
  catalog. Same rule, opposite direction.
  (3) **`check_g1.py` sample seeded (SAMPLE_SEED=7)** — it used unseeded `random.sample`, so the
  reviewer's 5 URLs changed every run and could not be re-verified or cited. Now reproducible and
  identical to the 5 recorded in `report/evidence/coverage.md`.

- **2026-07-25 (Ali — env setup + G1 catalog):** Second dev environment stood up (venv
  `~/venvs/OnMyBehalf` on **Python 3.13**, outside OneDrive; 3.14 is too new for chromadb/torch
  wheels and the 3.10 on PATH is the Store build). All deps + Playwright chromium installed; imports
  and `agents.models`/`agents.adapters` clean; `check_g0.py` runs and stops correctly at the missing
  key (key not yet copied from Mariam — not a blocker for the DATA track). **Hit a hard Cloudflare
  403 on every Dawlati path — cause was a VPN connection, not code/UA (logged under Findings).**
  VPN off → **G1 run: `enumerate.py` → `data/catalog.json`, 195+24+30 = 249 exact**, 0 dup ids, all
  rows carry modified_gmt/title/https url → **G1 AUTO PASS**; denominators captured to
  `report/evidence/coverage.md`. Pending human: **Mariam** opens the 5 sampled URLs (G1 reviewer
  reassigned from Gaby, who is not yet a repo collaborator; reviewer ≠ producer still holds).
  PR: https://github.com/mariam-929/OnMyBehalf/pull/1
  **Next: admin-ajax probe (1 h box) → 10-page spike + `data/spike_gold.json` → G2.**
- **2026-07-25 (env setup + G0 bakeoff):** Repo scaffolded + pushed (public: github.com/mariam-929/
  OnMyBehalf); plan moved into repo `docs/` + CONTRIBUTING/SETUP/CLAUDE. Env installed outside
  OneDrive (venv + all deps + Playwright chromium; all imports OK). Groq key wired into `.env`
  (gitignored, validated live; both models available). **G0 bakeoff RUN (Mariam): gpt-oss-120b
  WINS 10/10@0.55s vs qwen3.6 9/10@1.38s.** MODEL_ID set. Fixed adapter (strict additionalProperties)
  + UTF-8 console. **Auto PASS; Maria's Arabic confirmation pending** before G0 fully closes.
- **2026-07-25 (3rd review + N-fixes):** Third pre-code review returned START CODING (0 blockers;
  confirmed prior F/A fixes are real artifacts, not prose). Verified N1–N6 against the files, folded
  all: added LiveLookupResult + newer_version_available (N6); rewrote composer few-shot so no number
  is invented (N1); added IntentResult/ResearchPlan/PlanStep to schema (N2); per-doc freshness now a
  deterministic system step with ≤6 model-tool cap + >4-doc degrade (N3); fixed PROGRESS stale
  get_contacts/v2 refs (N4); RESOLUTIONS supersession note (N5). Plan is green; next = owners → G0.
- **2026-07-25 (2nd review + v3 folding):** Verified re-evaluation A01–A30 vs Groq docs + LIVE
  Dawlati API. Confirmed A01 (per-model structured-output/reasoning differences), A02 (8K TPM),
  A30 (Qwen Preview), and — via direct API calls — that contacts are NOT in REST (A06/A27) while
  REST `?search=` works. Folded ~26 findings to v3: created SCHEMA_AND_CONTRACTS.md, 3 prompt
  drafts, gold_claims.seed.json; replaced get_contacts→live_service_lookup; bounded research loop;
  freshness relabeled; gold oracle split from verification CSV; added G1b; separated outage drills.
  Still no production code; next = assign owners → G0.
- **2026-07-25 (review + amendment session):** Verified adversarial review vs primary sources
  (confirmed F01 both Groq models retired Jul 17; F02 freshness broken; F22 LangSmith privacy
  conflict; F33 timeouts async-only but NOT alpha). Amended SCOPE/TECH_PLAN/VERIFICATION to v2;
  created RESOLUTIONS.md + report/AI_LOG.md. Cut Tavily + LangSmith; redesigned freshness to REST
  modified_gmt; added research tool-loop (2 external calls), discriminated schema, typed
  contracts, RRF retrieval, computed confidence, claim-level eval gold, offline demo mode,
  evidence register. Deadline confirmed in writing (Jul 29). Still no code; next = G0 bakeoff.
- **2026-07-25 (planning session):** SCOPE v1 gaps fixed; TECH_PLAN v1 written (contained the F01
  stale-model error); PROGRESS + VERIFICATION + REVIEW_PROMPT created.
- **2026-07-24 (scoping session):** Idea evaluated; Dawlati recon (REST works, detail pages
  JS-rendered, portal login-walled, ai-train=no); CLAUDE.md + SCOPE.md created; 4 scope decisions
  locked.
