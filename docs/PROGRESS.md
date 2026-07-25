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
195+24+30 = **249 exact**, denominators captured to `report/evidence/coverage.md` (pending Gaby's
5-URL check). Second dev env (Ali) up on Python 3.13. Known gotcha: **Dawlati Cloudflare 403s VPN
IPs** — see Findings. **Next action: DATA track — admin-ajax probe (1 h box) → 10-page spike +
`data/spike_gold.json` → field-recall scoring → G2**; BUILD track (graph skeleton on synthetic
fixtures) can start in parallel. Deadline Wed 2026-07-29 (written).

## Gate record (AUTHORITATIVE — defs in `VERIFICATION.md` v3; no step starts before upstream gates
## PASS; Claude runs auto checks but may NOT fill "Human sign-off")

| Gate | What | Status | Date | Evidence | Human sign-off |
|---|---|---|---|---|---|
| G0 | Env + **per-model bakeoff** + synthetic fixtures (blocks all code) | AUTO PASS | 2026-07-25 | gpt-oss-120b 10/10@0.55s vs qwen3.6 9/10@1.38s; data/model_limits.json | **PENDING: Maria** confirms Arabic |
| G1 | Service catalog (249 posts) | AUTO PASS | 2026-07-25 | data/catalog.json — 195+24+30=249 exact, 0 dup ids, all modified_gmt | **PENDING: Gaby** opens 5 URLs |
| G1b | Contact catalog (/en/directory crawl) | NOT RUN | — | — | — |
| G2 | Corpus quality (spike-gated, multi-field) | NOT RUN | — | — | — |
| G3 | Reference data verified (40-row sheet) | NOT RUN | — | — | — |
| G4 | Retrieval calibrated (top-1 + abstention) | NOT RUN | — | — | — |
| G5 | Graph skeleton (BUILD track, fixtures) | NOT RUN | — | — | n/a |
| G6 | Agent end-to-end (gold + 2 ext calls) | NOT RUN | — | — | — |
| G7 | Freshness & HITL | NOT RUN | — | — | — |
| G8 | Eval (claim-level gold, 24-answer audit) | NOT RUN | — | — | — |
| G9 | UI demo-ready (RTL + offline) | NOT RUN | — | — | — |
| G10 | Repo & report compliant | NOT RUN | — | — | — |
| G11 | Demo readiness (human-only) | NOT RUN | — | — | — |

**Pending human checks queue:**
- **G0 — Maria:** review the 5 Arabic inputs → intent classifications from `gpt-oss-120b` in the
  bakeoff output (all 5 classified correctly: 4 service_query + 1 invalid_request for the
  injection). Confirm the model handles Arabic correctly and bless `openai/gpt-oss-120b` as the
  winner. Then G0 is fully signed off. (Auto part already PASS.)
- **G1 — Gaby:** open these 5 catalog URLs in a browser; confirm each loads and its Arabic title
  matches `data/catalog.json`. Then G1 is fully signed off. (Auto part already PASS.)
  1. `/ministry_service_ser/…` إصدار شهادات صحية لتصدير الحيوانات أو المشتقات الحيوانية
  2. `/en/useful-numbers-post/ogero/` Ogero
  3. `/ministry_service_ser/…` رخصة رعي في الغابات
  4. `/ministry_service_ser/…` إعطاء رخصة صيد الأسماك البحرية (بواسطة مركب)
  5. `/ministry_service_ser/…` تصحيح أو إضافة اسم على لوائح الشطب
  (full URLs in `report/evidence/coverage.md`) — **VPN must be OFF, see Findings.**

## Owners (team: Gaby, Mariam, Ali, Ghina, Maria; procedure/Arabic experts = Maria + Ghina)
Gate task owner + independent reviewer (reviewer ≠ producer). Adjust freely — these are proposed
by load-balance + domain fit, not fixed. Individual checklist tasks follow their gate's owner
unless a member picks one up.

| Gate | Owner | Reviewer | Rationale |
|---|---|---|---|
| G0 bakeoff | Gaby | Maria | Maria reads the 5 Arabic outputs to bless the winner |
| G1 catalog | Ali | Gaby | |
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
- [ ] **PENDING human: Maria** confirms Arabic classifications → G0 fully signed off
- [ ] freeze `==` pins via `pip freeze` (after Maria signs off)
- [x] venv (outside OneDrive) + deps installed + Playwright chromium

