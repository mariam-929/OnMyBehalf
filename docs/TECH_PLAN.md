# TECH_PLAN.md — Dawlati Agent: Tech Stack & Implementation Plan (v3, 2026-07-25)

v3 folds review 2 (A01–A30; `RESOLUTIONS.md`). Primary-source verification is mandatory before
any code depends on a capability (the A01 lesson). Deadline confirmed: Wed 2026-07-29. Contracts:
`SCHEMA_AND_CONTRACTS.md`. Prompts: `prompts/*_v1.md`.

## 0. Methodology
Constraints → primary-source verification → scoring → rejected alts. Any capability claim >7 days
old is re-verified before code depends on it.

## 1. Stack (v3 changes marked ►)

| Layer | Choice | Notes |
|---|---|---|
| Runtime | LangGraph 1.2.x + pinned langgraph-prebuilt | node timeout async-only → HTTP timeouts in code |
| LLM | **G0 bakeoff, per-model adapters** (A01) | see §1.2 — models are NOT drop-in |
| Structured output | ► **model-dependent** (A01, verified) | GPT-OSS: strict `json_schema`. Qwen3.6: **JSON Object Mode only** → Pydantic retry is load-bearing |
| Reasoning | ► model-dependent (A01) | Qwen: `reasoning_effort none/default` + `reasoning_format parsed`. GPT-OSS: `reasoning_effort low/med/high` + `include_reasoning` |
| Embeddings | bge-m3 local; fallback e5-base | arXiv 2402.03216; Arabic study 2506.06339 |
| Vector store | Chroma persistent | metadata filter drives core-gating |
| Retrieval | BM25(titles)+dense, RRF k=60; θ on DEV set, gate on HOLDOUT (A12) | |
| Contacts | ► `/en/directory` Playwright crawl → local ContactRecord (A06/A27) | REST has no contact fields (verified) |
| 2nd external call | ► `live_service_lookup` (REST `?search=`) (A06) | verified live; replaces get_contacts |
| Schema | Pydantic v2 discriminated union = `agents/models.py` (A07) | single source; complete in SCHEMA_AND_CONTRACTS.md |
| Queue | ► append-only JSONL + `portalocker` (A09) | nullable subject; dedupe |
| UI | Streamlit + RTL + ► HTML-escape all dynamic text (A29) + `--offline` emergency only (A15) | |
| Observability | local JSONL only | LangSmith cut |
| Lang detect | char-ratio, alphabetic denominator, ≥0.30 | classifier advisory |

### 1.2 G0 bakeoff + per-model adapters (A01, A05, A30 — verified 2026-07-25)
Both candidates share 30 RPM / 8K TPM / 1K RPD free tier (verified — note: **8K TPM, not the old
6K**). But capabilities differ, so G0 tests each through a **model-specific adapter**:
- `GptOssAdapter`: `response_format={"type":"json_schema","strict":true}`, `reasoning_effort`
  low/medium, `include_reasoning`. Expect guaranteed schema.
- `Qwen36Adapter`: `response_format={"type":"json_object"}` + **Pydantic validate + one repair
  retry** (no strict mode); `reasoning_effort default`, `reasoning_format parsed`. Note Preview.
Fixture (~1.5 h): 10 prompts (5 AR/5 EN) at the REAL discriminated schema + 2 tool-call fixtures.
Measure per model: schema-valid rate (≥9/10), Arabic fluency (human), p50 latency (≤10 s),
tool-call correctness, actual limits/headers → `data/model_limits.json`. **Bootstrap (A05):** the
schema + adapter fixture module (`agents/models.py` + `agents/adapters.py`) is an EXPLICIT
permitted G0 artifact; the production schema must equal the tested fixture. Winner → `MODEL_ID`,
**exact id pinned**. Tie/close → prefer GPT-OSS (strict schema + not Preview + granular reasoning).

### 1.4 Crawler (spike-first)
REST enumerate (249) → admin-ajax probe (1 h) → **10-page spike, save `data/spike_gold.json`,
score recall on documents+fees+authority+location+time (A13)** → full crawl (concurrency 3, 1 s,
retry ×2). Separately crawl `/en/directory` → ContactRecord store.

## 2. Repo layout (additions)
`agents/models.py` (=SCHEMA_AND_CONTRACTS), `agents/adapters.py` (per-model), `tools/live_service_lookup.py`,
`tools/enrich_contacts.py` (local), `tools/crawler/fetch_directory.py`, `tests/gold_claims.json`,
`data/spike_gold.json`, `data/review_queue.jsonl`, `report/evidence/`, `prompts/*_v1.md`.

