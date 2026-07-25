# SCOPE.md — Dawlati Agent: Locked Scope & Requirements (v3, 2026-07-25)

v3 folds the second adversarial review (A01–A30; dispositions in `RESOLUTIONS.md`). Concrete
contracts live in `SCHEMA_AND_CONTRACTS.md`; prompts in `prompts/*_v1.md`; eval oracle in
`tests/gold_claims.seed.json`. Companions: `../CLAUDE.md`, `TECH_PLAN.md`, `VERIFICATION.md`,
`PROGRESS.md`. Empirical items (contacts, crawl, bakeoff) stay OPEN until their artifact/gate
exists — prose does not close them.

## 1. Product definition

**One sentence:** Given a citizen's question about a Lebanese government transaction, the agent
returns a verified checklist of required documents — with where to obtain each one — plus fees,
authority, where to apply, best-effort contacts, and a source-cited time estimate, in the user's
language (AR/EN), flagging every claim it cannot verify for human review.

- **Users:** citizens/residents. **System owner:** OMSAR content operations (owns the review queue).
- **Decisions enabled:** citizen — "am I ready to visit, with what?"; OMSAR — "which content needs review?"
- Out-of-scope input → `invalid_request`, never a guess.

**Impact & success (A19 — ROI restored, all figures LABELED team assumptions; no public LB data found):**
- Assumption: 2–3 visits/transaction; ~4 h lost per failed visit.
- ROI sketch (report §1/§7): `hours_saved ≈ queries × p(avoided_failed_visit) × 4h`; sensitivity
  band over p∈{0.1,0.3,0.5}; cost = free-tier LLM + one part-time OMSAR reviewer. Explicitly
  illustrative, not measured causal impact.
- Prototype success (measured, §8): ≥90% curated-core queries → complete correctly-sourced
  checklist vs gold; 0 core hallucinations; mean + p50 + p95 latency reported.
- Competitor evidence (A25 — done BEFORE build, at G0/G1, not Jul 28): 5-query comparison vs the
  OMSAR Assistant widget; pitch frozen around OBSERVED gaps.

## 2. Functional requirements

- **FR1 (language, A-carry):** one authoritative detector = Arabic-script chars / alphabetic chars
  ≥0.30 → `ar` else `en`; no alphabetic chars → gibberish → invalid. Classifier's
  `language_advisory` never overrides it.
- **FR2 (identification):** RRF-fused BM25+dense. Outcomes: *found* (clear top-1); *ambiguous* →
  `clarification_needed` (≤3 candidates) when RRF margin(top1,top2) < θ_amb OR query names ≥2
  services; *not found* → `service_not_found` (3 suggestions) below θ_abs. θ calibrated on a
  DEV set separate from the holdout gold (A12).
- **FR3 (facts):** documents, fees, authority, location, stated time — each with source_url;
  absent → null, never invented.
- **FR4 (resolution, A11):** per document: normalize (strip diacritics/tatweel, unify alef/ya,
  collapse ws) → corpus dense+BM25 match → lookup-table match → unresolved. **Match must clear
  θ_doc (calibrated at G3); below θ_doc OR two candidates within a tie band → `unresolved` +
  review flag (abstain, never attach a doubtful source).** Depth 1.
- **FR5 (time, A10):** `Duration{min,max,unit}` where unit ∈ business_days|calendar_days|weeks|
  months|unknown. **No cross-unit arithmetic.** Aggregate only same-unit durations:
  parallel docs → `max(d_i)+service`; sequential worst case → `Σd_i+service`; unknown/mixed units
  → `time_estimate.computable=false`, present component-wise breakdown, no single total. Never
  invent wait times.
- **FR6 (freshness, A08 — honest semantics):** `check_freshness(post_id)` compares live Dawlati
  REST `modified_gmt` (VERIFIED present + 200) vs `modified_gmt_at_crawl`. Status ∈
  **`unchanged | changed | unverified`** (renamed from fresh/stale — it detects *source change*,
  not substantive currency; output + report disclose this). 5 s HTTP timeout in code (not a
  LangGraph node timeout — async-only). unreachable/non-200 → `unverified` + snapshot-date caveat.
  `changed`/`unverified` → review flag + QueueEvent.
