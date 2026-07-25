# RESOLUTIONS.md — Dispositions for adversarial review findings (2026-07-25)

Source: `ADVERSARIAL_REVIEW_FINDINGS.txt`. Verification of empirical claims done against primary
sources (Groq deprecations page, LangGraph fault-tolerance docs, LangSmith privacy docs, arXiv)
on 2026-07-25. Documents amended to v2: SCOPE.md, TECH_PLAN.md, VERIFICATION.md (+ PROGRESS.md,
CLAUDE.md, new report/AI_LOG.md). Owner = team (names to be filled in PROGRESS checklist);
deadline for all doc-level items: done 2026-07-25; empirical items land at their gates.

Legend: ACC = accepted, PART = partially accepted, REJ = rejected with evidence.

| ID | Sev | Disposition | Resolution (doc §) |
|---|---|---|---|
| F01 | BLK | **ACC — verified true** (deprecations page: both models retired for free tier 2026-07-17) | Model bakeoff qwen3.6-27b vs gpt-oss-120b is now G0; TECH_PLAN §1.2; SCOPE §15. Evidence: G0 bakeoff numbers |
| F02 | BLK | **ACC — confirmed, understated** (pages JS-rendered; GET-hash could never match) | FR6 redesigned: REST `modified_gmt` compare at answer time; canonical extract-hash only for recrawl diff. SCOPE FR6, TECH_PLAN §3 |
| F03 | BLK | ACC | Research phase = LLM tool-calling loop (decide-act-observe, max 8 calls); 2 external calls (check_freshness, get_contacts) in normal path; G6 asserts both visible. SCOPE §5 |
| F04 | BLK | ACC | Claim-level gold from core_verification.csv; eval compares normalized fields; URL check demoted to provenance. SCOPE §8, G8 |
| F05 | BLK | **RESOLVED externally** — written confirmation obtained: deadline Wed 2026-07-29 | CLAUDE.md, PROGRESS blockers cleared |
| F06 | BLK | ACC | Schedule rebaselined: 2 parallel tracks, ~3 h/day contingency, pre-authorized cut order, today (Jul 25) recovered for G0. TECH_PLAN §9 |
| F07 | MAJ | ACC | Discriminated union w/ per-action payloads incl. suggestions + review_reasons. SCOPE §4, models.py |
| F08 | MAJ | ACC | Typed contracts CatalogRecord…QueueEvent + producer/consumer map. TECH_PLAN §3 |
| F09 | MAJ | ACC | Duration model + parser rules + parallel/sequential aggregation + worked example. SCOPE FR5, TECH_PLAN §3 |
| F10 | MAJ | ACC | RRF(k=60) fusion; θ_abs/θ_amb calibrated at G4 on gold set. SCOPE FR2, TECH_PLAN §4 |
| F11 | MAJ | ACC | `clarification_needed` action + ambiguity margin rule + eval case. SCOPE FR2/§4/§8 |
| F12 | MAJ | ACC | Gloss policy: hand aliases for core; labeled unofficial gloss otherwise; name_en stays null. SCOPE FR14 |
| F13 | MAJ | ACC | `record_status:"incomplete"` forces caveat + −0.3 confidence + review flag; overrides core. SCOPE FR12 |
| F14 | MAJ | ACC | FR11 follow-up contract (required state; clarification when absent; user-declared held docs). SCOPE FR11 |
| F15 | MAJ | ACC | `--offline` cached demo mode + banner; provider-outage drill in G11; error action on Groq failure. SCOPE FR10/§9 |
| F16 | MAJ | ACC | All 3 prompts drafted v1 before graph nodes (BUILD track ordering). SCOPE §7, TECH_PLAN §9 |
| F17 | MAJ | ACC | `report/AI_LOG.md` created 2026-07-25 with backfilled entries; same-day updates mandated. SCOPE §10 |
| F18 | MAJ | PART — assumptions were already labeled, but framing improved | OMSAR content ops named system owner; 5-query competitor comparison added (Day 3); assumptions explicitly flagged. SCOPE §1 |
| F19 | MAJ | ACC | Counts frozen: 249 catalog / 219 service / ≥150 extracted_ok / 40 verified; four denominators reported separately. SCOPE §6, G1/G2 |
| F20 | MAJ | ACC | 40-row core_verification.csv (reviewer/date/fields/discrepancies) required at G3; doubles as eval gold. SCOPE §6 |
| F21 | MAJ | ACC | Single QueueEvent schema + atomic append + dedupe + status lifecycle. SCOPE §6 |
| F22 | MAJ | **ACC — verified** (enabled LangSmith tracing sends I/O to cloud; masking doc exists) | LangSmith cut; local JSONL only; privacy section now consistent. SCOPE §10/§13 |
| F23 | MAJ | ACC | Confidence = computed formula over evidence factors; core can score low. SCOPE FR7 |
| F24 | MAJ | ACC | Per-source freshness via REST modified_gmt for corpus-resolved docs; verified_on for lookup rows; worst-of aggregation. SCOPE FR6b (cut-order item 3 if slow) |
| F25 | MAJ | ACC | Tavily cut; replaced by get_contacts (Dawlati REST, in-scope, external, demo-visible). SCOPE §5 |
| F26 | MAJ | ACC | 10-page spike first; fallback triggered by measured recall <80%, not elapsed time. TECH_PLAN §1.4, G2 |
| F27 | MAJ | ACC | Real limits read at G0 into model_limits.json; spacing computed; user-visible latency is the primary metric. TECH_PLAN §5 |
| F28 | MAJ | ACC | Evidence register added to PROGRESS.md (claim→artifact→moment→path); capture during Days 1–3. SCOPE §10 |
| F29 | MAJ | ACC | Parallel DATA/BUILD tracks after G0; G5 fixture-based; report/repo checks continuous. VERIFICATION chain, TECH_PLAN §9 |
| F30 | MAJ | ACC | G6 checks prompt elements + 2 external calls + loop reactivity; G10 checks AI-log + iteration log. VERIFICATION v2 |
| F31 | MAJ | ACC | G2 measures field recall; G4 top-1 + abstention/ambiguity calibration; G6/G8 claim-level gold; G8 audits all 24. VERIFICATION v2 |
| F32 | MAJ | ACC | Bootstrap exception written; G0 now runs representative Arabic structured + tool-call fixtures on both candidates. VERIFICATION rules/G0 |
| F33 | MAJ | PART — "alpha" claim FALSE (docs: standard 1.2 features); async-only TRUE | HTTP-level 5 s timeout in code; asyncio.to_thread if node is async. TECH_PLAN §1/§4 |
| F34 | MAJ | PART — valid; needs user input | Owner column in PROGRESS checklist; user must assign names (open item) |
| F35 | MAJ | ACC | Single authoritative detector (alphabetic denominator, ≥0.30); classifier advisory. SCOPE FR1 |
| F36 | MAJ | ACC | needs_human_review = OR of conditions + review_reasons[]. SCOPE FR13 |
| F37 | MAJ | PART | Tavily+LangSmith cut now; follow-ups kept (small, shows memory) but FIRST in pre-authorized cut order. SCOPE §15 |
| F38 | MIN | PART — our cite was for the comparison bundle, not BGE-M3 itself; corrections adopted | arXiv 2402.03216 + 2506.06339 (verified: it IS the Arabic RAG study) in TECH_PLAN §11 |
| F39 | MIN | PART — v1 already said "pin exact at freeze" | Clarified: `==` pins frozen after G0. TECH_PLAN §8 |
| F40 | MIN | ACC | Fallback = exactly the 40-core set, one format. SCOPE §6 |
| F41 | MIN | ACC | RTL wrapper + G9 human visual check. SCOPE FR10, TECH_PLAN §6 |
| F42 | MIN | PART — grep works in our Git Bash, but scanner is better | Python secret_scan.py (patterns + entropy, history + tree). G10 |
| F43 | NIT | ACC | Filename corrected to MSBA316_… in CLAUDE.md |

