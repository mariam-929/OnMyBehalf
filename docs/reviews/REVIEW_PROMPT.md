# Prompt: Final pre-implementation review of our agentic-AI course project (v3 docs)

*(Copy everything below the line into the reviewer CLI agent. It has filesystem access, so it
reads the files itself — no attachments needed.)*

---

## Files to review — read ALL of these fully before writing anything

Read-only review: do NOT modify, create, or move any file. Paths (quote them — they contain
spaces):

**The authority (compliance ground truth):**
1. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\MSBA316_Project_Summer_2025_2026.pdf`

**The current plan (all at v3):**
2. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\CLAUDE.md`
3. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\SCOPE.md`
4. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\SCHEMA_AND_CONTRACTS.md`
5. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\TECH_PLAN.md`
6. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\VERIFICATION.md`
7. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\PROGRESS.md`
8. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\prompts\intent_classifier_v1.md`
9. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\prompts\research_agent_v1.md`
10. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\prompts\composer_v1.md`
11. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\tests\gold_claims.seed.json`
12. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\report\AI_LOG.md`

**Closure evidence (read to verify, not to trust):**
13. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\RESOLUTIONS.md` — claims of what two prior reviews changed.
14. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\ADVERSARIAL_REVIEW_FINDINGS.txt` — review 1 (F01–F43).
15. `C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\Final Project\ADVERSARIAL_REVIEW_FINDINGS_REEVALUATION.txt` — review 2 (A01–A30).

If you cannot read the PDF, say so at the top and mark every brief-compliance judgement UNVERIFIED;
do not reconstruct the brief from the other files.

## Situation

This project has already been through TWO adversarial pre-code reviews. Their findings were
verified (several against live Groq docs and the live Dawlati API) and folded into v3, with
per-finding dispositions recorded in RESOLUTIONS.md. Empirically settled facts you should NOT
re-litigate unless you have concrete contrary evidence: the two v1 Groq models are retired; Groq
structured-output/reasoning support differs per model (GPT-OSS strict json_schema vs Qwen3.6
JSON-object-only); Dawlati contact fields are not in its REST API while REST `?search=` and
per-record `modified_gmt` work. Still zero code. G0 (environment + per-model model bakeoff) has not
run. This is the LAST checkpoint before implementation begins.

## Your mandate

You are an independent, adversarial reviewer and course-grader proxy. This is not a fresh teardown
and not a rubber stamp. Your job is to answer one question with evidence: **is this plan ready to
start coding, or is there a specific defect that will cause rework or grade loss if we start now?**
Three lenses, in priority order:

1. **Closure verification.** RESOLUTIONS.md claims ~56 findings were resolved. Do NOT trust those
   claims — verify them against the actual v3 files. For a sample of the highest-severity
   dispositions (all BLOCKERs, plus any you find suspicious), confirm the fix is really present,
   complete, and consistent across every file it touches — not just asserted in prose. Flag any
   "closed" finding that is actually prose-only, partial, or contradicted elsewhere.
2. **Regression / new-defect hunt.** The v3 rewrite introduced new artifacts (SCHEMA_AND_CONTRACTS,
   three prompts, gold seed, bounded research loop, per-model adapters, live_service_lookup,
   relabeled freshness, G1b). New writing creates new bugs. Hunt for contradictions the folding
   introduced: schema fields referenced in SCOPE/prompts but absent from SCHEMA_AND_CONTRACTS;
   the prompts disagreeing with the schema or the bounded-loop budget; gates checking things the
   specs no longer say; dangling references to cut components (Tavily/LangSmith/get_contacts);
   numbers that disagree across files.
3. **Residual readiness.** Independent of the prior reviews, is anything still genuinely missing
   that blocks a clean start — a data contract with no consumer, an undefined behavior on the
   normal path, a gate whose pass criterion can't actually be met, an implementation ambiguity an
   LLM coding agent could not resolve without guessing?

## Rules of engagement (read these — they change how you should behave)

- **Weight everything by cost-if-found-late.** A defect that surfaces on Jul 27 with no slack is
  worth 100× a stylistic nit. Deadline is Wed Jul 29; four days; one laptop; team of ≤5.
- **You are allowed — encouraged — to greenlight.** After two deep reviews, the correct answer may
  be "start coding; resolve the rest at their gates." Do not manufacture findings to fill a table.
  A short review that says "ready, with these 3 real risks" is more valuable than 25 invented ones.
- **Distinguish "blocker before code" from "resolve during build at gate GX."** Many open items
  (crawl recall, bakeoff outcome, gold seeding, owner names) are DELIBERATELY deferred to gates.
  Do not report a deferred-to-gate item as a blocker unless the deferral itself is unsafe. Judge
  the plan's *gating*, not the fact that artifacts don't exist yet.
- **Every claim cites a file and section.** No generic best-practice lectures.
- **Don't re-open settled empirical facts** (above) without contrary evidence you can point to.
- If two of your findings conflict, resolve or flag the tension. If short on capacity, sacrifice
  depth, never table completeness.

## Focused checks (do these specifically)

- **Prompts vs schema vs loop:** Do `composer_v1.md`, `research_agent_v1.md`, and
  `intent_classifier_v1.md` emit exactly the shapes SCHEMA_AND_CONTRACTS.md defines? Does the
  research prompt's tool budget match SCOPE §5 and VERIFICATION G6 (≤2 model / ≤8 tool)? Do the
  prompts reference only tools that still exist (no get_contacts)?
- **Two-external-call claim:** With get_contacts gone, does the normal demo path still make two
  genuine external calls (check_freshness + live_service_lookup), and does G6 actually assert it?
  Is live_service_lookup's output contract defined, or is it a tool with no typed result?
- **Gold oracle:** Can `gold_claims.json` (as seeded/specified) actually adjudicate the normal
  cases, given the seed has null placeholders to be filled at G3? Is the DEV/HOLDOUT split (A12)
  real or nominal given the tiny corpus?
- **Bounded loop vs latency/TPM:** Re-check the arithmetic in TECH_PLAN §5 against 8K TPM and the
  ≤20 s target for the bounded loop (not the old 8-call one). State whether it closes.
- **Schema completeness:** Is every field used by the UI/eval/nodes present with type, nullability,
  and enum? Name any hole.
- **Gate meetability:** For G0, G1b, G2, G4, G6 — can the stated pass criteria actually be met by
  this team in the time, or are any set to fail by construction (e.g., 90% top-1 on a tiny
  holdout, 60% contact coverage that the data may not support)?

## Output format (strict)

1. **Go / no-go verdict** — ≤8 lines: START CODING / START AFTER N NAMED FIXES / RE-PLAN, the
   single most important reason, and the count of true blockers.
2. **Closure audit table** — the BLOCKER/MAJOR dispositions you actually verified: Finding ID (F/A)
   | Claimed fix | Verified? (YES / PARTIAL / NO / PROSE-ONLY) | Evidence (file §).
3. **New findings table** — only genuinely new or still-open items: ID | Severity (BLOCKER /
   MAJOR / MINOR / NIT) | Type (closure-gap / regression / residual) | File §ref | Finding | Fix |
   Blocks-code-now? (Y / resolve-at-GX). Order by cost-if-found-late.
4. **The short list** — the ≤7 things (if any) to fix in the documents before writing code, each
   mapped to a finding ID. If the list is empty, say so plainly and say start.
5. **What you could not assess** — empirical/live items you'd need to run (crawl, bakeoff, etc.);
   list, don't guess.