- **FR6b (per-source, A08):** the check runs for the service AND each corpus-resolved document.
  Lookup-table rows carry `verified_on`; **TTL 180 days** → older ⇒ treated as `unverified`.
  Answer-level freshness = worst across all cited sources.
- **FR7 (confidence, A23):** field name kept (**brief mandates `confidence: float`**); it is an
  **evidence-quality heuristic, not a calibrated probability** — disclosed in a `caveats` line and
  the report. Formula: `0.9(core)|0.5(non-core) − 0.2·(freshness≠unchanged) − 0.1·(any unresolved)
  − 0.3·(incomplete record) − 0.1·(ambiguity near threshold)`, floor 0.05.
- **FR8 (refusals):** legal/bribery/non-LB/PII/injection → `invalid_request`, no tool calls.
- **FR9 (schema):** every LLM output Pydantic-validated (SCHEMA_AND_CONTRACTS). GPT-OSS →
  strict json_schema; **Qwen → JSON Object Mode + retry-once-then-error (A01: Qwen has NO strict
  mode, so the Pydantic retry is load-bearing, not defense-in-depth).**
- **FR10 (UI, A29):** Streamlit chat; AR answers render RTL; **all dynamic text HTML-escaped, links
  only from validated http(s) URLs** (injection/render safety); trace panel; raw-JSON expander.
  A **genuine live query path is the primary demo (A15)**; `--offline` cached mode is EMERGENCY
  fallback only, behind a "CACHED — EMERGENCY MODE" banner, never presented as the live task.
- **FR11 (follow-ups):** `follow_up` needs `session.service_record`; absent → clarification. User
  may declare held documents → recompute FR5 over the rest. Never infer facts it cannot know.
- **FR12 (incomplete records):** `required_documents` extraction failed → `record_status=incomplete`
  → mandatory caveat, confidence −0.3, review flag, QueueEvent `extraction_incomplete`; core
  membership does NOT override.
- **FR13 (review aggregation):** top-level `needs_human_review` = OR of conditions;
  `review_reasons[]` enumerates each (enum in SCHEMA_AND_CONTRACTS).
- **FR14 (glosses):** core → hand aliases in `curated_core.json`; non-core null title_en → Arabic
  name + `name_en_gloss` marked "(unofficial translation)"; `name_en` stays null.

## 3. Non-functional
Latency: report **mean + p50 + p95 + max, user-visible incl. all waits** (A28); ex-backoff is
diagnostic only. AR+EN, UTF-8, free tiers, one laptop. 0 claim-level core hallucinations (vs gold).

## 4. Output schema
See `SCHEMA_AND_CONTRACTS.md` (complete discriminated Pydantic union — A07). `agents/models.py`
implements it verbatim and is the single source imported by nodes, UI, and eval.

## 5. Tools & agentic loop (A02, A06/A27 — get_contacts REPLACED after live verification)

**Research finding (2026-07-25):** contact phone/address data is NOT in Dawlati REST (acf empty,
no ajax route, client-rendered). So `get_contacts` as a live external call is **not viable**.
Resolution: contacts are crawled from `/en/directory` into a LOCAL `ContactRecord` store
(best-effort enrichment), and the second external call becomes `live_service_lookup` (VERIFIED:
REST `?search=` returns live results + modified_gmt).

| Tool | What | External? |
|---|---|---|
| `search_services(query,k)` | RRF BM25+dense over local corpus | local |
| `resolve_document(name_ar)` | normalize → corpus → lookup → abstain | local |
| `check_freshness(post_id)` | live Dawlati REST modified_gmt compare | **external** ✓ verified |
| `live_service_lookup(query)` | live Dawlati REST `?search=` — confirms service exists / newer match | **external** ✓ verified |

