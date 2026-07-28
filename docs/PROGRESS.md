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

### ▶ CURRENT STATE — read this first (2026-07-29)

**Deadline: today.** On **`main`**, synced with origin, tree clean. `build-graph-g5` was merged
(fast-forward) — work directly on `main` now.

#### The 7 things that will waste your time if you don't know them

1. **VPN OFF for anything touching dawlati.gov.lb.** Cloudflare 403s VPN IPs. The symptom is
   subtle: answers still render, they just all say `freshness: unverified`.
2. **Launch the UI with the `-m` form**, never bare `streamlit run` — `streamlit` is not on the
   system PATH and `Activate.ps1` silently fails under PowerShell's execution policy. This caused
   a real "localhost refused to connect" panic. Command and full guide: **`RUN.md`**.
3. **First query ~25 s** (encoder load), then ~1.3 s. **Warm it before any demo.**
4. **`data/` is gitignored.** A fresh clone has NO corpus and NO index. Rebuild:
   `enumerate.py` → `fetch_service_directory.py` → `indexer.py`.
5. **Encoder is LaBSE, not BGE-M3** (BGE-M3 stalled at ~1.2 GB of 2.3 GB). LaBSE is the code
   default. `EMBED_MODEL` overrides it, but you must rebuild the index after changing it.
6. **A large background download breaks the live tool calls.** Cost an hour of false debugging
   when freshness read "source unreachable" while the tools worked fine standalone.
7. **Groq free-tier latency is erratic** — 0.5 s to 12.8 s for identical calls. Both model calls
   are now time-bounded (6 s classify, 8 s narrate) with deterministic fallbacks. **Do not remove
   those timeouts to "improve quality"** — they are what stops the demo stalling for 40 s.

#### The architecture decision that governs everything (2026-07-29)

**The model writes LANGUAGE; code owns FACTS.** The composer LLM emits exactly two fields —
`reasoning` (logged) and `summary` (1–2 sentences to the citizen). It never sees or reproduces a
document name, fee, office, URL or duration; those are assembled from the retrieved record.

This is why "0 hallucinations" holds *and* the answer still reads like an agent. **If you ever let
the model emit factual fields, that guarantee dies.** Verified: after wiring the composer, prose
became model-written and hallucinations stayed at 0.

Before this, the LLM was used in **exactly one node** (`classify_intent`), `reasoning` was a
hardcoded constant identical on every answer, and `composer_v1.md` was 69 lines of dead code.

#### Team

**Ali and Gaby are out** (2026-07-28); their streams were absorbed. **Maria and Ghina delivered in
full** — their verification is the backbone of G2 and G3. Consequence: the technical gates have
**no independent technical reviewer**. Those sign-offs are recorded as producer self-checks, never
filled in. REPORT §7.7 names exactly which gates have real independence.

#### Gate status

| Gate | State |
|---|---|
| G0 bakeoff | ✅ PASS — closed 2026-07-28 by Mariam's decision (producer == reviewer, recorded as such) |
| G1 / G1b | ✅ FULLY PASSED |
| G2 corpus | ✅ **FULLY PASSED** — recall 90%, precision 81%, human check complete both directions |
| G3 core-44 | ⚠️ **PARTIAL** — exact gaps below |
| G4 retrieval | ⚠️ **2/4** — top-1 88% (CI 53–98%), abstain 1/3. Left failing deliberately |
| G5 graph | ✅ AUTO PASS 9/9 · 64 unit tests |
| G6 agent e2e | ✅ AUTO PASS 8/8 |
| G7 freshness/HITL | ⚠️ code exists + unit-tested; `diff_recrawl.py` still a stub, no `check_g7.py` |
| G8 eval | ⚠️ RUN — needs the all-24 manual audit |
| G9 UI | ✅ AUTO PASS 5/5 |
| G10 repo/report | ⚠️ REPORT.md complete; repo hygiene + secret-scan script + README refresh not done |
| G11 demo | ❌ **NOT STARTED — human-only and the top priority** |

#### G3's exact gaps (audited 2026-07-29)