## 3. Data contracts
All in `SCHEMA_AND_CONTRACTS.md` (A07). Producer→consumer chain closed there incl. ContactRecord
(A27), nullable-subject QueueEvent (A09), Duration units (A10), ResolvedDocument abstention (A11),
FreshnessResult change-status (A08). No stage passes untyped dicts.

## 4. Agent graph
- `retrieve`: RRF; abstain < θ_abs (no exact-title hit) ; clarify if margin < θ_amb (DEV-calibrated).
- `research`: bounded (A02) — 1 plan → batched deterministic execute → ≤1 replan → stop; ≤2 model
  calls + ≤8 tool calls; 5 s per tool. Prompt: research_agent_v1.
- `check_freshness`/`live_service_lookup`: `requests` 5 s timeout, browser UA; try/except →
  unverified. In an async node use `asyncio.to_thread`.
- `resolve_document`: normalize → dense+BM25 → θ_doc gate → abstain (A11).
- `compose`: adapter-appropriate structured output + CoT; SCHEMA_AND_CONTRACTS answer object.
- Duration aggregation per FR5/A10 (same-unit only; else component-wise, computable=false).
- Provider outage: Groq fail after backoff → `error`; UI retry; demo `--offline` emergency.

## 5. Rate limits & latency (A02, A28)
Real limits at G0 → `model_limits.json`. Bounded loop keeps a query within budget: plan(~1K) +
compose(~4K) + reasoning ≈ within 8K TPM/min; eval spacing = `ceil(tokens/TPM·60)+margin`.
Report **mean+p50+p95+max user-visible latency incl. waits**; ex-backoff separate/diagnostic.

## 6. Streamlit
RTL wrapper with `html.escape` on ALL dynamic text; links only from validated http(s) URLs (A29);
`--offline` loads `report/evidence/demo_cache/*.json` behind an EMERGENCY banner (A15); sidebar:
model id, snapshot date, coverage + contact-coverage.

## 7. Evaluation
Oracle = `gold_claims.json` factual values (A03); DEV/HOLDOUT split for retrieval (A12); all-24
manual audit; two captured failure records (A18); mean+p50+p95+max latency (A28).

## 8. Dev env
`.env` = GROQ_API_KEY + MODEL_ID; exact `==` pins after G0. `portalocker` for queue.

## 9. Schedule (resource-aware critical path — A04, A21, A22)

Single laptop = the constraint for COMPUTE tasks (bakeoff, crawl, index) → these are SERIAL on the
laptop. WRITING tasks (schema, prompts, graph code, report) parallelize across PEOPLE. Assign
owners before G0 (names → PROGRESS). Human gates need a named reviewer ≠ producer.

- **Jul 25 (today):** G0 — env + per-model bakeoff (laptop, serial) + **synthetic G5 fixtures made
  here (A22)** + competitor 5-query comparison started (A25). Draft prompts already done.
- **Jul 26:** [laptop, serial] enumerate→spike(save spike_gold)→crawl→directory crawl→index→G4
  calibration. [people, parallel, on fixtures] models.py+adapters→graph skeleton+validate/detect+
  unit tests→G5 (uses synthetic fixtures, NOT blocked on crawl — A22).
- **Jul 27:** retrieve+bounded research loop+compose on real index; freshness+live_lookup+queue;
  smoke G6 (gold case + 2 ext calls + observation-driven branch); ITERATION_LOG; UI shell+RTL.
- **Jul 28:** 24-case eval + gold (G8); prompt iterations; UI + escaping + offline; core_verification
  finished (team-split); all-lookup-rows source-checked (A24); evidence sweep; report §§1–4.
- **Jul 29:** report PDF; repo + secret scan + README + video (G10); rehearsal ×2 + separate
  source-outage vs provider-outage drills (A14/G11); SUBMIT.
Contingency reserve stated per day; slip → SCOPE §15 cut order.

## 10. Risks
Per-model adapter divergence (A01); Qwen Preview instability (A30); contacts thin (verified);
crawl extraction unknown until spike (A13); bounded loop must still show real re-plan (A26 gate).

## 11. Sources (verified 2026-07-25)
- Groq structured outputs (GPT-OSS strict only; Qwen JSON-object): console.groq.com/docs/structured-outputs
- Groq reasoning (per-model params): console.groq.com/docs/reasoning
- Groq rate limits (8K TPM): console.groq.com/docs/rate-limits
- Qwen3.6-27b Preview + caps: console.groq.com/docs/model/qwen/qwen3.6-27b
- Dawlati REST live checks (search + modified_gmt; contacts NOT in REST): verified by direct API calls
- LangGraph fault tolerance (async-only timeouts): docs.langchain.com/oss/python/langgraph/fault-tolerance
- Embeddings: arxiv.org/abs/2402.03216, arxiv.org/abs/2506.06339