Contacts: `enrich_contacts(authority_term)` = local lookup into the crawled ContactRecord store;
returns `[]` if no match. NOT counted toward the external-call requirement.

**Bounded research loop (A02 — replaces the 8-call free loop):** ONE plan call → system executes
the planned tool calls (deterministic, batched) → the model sees all observations → AT MOST ONE
re-plan (reserved for retrying an unresolved document with a normalized alias) → compose. Hard
budget: ≤2 model calls in the loop + 1 compose; per-call 5 s timeout; partial results allowed
(unresolved items flagged). Two external calls (check_freshness + live_service_lookup) run in the
model's plan on the normal path. Prompt: `prompts/research_agent_v1.md`.

**Per-document freshness is a DETERMINISTIC SYSTEM step, not model-planned (N3):** after
`resolve_document` returns, the system automatically runs `check_freshness(post_id)` on each
corpus-resolved document — this does NOT consume the model's re-plan (which stays available for
alias-retry) and is NOT counted against the model tool budget. Budget guard: the model plan is
capped at ≤6 tool calls (1 service freshness + 1 live_service_lookup + up to 4 resolve_document);
system per-document freshness adds ≤N more. If a service has >4 required documents, resolve all of
them but degrade to **service-only freshness** for the extras (SCOPE §15 cut-order item 4), noting
it in caveats. This keeps latency and the 8K-TPM budget bounded while showing a real
decide→act→observe→re-plan cycle.

Graph: `detect_language → validate_input → classify_intent → retrieve → research(plan→execute→
≤1 replan) → compose → validate_schema → respond`, with terminal branches for refusal/not-found/
clarification and the FR11 follow-up path.

### Memory
Short-term: 6-turn buffer + `service_record` + `user_held_documents[]`. Long-term: Chroma
(read-only at answer time). Rejected: summarization memory, per-user persistence, FAISS.

### Guardrails
Input node (pre-LLM): ≤1000 chars, strip HTML/control chars, reject no-alphabetic, injection screen.
Output: Pydantic discriminated models; FR9 retry.

## 6. Corpus, contacts & core (counts FROZEN)

- **Service catalog** = `ministry_service_ser` (195) + `services` (24) + `useful-numbers-post` (30)
  = **249 posts / 219 service pages**. Report four denominators: catalog / fetched / extracted_ok /
  verified-40 (never conflated).
- **Contact catalog (A27, NEW contract):** crawl `/en/directory` (Playwright — client-rendered)
  into `ContactRecord[]`; also `ministires` (~52) titles for authority normalization. Coverage is
  best-effort; a `contacts_coverage.md` records how many authorities got a contact. Gate: G1b.
- **Crawl spike FIRST (A13):** 10-page vertical spike, **ground truth SAVED as
  `data/spike_gold.json`** with per-field annotations (documents, fees, authority, location, time,
  title). Gate on field-level recall for ALL those fields, not just documents. <80% doc-list recall
  after 2 h → fallback = exactly the 40 core services, manual.
- **Core verification (A24):** `core_verification.csv` — 40 rows (reviewer/date/`*_ok`/
  discrepancies/en_alias/source_url). **Every lookup-table row used by any core/demo service is
  source-checked** (not 5 of 20). This file is review EVIDENCE.
- **Gold oracle (A03):** `tests/gold_claims.json` (seeded) holds expected FACTUAL VALUES — separate
  artifact from the CSV.
- **Review queue (A09):** `data/review_queue.jsonl`, append-only + file lock, `QueueEvent` schema
  with nullable `subject_post_id`; dedupe on (event_type, subject, open).

## 7. Prompts (DRAFTED v1 — A17)
`prompts/intent_classifier_v1.md`, `prompts/research_agent_v1.md`, `prompts/composer_v1.md` —
all three exist now with role/mandate/tools/negative-constraints/schema + few-shots. Iteration log
covers all three (≥1 failure-driven iteration each; composer target 3+), each entry a diff.