| requirement | reality |
|---|---|
| `core_verification.csv`, 40 rows each signed | **missing.** `curated_core.json` has 44 *selections* — that is the PICK, not a row-by-row field verification. Only **8** services were ever checked field-by-field (the G2 worksheets) |
| `document_sources.json`, ≥20 rows source-checked | **missing.** Seed has **3 rows, 0 with a `source_url`** |
| `gold_claims.json` ≥10 **normal** cases | has 8 cases but only **5 are `normal`** — short by 5 |
| `check_g3.py` | **missing** |

**Do not pad the gold with developer-written cases to reach 10.** Developer-written queries have
flattered the numbers twice already. Report 5 honestly.

#### Headline numbers (all reproducible — `VERIFY.md`)

| metric | value | source |
|---|---|---|
| Eval failure rate | **36.4%** (8/22 scored) | `tests/eval_report.json` |
| Hallucinated documents | **0** | ibid — **never quote bare, see below** |
| Latency | **p50 1.26 s**, mean 6.7 s, max 33.4 s (first case = cold load) | ibid |
| Adversarial | **6/6** | ibid |
| Retrieval top-1 (holdout) | 88% (7/8), CI 53–98% | `check_g4.py` |
| Extraction recall / precision | 90% / 81% | `check_g2.py` |
| Conditional structure | 113/180 (63%), 46 (26%) high-confidence | `tools/conditional_detect.py` |
| Core services | 44 (Maria 23 + Ghina 21) | `data/curated_core.json` |

**⚠ Never quote "0 hallucinations" without the caveat.** Documents are passed through from the
record, not generated, so fabrication is structurally impossible in that list. The detector is
real (verified by injecting a fabrication — it caught it), but zero reflects an architectural
choice, not model restraint. REPORT §6.1 says this; so must anyone presenting.

#### Findings that carry the report

1. **A flat `list[str]` cannot represent these services** (REPORT §5) — branch by applicant,
   either/or, preconditions, per-case recency windows. #11476 has all four. 63% of the corpus
   affected. Detected and disclosed, not fixed.
2. **Semantic similarity cannot detect absence.** «شو بدي لأجدد جواز سفري؟» returns
   **إصدار جواز سفر للخيل** (a HORSE passport) at cos 0.598. Abstention is 1/3.
3. **Arabizi routes as English** — script-ratio detector. 2 eval cases marked `known_fail`, kept
   in and scored so the failure is measured rather than hidden.
