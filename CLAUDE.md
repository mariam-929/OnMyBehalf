# OnMyBehalf — MSBA 316 Final Project (agentic AI for Lebanese government procedures)

> **▶ NEW SESSION START HERE:** read **`docs/PROGRESS.md` → the "CURRENT STATE" block at the top** —
> it is the single source of truth for exactly where the project is (gates done, next actions, key
> facts). Then follow the Session protocol below. Do NOT re-derive state from scratch or re-read the
> whole history. Env is already set up: run Python with
> `C:\Users\Mariam\venvs\OnMyBehalf\Scripts\python.exe` (venv is OUTSIDE OneDrive); Groq key is in
> `.env` (gitignored). Repo: github.com/mariam-929/OnMyBehalf.
>
> **As of 2026-07-28 (build day 4 done) — THE SYSTEM WORKS END TO END.** UI → agent → live Dawlati
> REST → cited answer. **PASSED: G1, G1b, G2, G5, G6, G9.** Partial: G3 (core-44 + gold done,
> lookup table missing), G4 (2/4, left failing on purpose), G7, G8 (run: 36.4% failure, 0
> hallucinations), G10 (REPORT.md written). **Not started: G11 demo — human-only and the top
> priority.** Branch `build-graph-g5`, pushed. Full detail + all gotchas in `docs/PROGRESS.md` →
> CURRENT STATE.
>
> **Four traps that cost real time this week:**
> 1. **VPN OFF** for dawlati.gov.lb — otherwise every answer silently reads `freshness: unverified`.
> 2. Launch the UI as `python.exe -m streamlit run …` — bare `streamlit run` fails because it is
>    not on PATH, which reads as "localhost refused to connect".
> 3. `data/` is gitignored — a fresh clone has no corpus and no index until you rebuild.
> 4. Encoder is **LaBSE** (BGE-M3 never downloaded). Rebuild the index if you change it.
>
> **Team: Ali and Gaby are out** (2026-07-28); their streams were absorbed. Maria and Ghina
> delivered in full — their verification is the backbone of G2/G3. The technical gates therefore
> have **no independent reviewer**; those sign-offs are recorded as producer self-checks, never
> filled in.
>
> **Orientation:** `VERIFY.md` (how to check the work) → `RUN.md` (launch + verified demo prompts)
> → `report/REPORT.md` → `prompts/ITERATION_LOG.md`.

Team: Gaby, Mariam, Ali, Ghina, Maria. This repo is the single home for code + plan. Human
teammates: start at `CONTRIBUTING.md` then `SETUP.md`. The `docs/` folder is the authoritative plan.

## What this project is

Course project for MSBA 316 (Text Analytics & NLP, AUB, Summer 2025/26, Dr. Ahmad El-Hajj).
Course brief: on Moodle (`MSBA316_Project_Summer_2025_2026.pdf`) — not in this public repo; read it
before making grading-relevant decisions.
**Authoritative docs (all at v3 after THREE adversarial reviews — read them, don't work from this
summary alone): `docs/SCOPE.md` (locked spec), `docs/SCHEMA_AND_CONTRACTS.md` (complete Pydantic
schema + typed pipeline contracts + gold-oracle — the single data-shape source), `docs/TECH_PLAN.md`
(stack + implementation, primary-source-verified), `docs/VERIFICATION.md` (gates G0–G11, G1b),
`prompts/*_v1.md` (the 3 drafted prompts), `docs/RESOLUTIONS.md` (per-finding dispositions
F01–F43, A01–A30, N1–N6; raw reviews in `docs/reviews/`), `report/AI_LOG.md` (mandatory AI-usage
log — keep current every session). Build against these; don't reopen their decisions silently.**

**⚠ Session protocol — `docs/PROGRESS.md` is the live status log:**
1. **Start of session:** read PROGRESS.md ("Where we are" + the checklist) before doing anything
   else; don't re-derive state from scratch.