## 8. Evaluation (24 cases + gold oracle — A03, A12, A18, A28)
- Normal (10 core, 5 AR/5 EN): compared against `gold_claims.json` FACTUAL VALUES (doc-set match
  w/ accepted_variants, fees/authority/duration value match, null_fields stay null). Retrieval
  quality measured on a HOLDOUT set distinct from θ-calibration (A12).
- Edge (8): non-core; lookup-table doc; unresolved doc (abstain); ambiguous two-service →
  clarification; misspelled AR; null fee stays null; `changed` (tampered modified_gmt); REST
  unreachable → `unverified`.
- Adversarial (6): bribery, legal, France visa, injection, gibberish, PII.
- **Manual audit of ALL 24** for paraphrased inventions (A03/G8). **Two failure-mode records
  captured with input/trace/wrong-output/root-cause/fix/before-after (A18).** Latency: mean/p50/
  p95/max incl. waits.

## 9. Demo (8 min) — A15
Pitch (30 s) → **live** EN query: checklist + trace showing the plan→execute→re-plan loop with
check_freshness + live_service_lookup external calls (2 min) → live AR query, RTL (1.5 min) →
failure showcase: unresolved doc + `changed` source → flags + queue (1.5 min) → composer prompt on
screen (1 min) → eval numbers + HITL queue (1.5 min). Live path is primary; `--offline` rehearsed
ONLY as emergency. Backup video uploaded + linked.

## 10. Logging (local JSONL only; A16, A20)
Run traces (JSONL) — UI/eval/failure-analysis source; review queue; `prompts/ITERATION_LOG.md`;
`report/AI_LOG.md` (**exact prompts where recoverable, honestly labeled where not — A16**);
evidence register in PROGRESS incl. **architecture diagram + appendix assembly rows (A20)**.

## 11. Out of scope
Tavily/open-web; LangSmith cloud tracing; `get_contacts`-via-REST (not available — contacts are
local crawl enrichment); wait-time prediction; portal.dawlati; geocoding/maps; daily scheduler
(design-only §7); French; depth-2 resolution; persistent accounts.

## 12. Figure-1 mapping
Included as v2, minus Tavily/LangSmith; second external call = live_service_lookup (not contacts).
Omissions (edge track, n8n, multi-agent, fine-tuning) explained in report §2.

## 13. Privacy
Queries → Groq cloud (state + mitigate: no accounts, no cloud traces, local JSONL gitignored,
local embeddings, public corpus). Consistent (LangSmith cut).

## 14. Repo compliance
`.env.example` = GROQ_API_KEY + MODEL_ID; Python `secret_scan.py` (patterns + entropy, history +
tree); exact `==` pins post-G0; README + video link; `agents/models.py` = single schema source.

## 15. Risks & fallbacks (A01, A30)
- **G0 model bakeoff (A01, verified):** `qwen/qwen3.6-27b` (Preview; JSON Object Mode only,
  reasoning none/default) vs `openai/gpt-oss-120b` (strict json_schema, reasoning low/med/high).
  **Per-model adapters required** — they are NOT drop-in. Winner → MODEL_ID; **pin exact model
  id**.
- **Model fallback ≠ provider fallback (A30):** both are Groq. Provider/network outage →
  `--offline` emergency mode (rehearsed separately at G11). Qwen being Preview is a stability risk
  → prefer GPT-OSS if bakeoff is close, since strict schema + non-Preview reduce risk.
- Contacts thin (verified risk) → answer still valid without contacts; enrichment is best-effort.
- Crawl <80% recall → 40-core manual fallback.
- Cut order if slipping (A-updated): (1) follow-ups/FR11; (2) full corpus beyond core; (3) contact
  enrichment; (4) per-document live freshness (keep service check); (5) UI polish beyond RTL.
  NEVER cut: 20+ tests + gold, visible bounded loop + 2 external calls, drafted prompts, two
  failure analyses, report, live demo path, backup video.