4. **Our own measurement failed twice, and both are in the report.** We published top-1 100% and
   retracted it (the gold was bare titles scoring cos 1.000); and `check_g4` scored abstention on
   cosine while the runtime thresholded on RRF — the gate passed while the agent refused a valid
   query. **Pattern: every time the test data became more independent, the numbers got worse**
   (3/8 on the experts' own questions vs 88% on ours).
5. **Two prompts were never being sent.** `intent_classifier` ran with `system_prompt=""` (the
   model then refused Ghina's own question); the composer was never called at all. ITERATION_LOG
   entry 1.

#### NEXT ACTIONS, in priority order

1. **G11 demo rehearsal — human-only, nobody else can do it.** 2 runs, 3 outage drills, backup
   video. Verified-working demo prompts (Arabic and English) are in `RUN.md`.
2. **G10 repo hygiene** — secret-scan script, README refresh, fresh-clone test (`VERIFY.md` has
   the audit commands).
3. **G8 manual audit** of all 24 answers (Maria/Ghina).
4. **G3 — `document_sources.json` is the highest-VALUE remaining item.** It is what lets
   `resolve_document` answer "where do I obtain this" for documents that are not themselves
   services. Needs a human to find and record each source URL; **do not invent them.**
5. Optional: `diff_recrawl.py` for a full G7; an `--offline` demo cache; regenerate
   `report/evidence/bakeoff.md` (evidence-polish only, now that G0 is closed).

#### Orientation for a new session

Read in this order: **`VERIFY.md`** (how to check everything, including how to catch me being
wrong) → **`RUN.md`** (launch + verified demo prompts) → **`report/REPORT.md`** →
**`prompts/ITERATION_LOG.md`** → this file.

**Never fill in a human sign-off.** Gates are allowed to fail — G2 sat at an honest FAIL until a
validated fix raised it to 90%, and G4 still fails 2/4 on purpose.

---
_(historical planning log below — CURRENT STATE above supersedes it for "where are we now")_

## Gate record (AUTHORITATIVE — defs in `VERIFICATION.md` v3; no step starts before upstream gates
## PASS; Claude runs auto checks but may NOT fill "Human sign-off")

| Gate | What | Status | Date | Evidence | Human sign-off |
|---|---|---|---|---|---|
| G0 | Env + **per-model bakeoff** + synthetic fixtures | ✅ **PASS** | 2026-07-28 | gpt-oss-120b 10/10@0.55s vs qwen3.6 9/10@1.38s; data/model_limits.json | **Mariam 2026-07-28** — closed on her authority as project lead. She read the 5 Arabic classifications 2026-07-25 and found them correct, but she also RAN the bakeoff, so reviewer≠producer is **not** satisfied for this gate. Recorded as a producer self-check promoted to a sign-off by decision, not as an independent review. Listed in REPORT §7.7 with the other partial-independence gates. |
| G1 | Service catalog (249 posts) | ✅ PASS | 2026-07-25 | data/catalog.json — 249 (195/24/30), 0 dup ids, all modified_gmt; `check_g1.py` 7/7; report/evidence/coverage.md | **Mariam 2026-07-25** (5 URLs load, titles match) |
| G1b | Contact catalog (/en/directory crawl) | ✅ PASS | 2026-07-25 | 126 ContactRecords, all valid; coverage 100%/95%; contacts_coverage.md | **Mariam 2026-07-25** (verified live: ministries have location+site+hours+portals, no phone; 15 hotlines in Useful Numbers tab). 2 enhancement findings logged |
| G2 | Corpus quality (REFRAMED: ajax, not crawl) | ✅ **PASS** | 2026-07-27 | 193 records, 180 complete; **recall 90% (36/40), precision 81%**; check_g2.py 5/5 | **Maria + Ghina 2026-07-27** — 8 services verified, cross-reviewed both directions (reviewer≠producer holds each way). Worksheets in report/evidence/ |
| G3 | Reference data verified (**core-44**, not 40) | ⚠️ **PARTIAL** | 2026-07-28 | `data/curated_core.json` **44 services** (Maria 23 + Ghina 21, each in her own clusters; 9 skipped w/ reasons); `tests/gold_claims.json` **8 claim-level cases**, all written BY the experts. Still missing: `core_verification.csv`, `document_sources.json` (≥20 source-checked rows), `check_g3.py` | Selections ARE the human check (reviewer≠producer holds: each judged her own cluster, neither approved her own). Lookup-table rows still need source-checking |
| G4 | Retrieval calibrated (top-1 + abstention) | ⚠️ **2/4 AUTO** | 2026-07-28 | holdout top-1 **88% (7/8, CI 53-98%)**, abstain **1/3**, clarify 1/1, 1.26s/query; theta_abs=0.55 cosine, dev-only calibration; report/evidence/retrieval.md | **PENDING: Maria/Ghina** — inspect misses + verdict. Reviewer: __ |
| G5 | Graph skeleton (BUILD track, fixtures) | ✅ **AUTO PASS** | 2026-07-27 | `check_g5.py` 9/9: compiles (14 nodes); all 5 terminal actions schema-valid w/ traces; 64 unit tests green | **n/a — no human check** |
| G6 | Agent end-to-end (gold + 2 ext calls) | ✅ **AUTO PASS** | 2026-07-28 | `check_g6.py` 8/8 — live index + live REST; both external calls in trace; 4/5 docs resolved; adversarial refused; out-of-scope abstains; report/evidence/trace_normal.json | **PENDING: Maria/Ghina** read the Arabic answer for fluency. Reviewer: __ |
| G7 | Freshness & HITL | NOT RUN | — | — | — |
| G8 | Eval (claim-level gold, 24-answer audit) | ⚠️ **RUN** | 2026-07-28 | 24 cases; **failure rate 36.4% (8/22)**, **hallucinations 0**, latency p50 1.56s/mean 4.96s; adversarial 6/6; tests/eval_report.json | **PENDING**: all-24 manual audit (Maria/Ghina). Reviewer: __ |
| G9 | UI demo-ready (RTL + offline) | ✅ **AUTO PASS** | 2026-07-28 | `check_g9.py` 5/5 — headless 200 in 3.4s, --offline banner, `<script>` + bidi payloads escaped, AR→rtl/EN→ltr | **PENDING**: non-builder walks the demo (A15). Reviewer: Maria/Ghina |
| G10 | Repo & report compliant | NOT RUN | — | — | — |
| G11 | Demo readiness (human-only) | NOT RUN | — | — | — |

**Pending human checks queue:**
- ~~**G2 — Maria/Ghina**~~ ✅ **HUMAN CHECK COMPLETE 2026-07-27.** Both worksheets returned and
  cross-reviewed (Ghina reviewed Maria's 4; Maria reviewed Ghina's 4 — all AGREE, with substantive
  additions). Reviewer ≠ producer satisfied in both directions. Transcribed to `data/spike_gold.json`
  (8 services verified). **AUTO now PASSES: 90% pooled recall (36/40), precision 81%** after the two splitter fixes.
  Human verdict BAD stands on 11464, 11554, 11476 — recorded as report material, not a blocker.
  Worksheets: `report/evidence/g2_worksheet_maria_FULL.md`, `g2_worksheet_ghina (Final).md`.
- **G3 — Maria + Ghina (Job C, core-40 rebuild) — NOW THE CRITICAL PATH.** Worksheets:
  `report/evidence/jobc_worksheet_{maria,ghina}.md` (split by procedure family; 26 / 27 rows).
  **Maria's half is IN** (`jobc_worksheet_maria_completed.md`: 23 KEEP / 3 SKIP + 4 demo questions;
  3 SKIPs flagged for Mariam to verify — 11472 شكاوى, and two suspected duplicate pairs
  11522↔11476, 11498↔11560). **Ghina's 27 rows are OUTSTANDING and block G3.** Reminder: the
  existing `gold_claims.seed.json` has only 3 cases and 2 of them are passport-based, so the
  usable gold is effectively **1 vs a required ≥10** — Job C's 8 demo questions are the seed.
- ~~**G0 — Maria**~~ ✅ **CLOSED 2026-07-28 by Mariam's decision** (see gate record; independence limitation recorded, not hidden).
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
- [ ] `indexer.py` → Chroma; G4 calibration on 10-query gold → BGE-M3 vs e5-base — Owner: __

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
| Model decision | bakeoff numbers table | G0 | report/evidence/bakeoff.md | [ ] |
| Coverage denominators | catalog/fetched/extracted/verified counts | G1–G3 | report/evidence/coverage.md | [~] catalog=249 captured at G1; fetched/extracted/verified pending G2–G3 |
| Retrieval quality | G4 gold results + θ values | G4 | report/evidence/retrieval.md | [ ] |
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
| 2026-07-27 | **Splitter fixed for the 2 mechanical failure classes** (headings + Roman-numeral case headers) | `is_heading()` now scans every line (colon optional, 30-char cap so the real document «المستندات المشار إليها في البنود…» survives). Re-ingested: exactly the 4 human-flagged phantoms dropped, nothing else. **Precision 74% → 82%.** |
| 2026-07-27 | **SUPERSEDES the entry above:** conjoined-document splitting **adopted** after validation — recall 80% → **90%, G2 PASSES** | The earlier judgement that recall was "mechanically capped at 80%" was **wrong**, and is corrected here. It was right that splitting on «و» *generally* is unsafe (commonest conjunction, also a bound prefix), but wrong to conclude no rule was safe. A rule firing only where «و» directly prefixes a **closed list of document head-nouns** (صورة/وثيقة/بيان/شهادة/إفادة/محضر/تقرير/طلب/نسخة/إقامة) is lexical, not semantic. **Validated before adoption, not after:** it performs exactly **11 splits corpus-wide, all 11 inspected and correct — 8 of them on services no human verified**, which is an effective holdout. Decisive case: on unverified **#11568** it separates «بيان قيد عائلي للمطلقين» from «بيان قيد عائلي لوالدي المطلقة» — which **Ghina had independently verified as two separate documents on the sibling service #11532**, so the rule reproduces a human judgement it was never fitted to. Effect: **recall 80%→90%, precision 82%→81%, 9/180 services touched, +12 documents.** Adopted now because it is cheapest before G4 indexes the corpus. Residual 4 misses are #11464 documents that live in the notes section, not `required_documents_html` — a different change, not attempted. **G2 AUTO PASS + human check complete = G2 FULLY PASSED.** |

## Findings / surprises

- **2026-07-27 — ARABIZI IS MISROUTED AS ENGLISH (found answering Ghina's Job-C question).**
  `detect_language` (FR1) decides on Arabic-vs-Latin letter ratio, so Latin-script Arabic —
  «shu badde la sajjel zawej» — scores 0 Arabic letters and returns `lang="en"`. Measured:
  fosha ✅ ar · Lebanese dialect in Arabic script ✅ ar · **Arabizi ❌ en** · Arabic+English mixed
  ❌ en. Consequence: the agent answers an Arabic speaker in English and then matches Latin text
  against an Arabic corpus — it does not crash, it quietly does the wrong thing. **Arabizi is
  extremely common in Lebanon, so this is a real gap, not a corner case.** Proper fix is
  transliteration detection (not a 2-day item). DECISION: keep Arabizi OUT of the demo questions;
  carry 1–2 Arabizi cases in the eval set as a KNOWN-FAIL and write it up as failure mode #2
  (the brief requires ≥2 analysed modes). Job-C demo questions are therefore specified as Arabic
  script, fosha + Lebanese dialect, with the "messy" case messy IN ARABIC (typos, no punctuation,
  telegraphic) rather than transliterated.

- **2026-07-27 — ⭐ STRUCTURAL: a flat document list cannot represent these services (Maria + Ghina,
  G2 human check, independently raised by both).** The deepest G2 finding is not extraction noise —
  it is a **data-model mismatch**. `CorpusRecord.sections.required_documents` is `list[str]`, but the
  source encodes conditional logic that a flat list destroys. Four constraint types observed:
  (1) **case/branch by applicant type** — #11528 has three cases (minor / adult / outside the legal
  window) behind the I·II·III headings; #11476 branches general / Syrian wife / Palestinian wife,
  each with different documents; (2) **either/or within one requirement** — اقامة صالحة **أو**
  تأشيرة دخول; التعميم 1/84 **أو** قرار قنصلي — one requirement, several valid documents, not
  several mandatory ones; (3) **eligibility preconditions** — #11476 requires the marriage registered
  ≥1 year before applying; (4) **document recency windows differing by case** — Syrian بيان قيد
  <6 months, Palestinian <3 months. **#11476 exhibits all four in one service.**
  Consequence: flattening turns "bring A or B" into "bring A and B", and drops the branch a citizen
  is actually in. **Not fixable by 2026-07-29** — schema change + re-extraction + re-verification.
  DECISION NEEDED: report as a named limitation with #11476 as the worked example (recommended), or
  attempt a `conditional`/`applies_to` field. Note (4) also touches FR6: recency applies to the
  CITIZEN's documents, not only to source freshness — `check_freshness` does not cover it.
- **2026-07-27 — fees missed by the crawl on 3 services (Maria, G2 Part 2 review).** #11476 carries
  **two** fees: 50,000 ل.ل per certified-copy document AND **20,000,000 ل.ل collected only if the
  application is approved** — a large CONDITIONAL fee (this resolves the "20M looks like a digit
  error" query: the amount is real, the conditionality is what was lost). #11528 and #11518 are both
  **لا رسوم (free)** and were left blank. Blank ≠ free: the agent must distinguish "no fee" from
  "fee not published", and currently cannot.

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

- **2026-07-29 (composer wired; merged to main; G0 closed):** Audit found the gap that mattered:
  **the LLM was used in exactly ONE node** (`classify_intent`). `compose` and `research` never
  called the model, so `reasoning` — a field the brief mandates — was a **hardcoded constant
  identical on every answer**, and `composer_v1.md` was 69 lines of dead code. For a project about
  agentic AI the agent was a RAG pipeline with a classifier bolted on the front.
  **Fixed with a strict split: the model writes LANGUAGE, code owns FACTS.** New `Narration`
  schema — the composer emits only `reasoning` + `summary` and never sees a document name, fee,
  office, URL or duration. Rationale: anything the model is asked to reproduce it can also
  corrupt, so the cheapest guarantee against a fabricated document is to never route documents
  through it. **Verified by re-running the whole eval: prose became model-written and
  hallucinations stayed at 0; failure rate unchanged at 36.4%.** `composer_v1.md` narrowed to
  match (MANDATE, CoT, OUTPUT SCHEMA and all four few-shot examples rewritten) — a prompt still
  describing the full answer object would have contradicted its own schema.
  **Latency bounded rather than hoped for:** free-tier calls measured 0.5–12.8 s for identical
  requests and one eval case hit 40 s. Both model calls now have timeouts (6 s classify, 8 s
  narrate) with deterministic fallbacks. **p50 2.55 s → 1.26 s**, mean 10.7 → 6.7 s. Timing out
  classification is safe by construction: `validate_input` already refuses adversarial input
  before any model call. Also caught a latent `TypeError` — the Qwen adapter lacked the `timeout`
  kwarg and would have crashed the moment anyone switched `MODEL_ID`.
  **G0 closed** by Mariam's decision, recorded honestly as producer == reviewer rather than
  attributed to Maria; REPORT §7.7 now names which gates have real independence (G1/G1b/G2/G3) and
  which do not. **Merged `build-graph-g5` → `main`** (fast-forward, 56 files, ~7.9k insertions) and
  verified on `main` afterwards: 64 unit tests, G2/G5/G6/G9 all PASS, secret scan clean.
  **G3 audited precisely** — `core_verification.csv` missing, `document_sources.json` missing
  (seed has 3 rows, 0 with sources), gold has 5 normal cases of the 10 required, `check_g3.py`
  missing. Decision recorded: **do not pad the gold with developer-written cases** — developer
  queries have flattered the numbers twice already.
  Also written: **`VERIFY.md`** (how to check the work, including how to catch me being wrong) and
  **`RUN.md`** (launch A–Z + verified demo prompts), both after a real "localhost refused to
  connect" that turned out to be `streamlit` not being on PATH.
  **Next: G11 demo rehearsal — human-only and the top priority.**

- **2026-07-28 (build day 4 — G4, G6, G9, G8, report; Ali+Gaby's streams absorbed):** Six gates
  moved. **G4** built from two stubs (indexer + hybrid retrieval + dev-only calibration + Wilson
  CI); **G6 PASS 8/8** (live index, live REST, both external calls in trace, `resolve_document`
  and `agents/runtime.py` written); **G9 PASS 5/5** (full Streamlit UI replacing the 8-line stub,
  incl. the A29 escaping criterion); **G8 run** (24 cases, 36.4% failure, 0 hallucinations, p50
  1.56 s, adversarial 6/6); **REPORT.md written, all 8 sections**; `ITERATION_LOG` with 3
  iterations; `VERIFY.md` and `RUN.md` written. Ghina's Job C landed → **core-44** +
  `gold_claims.json` (8 expert-written cases).
  **Bugs found by running the thing, not by reading it:** (1) the intent prompt was never sent —
  `system_prompt` defaulted to `""` — so the model classified with no instructions and refused
  Ghina's own religion-change question; (2) `check_g4` scored abstention on cosine while the live
  node thresholded on RRF, so **the gate passed while the agent refused a valid query** — both now
  share `classify_outcome()`; (3) two working external calls rendered as `None` in the trace, which
  is the demo screen; (4) the encoder defaulted to BGE-M3, which is **not installed** — a plain
  `streamlit run` would have failed on demo day, invisible to me because I always set the env var;
  (5) `streamlit` is not on PATH, producing a "localhost refused to connect" that looked like a
  broken app.
  **Two retractions, both kept in the record rather than quietly corrected:** top-1 "100%" was an
  artefact of a gold set made of bare titles (cos 1.000) → honest 88%; and "recall is mechanically
  capped at 80%" was wrong → a validated conjoined-document rule reached 90% and **G2 FULLY
  PASSED**. Pattern worth carrying into the report and the viva: **every time the test data became
  more independent, measured performance got worse** (3/8 on the experts' own questions vs 88% on
  ours).
  **Next: G11 demo rehearsal (human-only, top priority), G10 repo hygiene, regenerate
  `bakeoff.md` to unblock Maria's G0 sign-off, finish G3's lookup table.**

- **2026-07-27 (splitter fix + conditional detector + G5 PASSED):** Three pieces.
  **(1) Splitter:** `is_heading()` now scans every line with the colon optional and a 30-char cap
  (so the real document «المستندات المشار إليها…» survives) + Roman-numeral case headers.
  Re-ingested 193; exactly the 4 human-flagged phantoms dropped. **Precision 74%→82%**; recall
  stays 80% and is mechanically capped (residual misses are documents conjoined by «و»).
  **(2) Conditional detector** (`tools/conditional_detect.py` + `ConditionalFlag`,
  `conditional_structure` in ReviewReason/QueueEvent, `AnswerOut.conditional_flags`): carries the
  G2 structural finding into every answer — caveat + confidence penalty (capped 0.40) + review
  queue. `either_or` is marked low-confidence (keys on ubiquitous «أو») so it never escalates
  alone. **113/180 (63%) flagged; 46/180 (26%) high-confidence.** Verified #11476 shows all four
  types and drops 0.9→0.30; **#11532, the demo service, shows ZERO flags** (no false positive on
  the demo path). **(3) G5 AUTO PASS** — `agents/graph.py` (14 nodes, 5 terminal branches) +
  `agents/nodes/*` + `tools/{duration,rrf,review_queue}.py`; every dependency defaults to None so
  the graph runs with no key, no network, no index. **64 unit tests green; `check_g5.py` 9/9.**
  The tests caught 2 real bugs before they shipped: `_BRANCH` missing `re.M` (Roman-numeral
  branches invisible on multi-line text) and `review_queue` re-opening a portalocker-held file
  (PermissionError under Windows mandatory locks). **Next: G6 needs Ali's index; report §§1–3 can
  start now.**

- **2026-07-26 (non-technical onboarding for Maria & Ghina):** Wrote `docs/GUIDE_MARIA_GHINA.md` —
  A-to-Z guide for the two domain experts, deliberately **excluding** the Python/venv setup (their
  three jobs need a browser and a text file; a 500 MB torch install for a read-Arabic-pages task is
  bad ROI at T-3 days). Covers: repo access, the 4 files that matter, VPN-off rule, the
  passport/licence-absent + 3-of-22-ministries context, the three jobs (G0 Arabic sign-off; G2
  extraction check; G3 core-40 rebuild), reviewer≠producer, and three no-friction ways to hand work
  back. Generated **per-person** worksheets `report/evidence/g2_worksheet_{maria,ghina}.md` — the 8
  `spike_gold.json` services rendered as fill-in-the-blanks (machine documents numbered, verdict
  blanks OK/WRONG/NOT A DOCUMENT/SPLIT, MISSING section, fees/where-to-apply for the 3 deep ones) so
  neither expert has to touch JSON; Mariam transcribes answers back into `spike_gold.json`.
  **G2 split** (balanced on effort — a field-by-field doc ≈ 3× a skim doc, so 15 docs/2 deep vs
  28 docs/1 deep is roughly even): Maria 11464 + 11554 (deep) + 11704 + 11674; Ghina 11532 (deep) +
  11528 + 11476 + 11518. Each file has a Part 2 review block for the other's four → reviewer ≠
  producer satisfied within the pair. **G3 split by procedure family:** Maria = person records
  (هوية/ولادة/وفاة/جنسية, 16 rows), Ghina = relationship + register records (زواج/طلاق/بيان قيد,
  22 rows, incl. 8 near-identical وثيقة زواج variants); 4 demo questions each, one deliberately
  messy. Two specific bugs flagged for hunting: doc 2 of #11464 has a stray `3.` mid-sentence
  (likely a merged pair), and #11674 extracted zero documents. **Found a blocker for G0: the bakeoff's 5 Arabic outputs were never persisted**
  (`check_g0.py` writes only aggregate counts to `model_limits.json`; `report/evidence/bakeoff.md`
  does not exist) — Maria's sign-off is un-doable until Mariam re-runs it capturing per-fixture
  output. Logged in the pending-checks queue. Jobs B and C are unblocked and can start now.
- **2026-07-25 (G1b enhancements + handoff prep):** Mariam signed off G1 (5 URLs) and G1b (contacts
  live-review). Per her review, added two contact enhancements: `opening_hours` captured (23
  ministries) + Useful-Numbers hotlines joined to ministries (6 gained a phone; no false matches).
  Decided AGAINST scraping other government sites (fragile, dilutes single-source thesis, low ROI) —
  Dawlati's own data provided both. Refreshed CLAUDE.md + this "CURRENT STATE" block for a clean
  new-chat handoff. **Next: core-40 rebuild + G2 field-check (Maria/Ghina); BUILD-track G5.**
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
