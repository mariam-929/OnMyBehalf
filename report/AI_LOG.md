# AI Interaction Log

Mandatory appendix per course brief §9. Format per interaction:
Task / Prompt / AI Response Summary / Implementation / Modifications.
**Update same-day, every session.** Backfilled 2026-07-25 from session history (F17); exact
prompt wording reconstructed where the verbatim text was not retained is marked *(paraphrased)*.

---

## AI Interaction 1
Task: Evaluate the project idea (LLM agent over Lebanon's Dawlati portal) against the course brief.
Prompt: *(paraphrased)* "This is a government paperwork portal (dawlati.gov.lb). Our agent tells
users the papers/requirements for a legal process, guides to centers, hours, call centers,
estimates total time. Look at the idea, feasibility, scope adjustments, fit to the brief."
AI Response Summary: Judged the idea a good fit for the Public Sector domain; ran live recon of
the Dawlati site (REST API exposes ~195 services but detail pages are JS-rendered; portal is
login-walled; robots ai-train=no; site already has an OMSAR chatbot). Recommended cutting the
daily-update pipeline to a per-query freshness check + human-review flag.
Implementation: Adopted the scope framing; produced CLAUDE.md project context.
Modifications: Deadline later corrected from 2 days to 4 (Wed Jul 29).

## AI Interaction 2
Task: Add "where to obtain each document" as a feature.
Prompt: *(paraphrased)* "It should also tell us from where we can get each paper."
AI Response Summary: Framed required documents as a dependency graph (documents are often
themselves services); proposed a `resolve_document` tool (corpus → lookup table → unresolved)
bounded to depth 1, with per-document provenance to avoid hallucinated sources.
Implementation: Became FR4 + document resolution design in SCOPE.
Modifications: none.

## AI Interaction 3
Task: Lock down detailed scope.
Prompt: *(paraphrased)* "Refine the requirements, decide on a scope, be very specific." Plus four
multiple-choice decisions (corpus breadth, languages, interface, freshness approach).
AI Response Summary: Produced SCOPE.md v1 with 10 FRs, JSON schema, 4 tools, curated core, 24
eval cases, demo script. User chose: full crawl + 40-core, AR+EN, Streamlit chat, live freshness
with cached fallback.
Implementation: SCOPE.md v1.
Modifications: Superseded by v2 after review (see AI Interaction 8).

## AI Interaction 4
Task: Re-audit against the brief for missed requirements.
Prompt: *(paraphrased)* "Recheck the project brief and re-evaluate; ensure we hit everything."
AI Response Summary: Found 7 gaps (quantified impact/ROI, memory design, corrected iteration-log
rubric reading, intermediate-prompt schemas, input-validation guardrail, omitted-component
justifications, privacy position); patched SCOPE.
Implementation: SCOPE.md §§ updated.
Modifications: none.

## AI Interaction 5
Task: Detailed tech-stack analysis and technical plan with research.
Prompt: *(paraphrased)* "Perform a detailed tech stack analysis and technical planning; do
thorough research and justify each decision."
AI Response Summary: Web research produced TECH_PLAN.md v1 (LangGraph, Groq Qwen3-32B, BGE-M3,
Chroma, Playwright). **Contained the F01 error: relied on third-party articles that listed
qwen3-32b/llama-4-scout as current; these were retired 2026-07-17.**
Implementation: TECH_PLAN.md v1.
Modifications: Corrected in v2 after the model-retirement finding (AI Interaction 8). Lesson:
verify provider claims against primary docs.

## AI Interaction 6
Task: Progress-log + session-protocol + verification-gate system.
Prompt: *(paraphrased)* "Create a progress log so each session starts smoothly" then "add
per-step verification we cannot bypass (automated + human)."
AI Response Summary: Created PROGRESS.md (living status) and VERIFICATION.md (gates G0–G11, auto +
human each), with a session protocol in CLAUDE.md.
Implementation: PROGRESS.md v1, VERIFICATION.md v1.
Modifications: Both revised to v2 after review.

## AI Interaction 7
Task: Write a prompt for an external LLM to review the plan for gaps before coding.
Prompt: *(paraphrased)* "Write a detailed review prompt … catch gaps early before implementation
… include file paths (CLI reviewer with filesystem access)."
AI Response Summary: Produced REVIEW_PROMPT.md — adversarial pre-code gap review across 9
dimensions, weighting findings by cost-if-found-late.
Implementation: REVIEW_PROMPT.md.
Modifications: none.

## AI Interaction 8
Task: Verify the external reviewer's findings and apply valid ones.
Prompt: *(paraphrased)* "Check this assessment objectively, verify which claims are valid, do
research, be critical" → then "apply the appropriate modifications."
AI Response Summary: Verified findings against primary sources — confirmed F01 (both Groq models
retired 2026-07-17), F02 (freshness hashing broken), F22 (LangSmith cloud traces contradict
privacy claim), F33 (timeouts async-only, but NOT alpha), F38 (better citations). ~30/43 findings
valid. Amended SCOPE/TECH_PLAN/VERIFICATION to v2, created RESOLUTIONS.md dispositions, this log.
Implementation: SCOPE v2, TECH_PLAN v2, VERIFICATION v2, RESOLUTIONS.md, AI_LOG.md.
Modifications: Rejected F33's "alpha" claim with evidence; partially accepted F18/F37/F39/F42.

## AI Interaction 9
Task: Verify the first external reviewer's findings (F01–F43) and apply the valid ones.
Prompt (verbatim): "check this assessment objectively and verify which claims are valid or not
'…ADVERSARIAL_REVIEW_FINDINGS.txt'. do research when deciding on the validity of each claim, be
objective and critical" — then, after the report and confirming the deadline: "1- written deadline
is wednesday, now apply the appropriate modifications according to the assessment outcome".
AI Response Summary: Verified vs primary sources — confirmed both Groq v1 models retired Jul 17
(F01), freshness hashing broken (F02), LangSmith privacy conflict (F22), timeouts async-only but
not alpha (F33). Amended all docs to v2; created RESOLUTIONS.md + this log.
Implementation: SCOPE/TECH_PLAN/VERIFICATION v2, RESOLUTIONS.md, AI_LOG.md; cut Tavily+LangSmith;
freshness→REST modified_gmt; added research loop, discriminated schema, typed contracts.
Modifications: Rejected F33 "alpha" with evidence; partially accepted F18/F37/F39/F42.

## AI Interaction 10
Task: Verify the second reviewer's re-evaluation (A01–A30) of the v2 docs, then fold accepted
findings with a final verification round on each.
Prompt (verbatim): "check this re-assessment objectively and verify which claims are valid or not
'…ADVERSARIAL_REVIEW_FINDINGS_REEVALUATION.txt' do research when deciding on the validity of each
claim, be objective and critical" — then: "fold the accepted findings, but when folding each
finding do one final round of verification on it and its fit on the overall picture and do thorough
research".
AI Response Summary: Verified vs Groq docs — A01 (GPT-OSS strict json_schema only; Qwen3.6
JSON-object only; reasoning params differ), A02 (TPM 8K not 6K; 8-call loop over budget), A30
(Qwen3.6 Preview). Live-tested Dawlati REST: contact data NOT exposed (get_contacts not viable);
`live_service_lookup` via REST `?search=` verified. ~26/30 valid, 4 partial, A23 fix conflicts
with brief.
Implementation: v3 docs; new SCHEMA_AND_CONTRACTS.md, prompts/*_v1.md, tests/gold_claims.seed.json;
RESOLUTIONS A01–A30. Replaced get_contacts→live_service_lookup; bounded research loop; per-model
adapters; freshness relabeled unchanged/changed/unverified.
Modifications: A23 kept `confidence` field (brief-mandated) as disclosed heuristic; A10/A04 partial.

---
*(Append implementation-phase interactions below as they happen. Prompts from Interaction 9 onward
are verbatim; 1–8 reconstructed/paraphrased from history per A16.)*
