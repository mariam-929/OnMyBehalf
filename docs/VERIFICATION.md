# VERIFICATION.md — Stage gates v3 (folds A01–A30 gate findings)

Rules (v2 + additions):
- **Bootstrap (A05):** `agents/models.py` (schema) + `agents/adapters.py` (per-model) + gate
  scripts + synthetic fixtures are PERMITTED before G0 passes; all OTHER production code is blocked
  by G0. Production schema must equal the G0-tested fixture.
- Human sign-offs name a person + date; each human gate names a reviewer ≠ producer (A21).
- Claude runs auto checks; never self-certifies human checks.
- A gate closes only when its ARTIFACT exists — not on prose.

**Dependency (A22 — G5 uses synthetic fixtures made in G0, NOT the crawl):**
`G0 → { DATA: G1→G1b→G2→G3→G4 }  ∥  { BUILD: G5(synthetic fixtures) } → G6(needs G4 index) → G7 → G8 → (G9,G10) → G11`

### G0 — Env + per-model bakeoff (A01,A05,A30)
- Auto: imports pinned; GROQ_API_KEY set; **both adapters run the 10 structured + 2 tool-call
  fixtures at the REAL schema; winner schema-valid ≥9/10, p50 ≤10 s**; real limits → `model_limits.json`;
  synthetic G5 fixtures generated + committed; venv outside OneDrive.
- Human: read 5 AR outputs per model; bless winner (numbers → PROGRESS). Reviewer: __

### G1 — Service catalog (A19 denominators)
- Auto: exactly 3 post types; counts vs 195/24/30 (>5% miss fails); no dup ids; every row modified_gmt.
- Human: 5 random URLs in browser. Reviewer: __

### G1b — Contact catalog (A27, NEW)
- Auto: `/en/directory` crawl → ≥1 ContactRecord per ≥60% of distinct authorities referenced by
  the 40 core services; `contacts_coverage.md` written.
- Human: 3 contacts checked against the live directory. Reviewer: __
- (If coverage <60%: contacts stay best-effort; answer valid without them — not a blocker.)

### G2 — Corpus quality (REFRAMED by PR #1 — ajax-ingested, not page-crawled; A13)
**Reframe:** the service DETAIL pages are empty (verified — a rendered page is ~430 chars of
chrome). There is NO page crawl and NO 10-page render spike / 40-core fallback. The corpus comes
structured from the services-directory admin-ajax endpoint
(`tools/crawler/fetch_service_directory.py`). The risk shifted from "can we render the page" to
"is the extraction / document-splitting correct" — **fill-rate ≠ correctness.** Coverage is a
source property: only 3 of 22 ministries are populated (Dawlati is adding them incrementally);
report 4 denominators, never present 195 as national coverage.
- Auto (`check_g2.py`): `data/corpus/*.json` exist; all Pydantic-valid; **#files == #distinct
  post_ids** (ingester fails loud otherwise); ≥150 complete (required_documents non-empty —
  currently 180/193); every record has modified_gmt_at_crawl + canonical content_hash; unmatched
  ≤~5% (currently 2). Extraction correctness: `data/spike_gold.json` scored — machine docs vs
  human-verified gold, recall ≥85% (PENDING until humans verify).
- Human (Maria/Ghina; reviewer Ghina): open the live guide, diff **3 civil-registry core services
  field-by-field** (e.g. 11464 بطاقة هوية, 11554 تسجيل ولادة) + skim 7; correct
  `data/spike_gold.json` `gold_documents` and set `verified=true`, then re-run check_g2.
  (Core-40 rebuilt around civil registry — passport/license do NOT exist; candidates in
  `report/evidence/core40_candidates.md`.)

### G3 — Reference data + gold (A03,A24)
- Auto: `core_verification.csv` 40 complete rows; **every lookup row used by core/demo source-checked
  (A24)**; `gold_claims.json` has ≥10 normal cases with FACTUAL values (not booleans, A03).
- Human: each core row signed by reviewer; all used lookup rows confirmed against source_url. Reviewer: __

### G4 — Retrieval calibrated (A12, no leakage)
- Auto: θ calibrated on DEV set; measured on SEPARATE HOLDOUT: **top-1 ≥90% or correct
  clarification** on core holdout (report CI for small n); 3 known-out queries abstain 3/3; 2
  ambiguous → clarify 2/2; embed ≤2 s.