### DATA track (Jul 26)
- [x] `enumerate.py` → `data/catalog.json` (249: 195+24+30 — **exact**) → G1 AUTO PASS — Owner: **Ali**
      (pending Gaby's 5-URL human check)
- [ ] admin-ajax probe (1 h box) → DECISION under Decisions — Owner: __
- [ ] 10-page spike + field-recall scoring → G2 spike gate (≥80% or 40-core fallback) — Owner: __
- [ ] full crawl → `extract.py` → `data/corpus/*.json` — Owner: __
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
| Contact coverage (A27) | authorities-with-contact count | G1b | report/evidence/contacts_coverage.md | [ ] |
| Spike ground truth (A13) | per-field annotations, 10 pages | G2 | data/spike_gold.json | [ ] |

## Decisions made mid-implementation (append)

| Date | Decision | Why |
|---|---|---|
| 2026-07-25 | Docs v1→v2 after adversarial review; RESOLUTIONS.md records all 43 dispositions | ~30 findings valid incl. 2 verified blockers (F01 model retirement, F02 freshness) |
| 2026-07-25 | Docs v2→v3 after 2nd review (A01–A30) | ~26 valid; per-model adapters, bounded loop, gold-oracle split |
| 2026-07-25 | **get_contacts → live_service_lookup** | LIVE test: Dawlati REST exposes no contact fields; REST `?search=` verified as the 2nd external call |
| 2026-07-25 | Freshness labels → unchanged/changed/unverified | modified_gmt detects source change, not currency (A08) — honest semantics |
| 2026-07-25 | **MODEL_ID = openai/gpt-oss-120b** (G0 bakeoff winner; owner Mariam) | 10/10 schema-valid @0.55s p50 vs qwen3.6 9/10 @1.38s (1 json_validate_failed, Preview). GPT-OSS: strict schema, 2.5× faster, not Preview. Both 8K TPM. Also fixed adapter (strict `additionalProperties`) + UTF-8 console. |

## Findings / surprises

- **2026-07-25 — Dawlati Cloudflare 403s VPN/datacenter IPs (Ali, env setup).** Every dawlati.gov.lb
  path — REST endpoints AND the plain homepage — returned `403 / server: cloudflare` ("Attention
  Required!") from `requests`, `curl`, and real headless Chromium alike, while other sites (incl.
  other Cloudflare-fronted ones) returned 200. Cause was a **VPN connection**, not the User-Agent,
  the code, or the network. VPN off → 200 on all three post types immediately. **If any Dawlati call
   403s, check the VPN before debugging the code.** (The browser-UA header in `enumerate.py` is still
  required — Cloudflare also 403s default clients — so both conditions must hold.)
- (nothing else from implementation yet — the F01 model retirement was caught by review, pre-code)

## Blockers

- **NONE blocking G0.** Owners assigned (table above; team confirmed: Gaby, Mariam, Ali, Ghina,
  Maria; experts Maria+Ghina). Groq key created by Mariam (stored in a local txt OUTSIDE the repo;
  goes into `.env` at scaffold, gitignored).
- Bakeoff winner's Arabic quality and crawl extraction quality unknown until G0/G2 (measured, not
  assumed) — expected, not a blocker.

## Session log (newest first)

- **2026-07-25 (Ali — env setup + G1 catalog):** Second dev environment stood up (venv
  `~/venvs/OnMyBehalf` on **Python 3.13**, outside OneDrive; 3.14 is too new for chromadb/torch
  wheels and the 3.10 on PATH is the Store build). All deps + Playwright chromium installed; imports
  and `agents.models`/`agents.adapters` clean; `check_g0.py` runs and stops correctly at the missing
  key (key not yet copied from Mariam — not a blocker for the DATA track). **Hit a hard Cloudflare
  403 on every Dawlati path — cause was a VPN connection, not code/UA (logged under Findings).**
  VPN off → **G1 run: `enumerate.py` → `data/catalog.json`, 195+24+30 = 249 exact**, 0 dup ids, all
  rows carry modified_gmt/title/https url → **G1 AUTO PASS**; denominators captured to
  `report/evidence/coverage.md`. Pending human: Gaby opens the 5 sampled URLs.
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