2. **During work:** tick checklist items; record unplanned decisions in its Decisions table and
   surprises under Findings; capture report/demo artifacts into the Evidence register.
3. **Before ending any working session:** update "Where we are", the checkboxes/gate record, and
   append a dated Session-log entry. An out-of-date PROGRESS.md breaks the next session — treat
   updating it as part of the task, not optional.
4. **Stage gates are blocking** — `docs/VERIFICATION.md` defines gates G0–G11 (+G1b) with an
   automated check + a human check each. Do not start a step whose upstream gate isn't PASS in
   PROGRESS.md's Gate record. Claude runs the automated checks (`tests/gates/check_g{N}.py`) and
   records results, but **must never fill in or fake a human sign-off** — when a human check is due,
   add it to the "Pending human checks queue" in PROGRESS.md, tell the user exactly what to verify
   and how, and work only on non-dependent tasks until it's signed off. Gate failure → fix and
   re-run, or invoke the documented fallback and record it under Decisions.

**One-sentence pitch:** Given a citizen's request about a Lebanese government transaction (passport,
ID, civil extract, permits, …), the agent returns a structured checklist of required documents,
**where to obtain each document**, fees, where to apply, and a source-cited time estimate — with a
confidence heuristic and a human-review flag when sources are changed or unverifiable.

Data source: **Dawlati**, Lebanon's national public-services portal — https://dawlati.gov.lb (OMSAR).
Stakeholder: citizens; system owner: OMSAR content ops (owns the review queue).

## Deadline
- **Due Wednesday July 29, 2026 — confirmed in writing.** Sprint Jul 25 (G0) → Jul 29.
- Presentations week of Jul 27+: 8-min live demo + 4-min Q&A. Group of 5.

## Hard requirements from the brief (grading-relevant)
- Agent: reasoning loop (perceive→plan→act→observe), **≥2 external tool calls**, **structured JSON
  output** (`action`, `reasoning`, `output`, `confidence`), documented failure analysis.
- System prompt: role, mandate, tool list, **negative constraints**, output schema.
- CoT where multi-step (documented); **≥1 component uses few-shot with ≥2 examples**.
- **≥20 test cases** (normal/edge/adversarial); report failure rate, hallucination count, **avg latency**.
- **Iteration log with failure analysis for ≥3 prompts.** ≥2 failure modes analyzed.
- Grading: Report 55% (8 sections), Demo/Q&A 35%, Repo 10%.
- Demo: one live end-to-end run, a tool call visible in a trace, **one failure case handled**, a
  system prompt on screen.
- Repo (public, **no live keys**): `/agents /prompts /tools /tests /data README requirements.txt .env.example`.
- **AI-usage appendix mandatory** (`report/AI_LOG.md`) — Task/Prompt/Response/Implementation/Modifications.

## Architecture & stack (full rationale in docs/TECH_PLAN.md §1)
- **LangGraph 1.2.x** stateful loop (visible in traces). Node `timeout` is async-only → HTTP timeouts in code (F33).
- **LLM: G0 bakeoff — `qwen/qwen3.6-27b` vs `openai/gpt-oss-120b` on Groq.** ⚠ v1 picks (qwen3-32b,
  llama-4-scout) were **retired for free tier 2026-07-17** — verify model claims at
  console.groq.com/docs/deprecations, never third-party articles (F01, A01).
- **Structured output/reasoning is PER-MODEL (A01, verified):** GPT-OSS = strict `json_schema`;
  Qwen3.6 = JSON Object Mode only (Pydantic retry load-bearing). Each tested via its own adapter
  (`agents/adapters.py`). Qwen3.6 is Preview → prefer GPT-OSS on a close bakeoff (A30).