- Human: inspect misses → verdict; BGE-M3 vs e5. Reviewer: __

### G5 — Graph skeleton (synthetic fixtures, A22)
- Auto: compiles; mock traversal of ALL terminal paths → schema-valid discriminated responses;
  unit tests green (language, validation, normalizer, **Duration parser+aggregator incl. mixed-unit
  → computable=false (A10)**, RRF, **queue append-only+lock+dedupe (A09)**, schema round-trip).
- Human: none.

### G6 — Agent end-to-end (A02,A03,A26)
- Auto: 5 smoke (1 gold core case): action 5/5; schema 5/5; **gold factual match on core case (A03)**;
  provenance 0 violations; latency ≤20 s incl. waits; **trace shows the 2 external calls
  (check_freshness+live_service_lookup) AND a deterministic observation-driven branch — fixture
  where an unresolved doc forces the ≤1 re-plan, asserted automatically (A26)**; composer prompt
  file has all 5 elements (string checks); **loop respects ≤2 model calls / ≤6 model-planned tool
  calls (A02, N3)**; **`live_service_lookup` returns a populated `LiveLookupResult`; an
  `is_newer=true` fixture sets review_reason `newer_version_available` + needs_human_review (N6)**;
  **composer produces NO duration not derivable from evidence (N1) — a docs-with-null-duration
  fixture yields is_lower_bound=true, never an invented total**.
- Human: read 5 answers (AR fluency, usability). Reviewer: __

### G7 — Freshness & HITL (A08,A09,A14)
- Auto: **inject a dead/timeout REST client while Groq stays UP (A14)** → `unverified` + flag +
  caveat + queue; tampered modified_gmt → `changed` + flag + queue; equal → `unchanged`, no flag;
  per-document freshness populated **by the deterministic system step, NOT the model plan, and
  without exceeding the tool budget; >4-doc service degrades to service-only freshness with a caveat
  (N3)**; TTL>180d lookup row → unverified (A08); queue dedupe holds (A09).
- Human: observe one injected-source-failure run (≠ turning off wifi). Reviewer: __

### G8 — Evaluation (A03,A18,A28)
- Auto: 24/24; normal ≥9/10 **gold-correct**; adversarial 6/6; edge ≥7/8; provenance 0; latency
  **mean+p50+p95+max incl. waits (A28)** in eval_report.json.
- Human: **all-24 manual audit → audit.md; core claim-level hallucinations = 0; TWO failure records
  captured (input/trace/wrong-output/root-cause/fix/before-after) (A18).** Reviewer: __

### G9 — UI (A15,A29)
- Auto: headless boot 200/30 s; scripted query renders; `--offline` serves 3 demo queries with
  EMERGENCY banner; **adversarial HTML/RTL string is escaped, not executed (A29)**.
- Human: non-builder walks demo incl. AR RTL tables + **live path is primary, offline shown as
  emergency only (A15)**. Reviewer: __

### G10 — Repo & report (A16,A17,A18,A20)
- Auto: brief §6.3 structure; `secret_scan.py` clean (patterns+entropy, history+tree); `==` pins;
  README video link; **prompts ≥2 versions each; AI_LOG has exact prompts for recoverable
  interactions, honestly-labeled otherwise (A16); ITERATION_LOG ≥1 failure entry per prompt (A17);
  two failure records present (A18); evidence register incl. architecture diagram + appendix
  assembly rows complete (A20)**.
- Human: reader-1 report vs brief Table 6 + rubric Exceeds; reader-2 fresh clone → working smoke
  query. Reviewers: __, __

### G11 — Demo readiness (human-only, A14/A15/A30)
- Two ≤8-min rehearsals (4 required elements) on the LIVE path; **THREE distinct drills: Dawlati
  source outage (inject dead REST), Groq provider outage (→ offline emergency), normal** — kept
  separate (A14/A15/A30); backup video on 2nd device; Q&A dry run incl. the model-retirement +
  contacts-not-in-REST decision stories. Reviewer: __

## Gate record: authoritative copy in PROGRESS.md.