**Residual risks after amendments:** bakeoff winner's Arabic quality unknown until G0 (measured,
not assumed); crawl extraction quality unknown until spike; owners unassigned until user provides
team names (F34); per-source freshness is the first thing cut if REST latency surprises us.

---

# Round 2 dispositions — A01–A30 (folded into v3, 2026-07-25)

Verified empirically 2026-07-25: A01 (Groq structured-output/reasoning per-model — GPT-OSS strict
json_schema only; Qwen3.6 JSON-object only), A02 (TPM=8K), A30 (Qwen3.6 Preview), and A06/A27
(live API test: contact data NOT in Dawlati REST → get_contacts not viable; `live_service_lookup`
via REST `?search=` verified working). Docs → v3. Legend as above.

| ID | Sev | Disposition | Resolution |
|---|---|---|---|
| A01 | BLK | **ACC — verified** | Per-model adapters (GptOss strict / Qwen36 json-object+retry); G0 tests each through its real path. TECH_PLAN §1.2, SCHEMA §; SCOPE FR9 |
| A02 | BLK | ACC (TPM corrected 6K→8K) | Bounded loop: 1 plan→batched execute→≤1 replan→compose; ≤2 model/≤8 tool calls. SCOPE §5, TECH_PLAN §4/§5, research_agent_v1 |
| A03 | BLK | ACC | `gold_claims.json` (factual values) separate from `core_verification.csv` (evidence). SCHEMA §3, SCOPE §8, G3/G8 |
| A04 | BLK | PART | Resource-aware critical path: laptop-serial compute vs people-parallel writing; owners required. TECH_PLAN §9 (impossibility overstated — team parallelizes writing) |
| A05 | BLK | ACC | Schema+adapter fixture = permitted G0 bootstrap; production schema must equal it. VERIFICATION rules/G0 |
| A06 | MAJ | **ACC — verified, replaced** | Live test: contacts not in REST. `get_contacts`→`live_service_lookup` (verified REST search) as 2nd external call. SCOPE §5, TECH_PLAN §1 |
| A07 | MAJ | ACC | Complete discriminated Pydantic union incl. Contact, freshness enum, provenance, nullability. SCHEMA_AND_CONTRACTS.md §1 |
| A08 | MAJ | ACC | Freshness relabeled `unchanged/changed/unverified` (change-status, not currency); lookup TTL 180d. SCOPE FR6/6b, SCHEMA |
| A09 | MAJ | ACC | Append-only JSONL + portalocker + nullable subject_post_id + dedupe. SCHEMA §1, SCOPE §6 |
| A10 | MAJ | PART | Duration carries `unit`; no cross-unit arithmetic; mixed/unknown → computable=false, component-wise. SCOPE FR5, SCHEMA (service-time WAS already included — minor overreach) |
| A11 | MAJ | ACC | Resolver normalize + θ_doc gate + tie-band abstention. SCOPE FR4, TECH_PLAN §4 |
| A12 | MAJ | ACC | DEV/HOLDOUT split; G4 bar → 90% top-1-or-clarify on holdout, CI disclosed. VERIFICATION G4 |
| A13 | MAJ | ACC | `spike_gold.json` saved; recall gated on documents+fees+authority+location+time. SCOPE §6, G2 |
| A14 | MAJ | ACC | G7 injects dead REST with Groq UP; outage drills separated. VERIFICATION G7/G11 |
| A15 | MAJ | ACC | Live path is primary demo; `--offline` = emergency-only, banner. SCOPE FR10/§9, G9/G11 |
| A16 | MAJ | ACC | AI_LOG: exact prompts where recoverable, honestly labeled otherwise; G10 checks. SCOPE §10 |
| A17 | MAJ | ACC | All 3 prompts DRAFTED as artifacts now: prompts/*_v1.md. SCOPE §7 |
| A18 | MAJ | ACC | Two failure records (input/trace/wrong/root-cause/fix/before-after) gated at G8/G10. SCOPE §8 |
| A19 | MAJ | PART | ROI formula + sensitivity restored, labeled illustrative. SCOPE §1 |
| A20 | MAJ | ACC | Evidence register adds architecture diagram + appendix assembly rows. PROGRESS, SCOPE §10 |
| A21 | MAJ | PART — needs team | Owner + reviewer columns on every gate/task; NAMES still required from user. PROGRESS, VERIFICATION |
| A22 | MAJ | ACC | Synthetic G5 fixtures created in G0; G5 no longer needs crawl. VERIFICATION chain/G0/G5 |
| A23 | MAJ | PART — fix conflicts w/ brief | Field name `confidence` kept (brief mandates it); disclosed as evidence-quality heuristic, not probability. SCOPE FR7, SCHEMA §2 |
| A24 | MAJ | ACC | Every lookup row used by core/demo source-checked (not 5/20). SCOPE §6, G3 |
| A25 | MAJ | ACC | Competitor 5-query comparison moved to G0/G1 (before build). SCOPE §1, TECH_PLAN §9 |
| A26 | MAJ | ACC | G6 asserts a deterministic observation-driven branch fixture (unresolved doc forces re-plan). VERIFICATION G6 |
| A27 | MAJ | **ACC — verified** | ContactRecord contract + `/en/directory` crawl + authority normalization + G1b. SCHEMA, SCOPE §6 |
| A28 | MIN | ACC | Report mean+p50+p95+max incl. waits. SCOPE §3/§8, G8 |
| A29 | MIN | ACC | RTL wrapper html-escapes dynamic text; validated URLs only; G9 adversarial-HTML check. SCOPE FR10, TECH_PLAN §6 |
| A30 | MIN | **ACC — verified** | Model vs provider fallback separated; exact model id pinned; prefer GPT-OSS on close bakeoff (not Preview). SCOPE §15 |

**Still OPEN (artifact/gate must exist — not closed by prose):** A01 adapters (G0), A03 gold
seeding (G3), A06/A27 contact coverage (G1b), A13 crawl recall (G2), A18 failure records (G8),
A21 owner NAMES (needs user), A25 competitor data (G0/G1).

**Round-2 reviewer errors/overreach noted:** A23 (rename conflicts with brief-mandated field);
A10 (service processing time was already included); A04 ("one laptop can't parallelize" ignores a
multi-person team doing writing tasks). All partially accepted on their valid core.

Note (N5): F03/F24/F25 above describe `get_contacts` as the second external call — **superseded by
A06/A27** (get_contacts removed; `live_service_lookup` is the second external call). Rows kept as
historical record.

---

# Round 3 dispositions — N1–N6 (folded into v3, 2026-07-25)

Third review verdict was **START CODING** (0 architectural blockers; prior fixes verified real).
N-findings are localized spec/prompt edits, none block G0. All verified against the actual files
before folding. Legend as above.

| ID | Sev | Disposition | Resolution |
|---|---|---|---|
| N6 | MAJ | **ACC — verified** (no LiveLookupResult model; review_reasons had no newer-match value) | Added `LiveLookupResult` model + `newer_version_available` review reason + consumer rule; G6 asserts populated + is_newer→flag. SCHEMA §1, SCOPE §5, G6 |
| N1 | MAJ | **ACC — verified** (composer few-shot output [7,15] not derivable from shown [5,10]) | Rewrote composer few-shot into 3 examples where every number derives from evidence (null-duration→lower bound; mixed-unit→computable=false); G6 asserts no invented duration. composer_v1.md, G6 |
| N2 | MAJ | **ACC — verified** (IntentResult/ResearchPlan existed only in prompts) | Added `IntentResult`, `ResearchPlan`, `PlanStep` (tool name = Literal enum) to schema; G5 round-trips them. SCHEMA §1 |
| N3 | MAJ | **ACC — verified** (per-doc freshness collided with the single re-plan + ≤8 budget) | Per-document freshness = deterministic SYSTEM step (not model-planned, not in model budget); model plan capped ≤6; >4 docs → service-only freshness (cut-order 4). SCOPE §5, research_agent_v1, G6/G7 |
| N4 | MIN | **ACC — verified** (PROGRESS line 67 get_contacts; lines 8/9/23 said v2) | Fixed stale tool ref + v2→v3 pointers. PROGRESS.md |
| N5 | NIT | ACC | Supersession note added above (F03/F24/F25). RESOLUTIONS.md |

**Still OPEN after round 3 (unchanged, gate/team-dependent):** owner NAMES (F34/A21); G0 bakeoff;
crawl recall (G2); gold seeding (G3); contact coverage (G1b); competitor data (G0/G1); bounded-loop
TPM/latency closure (measure at G0/G6 — do not assert closed until measured).