- **Chroma** + **BGE-M3** local embeddings; hybrid BM25+dense fused by **RRF** (F10, A12).
- **Tools (4, ≥2 external):** `search_services` (local), `resolve_document` (local),
  `check_freshness` (external — REST `modified_gmt`), **`live_service_lookup`** (external — REST
  `?search=`). `get_contacts` REPLACED (A06/A27): contacts are NOT in Dawlati REST (verified) →
  local `/en/directory` crawl, best-effort, not an external call. Research loop is BOUNDED (A02):
  1 plan → batched execute → ≤1 re-plan → compose; per-document freshness is a deterministic SYSTEM
  step (N3). **Tavily CUT; LangSmith CUT** (local JSONL traces keep the privacy claim true — F22).

## Freshness / HITL (F02, A08)
`check_freshness(post_id)` compares live REST `modified_gmt` vs the value stored at crawl time →
`unchanged | changed | unverified` (change-detection, NOT currency). Recrawl-diff uses ONE canonical
`fetch→render→extract→normalize→sha256` (never raw HTML). Both feed one append-only `review_queue.jsonl`
(`QueueEvent` schema); OMSAR content ops is the owner. Daily-cron + reviewer-UI = report §7 (design-only).

## Dawlati recon (verified 2026-07-24/25)
- Cloudflare 403s default clients → **browser User-Agent required**.
- Public WP REST API `…/wp-json/wp/v2/`: `ministry_service_ser` (195), `services` (24),
  `useful-numbers-post` (30), `ministires` (52), etc. Mostly Arabic.
- Service DETAIL (documents/fees/steps) NOT in REST (JS-rendered) → Playwright. **Contacts also NOT
  in REST** (verified — acf empty, no ajax route) → `/en/directory` Playwright crawl.
- Live REST `?search=` works + per-record `modified_gmt` returns 200 (basis for the 2 external tools).
- `portal.dawlati.gov.lb` login-walled — out of scope. Dawlati has an "OMSAR Assistant" chatbot →
  differentiate (structured/citable/HITL vs generic Q&A). robots `ai-train=no` → retrieval-with-attribution only.

## Scope (do not silently reopen; detail in docs/SCOPE.md §§6,11,15)
IN: 249 catalog / 219 service pages (frozen), 40 verified core; resolver + lookup table; REST
freshness + review queue; discriminated JSON; 24 tests + claim-level gold; AR+EN + RTL; `--offline` demo.
OUT: Tavily/open-web (cut); LangSmith cloud (cut); get_contacts-via-REST (not available); wait-time
prediction; portal.dawlati; geocoding; daily scheduler (design-only); French; depth-2 resolution.
Adversarial (legal/bribery/non-LB/PII/injection) → `invalid_request`.

## Sprint plan (detail + owners in docs/TECH_PLAN.md §9 / docs/PROGRESS.md)
Jul 25 G0 (env + bakeoff + synthetic fixtures) → Jul 26 DATA (enumerate→spike→crawl→verify→index→G4)
∥ BUILD (models→prompts→graph→G5 on fixtures) → Jul 27 wire real index + freshness/queue + UI shell
→ Jul 28 24-case eval (G8) + prompt iterations + UI/offline + competitor + evidence + report §§1–4
→ Jul 29 report PDF + repo + secret scan + video + outage drills (G11) + SUBMIT. Capture evidence DURING the build.

## Environment
**`SETUP.md` is the end-to-end setup guide.** **KEEP IT CURRENT: adding/removing a dependency →
update `requirements.txt` AND SETUP.md's Dependencies table in the SAME commit** (SETUP.md §8). Venv
lives OUTSIDE OneDrive (sync locks) — default `%USERPROFILE%\venvs\OnMyBehalf`; the machine's
Microsoft-Store Python redirects `AppData\Local`, so never put the venv there. Launch:
`streamlit run app/streamlit_app.py`.

## Working conventions
- Scratch/temp files go outside OneDrive (it syncs everything; venv/Chroma/logs are gitignored).
- Corpus snapshots = anonymised sample data under `/data/`.
- Never commit API keys; `.env` is gitignored; keep `.env.example` current.
- Arabic I/O in UTF-8 (`PYTHONIOENCODING=utf-8` on Windows).
