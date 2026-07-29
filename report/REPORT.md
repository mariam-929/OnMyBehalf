# OnMyBehalf, an accountable agent for Lebanese government procedures

**MSBA 316, Text Analytics & NLP · AUB · Summer 2025/26 · Dr. Ahmad El-Hajj**
Team: Gaby, Mariam, Ali, Ghina, Maria
Repository: <https://github.com/mariam-929/OnMyBehalf>

---

## 1. Problem and stakeholder

Completing any transaction at a Lebanese government office requires knowing three things in
advance: which documents to bring, what it costs, and where to go. Getting one wrong means a
wasted trip. The information is published on **Dawlati** (dawlati.gov.lb), OMSAR's national
services portal, but it is scattered across a directory interface, almost entirely in Arabic,
and it never answers the question citizens actually have: *where do I obtain each of the documents
I am being asked to bring?*

**Stakeholder:** the citizen. **System owner:** OMSAR content operations, who would own the
human-review queue described in §7.

**What we built.** An agent that takes a question in Arabic or English and returns a structured
checklist: every required document, **where to obtain each one**, fees, where to apply, source
freshness, and a link to the exact Dawlati page each fact came from, together with a confidence
score and an explicit human-review flag when the source is uncertain or the data model cannot
represent the answer faithfully.

**The claim is not that it is a better chatbot. It is that it is an accountable one.** Every
factual field is traceable to a government page; the system says when it does not know; and it
flags for human review rather than papering over gaps. Section 6 shows where it still fails.

Accountability is also what decides where the language model is allowed to act. It writes prose;
it plans which unresolved documents to retry; it never emits a fact and never chooses a source
(§3.4, §3.6). Those two exclusions are not caution for its own sake; they are the reason the
guarantees in this report survive contact with the evaluation.

---

## 2. Data: what Dawlati actually contains

We froze a catalog of **249 posts** (195 services, 24 service pages, 30 useful numbers) from the
public WordPress REST API, and a corpus of **193 service records**, 180 of them with required
documents. Three discoveries reshaped the project, and all three are properties of the source
rather than of our pipeline.

**The service detail pages are empty.** The plan assumed a 219-page crawl. A one-hour probe found
that **0 of 249 posts carry content in REST**, and a fully rendered service page yields ~430
characters of navigation and footer with no section keywords and no content XHR. The real corpus
sits behind an admin-ajax endpoint (`omsar_load_directory_ministry_services`), one call per
ministry, returning structured `required_documents_html` / `fees_html` / `notes_html`. Twenty-two
POSTs (~30 s) replaced the planned Playwright crawl. Had we not probed, we would have produced 219
empty records and failed our own corpus gate at roughly 0% recall.

**Only 3 of Lebanon's 22 ministries have published anything**: Agriculture (115 services),
Interior (53), Culture (27). The other 19 return zero. Dawlati says so itself on the guide page.
**We report four denominators separately and never present 195 as national coverage.**

**Passports and driving licences do not exist on Dawlati.** Both were in our original core-40, one
was a gold eval case, and one was the demo script. The only «جواز سفر» match in the entire corpus
is **إصدار جواز سفر للخيل**, a horse passport. The project was rebuilt around the civil-registry
cluster (identity, birth, marriage, divorce, death, civil extracts), which does exist and is what
citizens most often need.

That discovery is also what produced the last piece of architecture. If the country's most-asked
procedure is absent from the portal, then a system that only reads the portal is structurally
incapable of answering it; no amount of retrieval tuning changes that. §3.6 describes the branch
that follows: when Dawlati has no record, the agent falls back to the authority that actually
issues the document. The passport is answerable again, from general-security.gov.lb, with a
citation and an explicit statement that the answer did not come from Dawlati.

---

## 3. Method

### 3.1 Architecture

A **LangGraph** state machine implementing perceive → plan → act → observe:

```
detect_language → validate_input → classify_intent → retrieve
   → research (bounded: plan → execute → ≤1 replan) → compose → validate_schema → respond
        ↘ invalid_request   ↘ clarification_needed   ↘ error
        ↘ external_lookup (only when Dawlati has no record, §3.6) ↘ service_not_found
```

Every node appends to `trace_events`, which is the **single** source for both the UI trace panel
and the eval harness, so what the demo shows is what the metrics measured.

Language detection and input validation are **deterministic and run before any model call**. Two
reasons: an adversarial input should never reach the model, and a refusal that varies run to run
cannot be rehearsed for a demo.

### 3.2 Retrieval

Hybrid, fused with **Reciprocal Rank Fusion** (k=60): BM25 over titles + dense vectors over
Chroma, plus the same two channels over a boilerplate-stripped query, plus a fifth channel for
curated-core membership. Five design decisions, each forced by a measurement (§6.2).

Embeddings are **LaBSE**, not the planned BGE-M3. BGE-M3 is a ~2.3 GB download that had
transferred 36 KB after several minutes on the build machine and was additionally saturating the
connection badly enough to make our live REST calls time out. LaBSE was cached, is purpose-built
for cross-lingual sentence retrieval across 109 languages including Arabic, and `EMBED_MODEL` is
an environment variable so the comparison remains a one-line change.

### 3.3 Tools (5, of which 3 are external)

| tool | kind | what it does |
|---|---|---|
| `search_services` | local | RRF-fused hybrid retrieval |
| `resolve_document` | local | resolves each required document to where it is obtained; **abstains** below threshold |
| `check_freshness` | **external** | live REST `modified_gmt` vs our snapshot → `unchanged / changed / unverified` |
| `live_service_lookup` | **external** | live REST `?search=`: does this service still exist, is there a newer one |
| `external_source_lookup` | **external** | when Dawlati has no record at all, fetches the procedure from the issuing authority's own site (§3.6) |

`resolve_document` uses a **stricter** threshold than retrieval (0.62 vs 0.45) plus a tie band. The
asymmetry is deliberate: a wrong service answer is visible and recoverable, but a wrong *"go here
to obtain this document"* sends a citizen to the wrong ministry.

### 3.4 What the model writes, and what it is never allowed to touch

The LLM contributes **language only**. It emits exactly two fields, `reasoning` (logged) and a
1-2 sentence `summary` for the citizen, and never sees or reproduces a document name, a fee, an
office, a URL or a duration. Those are assembled by code directly from the retrieved record.

The split is deliberate and it is what lets both claims hold at once: the answer reads as an
agent explaining itself, **and** a fabricated document is structurally impossible in it, because
the facts never round-trip through the model. Re-running the full eval after wiring the composer
confirmed it: prose became model-written and **hallucinations stayed at 0**.

Both model calls are time-bounded (6 s classification, 8 s narration) and both degrade to
deterministic behaviour on timeout. Free-tier latency is erratic (identical calls measured
between 0.5 s and 12.8 s), and an unbounded wait in front of an audience is a worse failure than
a plainer sentence. Bounding them moved p50 from 2.55 s to 1.26 s, measured at the time of that
change. The headline p50 in §6.1 differs again (0.98 s); with 22 cases and eight of them
sub-second refusals, the median moves easily between runs; we measured 0.76 s and 0.98 s on two
consecutive runs of the same commit, and we have not attributed that spread to any specific
cause. The figures quoted in §6.1 are the ones in the committed `tests/eval_report.json`.

Before this was wired, `reasoning`, a field the brief mandates, was a hardcoded constant string,
identical on every answer.

### 3.5 Confidence and human review

`confidence` is an **evidence-quality heuristic, not a calibrated probability**, and is disclosed
as such in the answer and here. It starts at 0.9 for a curated-core service or 0.5 otherwise, and
deducts for stale or unverified freshness, unresolved documents, incomplete records, and
conditional structure the data model cannot express (§5). Anything flagged is written to an
append-only, file-locked, deduplicated review queue owned by OMSAR content ops.

### 3.6 Answering when Dawlati has nothing: a federated source layer

§2 records that the single most-asked transaction in Lebanon (the passport) is **not on Dawlati
at all**, and §6.3 records what that cost: the agent returned a horse passport, then, once
abstention was tightened, returned nothing. Both are correct behaviours over a corpus that does not
contain the answer. Neither helps the citizen. But the documents *are* published, by the General
Directorate of General Security, the authority that actually issues them.

So the graph gained one branch:

```
retrieve ──found──────────────→ research → compose
         ──ambiguous──────────→ clarification_needed
         ──not_found──→ external_lookup ──hit──→ research → compose
                                        ──miss─→ service_not_found
```

**It was first wired to fire only where the system had already given up, and that was wrong.**
The original design routed the fallback off `not_found` alone, on the reasoning that a branch which
cannot be reached from any answering path cannot regress one. The eval agreed: `edge_absent_1`
passed, and the passport was answered from General Security.

Opening the UI and retyping the question in four other ways showed the flaw. Retrieval does not
merely *fail* on passport queries, **it succeeds wrongly.** «شو بدي لأجدد جواز سفري؟» matches
«إصدار جواز سفر للخيل», the horse passport, above threshold; the graph therefore reported `found`,
went to compose, and never reached the fallback at all. **Four of six natural phrasings returned
the horse passport. Only the eval's own phrasing abstained**, which is precisely why the eval was
green, the gold case had encoded one wording, and the wording was the unrepresentative one.

The fallback now sits on the `found` arm as well, and the guarantee is stated more narrowly and
more honestly: **the node is a no-op unless the curated registry matches the query**, so its blast
radius is the procedures a human put in that table, not every answer. An explicit animal term
(«خيل», «حصان», *horse*) vetoes the registry, so a citizen who genuinely wants the horse passport
still gets Dawlati's record. Wired off (`external_fn=None`, the default) the graph remains
byte-identical to the previous version.

*This is the second time in this project that a green gate described a narrower reality than we
believed (§6.2), and the first time a human simply retyping a question found it.*

**Design decision: the model does not choose the source.** This is the most important sentence in
the section. It would have been easy, and would have demoed well, to let an LLM decide which
government site to consult. We did not, for the same reason the model is not allowed to emit a
document name (§3.4): a model that selects URLs can invent one, and source selection is the single
decision where a fabrication puts a citizen physically in front of the wrong ministry. Instead:

| step | decided by |
|---|---|
| "Dawlati has no record" | retrieval score below the abstention threshold (deterministic) |
| "which official source covers this" | a curated registry a human opened, read and verified |
| "fetch it" | HTTP, with a committed snapshot as fallback |
| "what does it say" | deterministic extraction, no model input |

The reasoning loop is unchanged and remains where it belongs: `plan_research` (§3.1) decides which
unresolved documents to retry and with what search key, bounded to one re-plan, addressing
documents by index so it cannot put words on screen. **The agent reasons within a source; code
decides which sources exist.**

**How it extends.** The branch is source-agnostic by construction. It calls any function of
`(query, language) → record`, and a source contributes a record in the *same shape* the Dawlati
ingester produces, so composition, caveats, confidence, the review queue, the UI and the eval
harness all work on a new source with no changes. Adding one is therefore two data steps and no
graph changes:

1. append an entry to the registry (subject terms, qualifiers, the AR and EN URLs, the authority);
2. run `tools/crawler/fetch_external_snapshots.py` to capture and verify the snapshot.

What does **not** come free, and we would mislead by implying otherwise: **extraction is
per-site.** Every ministry publishes its own HTML, and the regexes that read General Security's
pages will not read the Ministry of Justice's. That per-source extractor is the real unit of cost
in extending this (roughly the same work the Dawlati ingester needed), and it is why the layer
ships with three verified URLs rather than a claim of national coverage. The registry scales by
table entry; the extractors scale by engineering effort.

What *does* generalise for free is the accountability, which is the part that matters: every
external answer carries the source domain, a clickable URL to the exact page, a caveat stating in
the citizen's language that the service is not on Dawlati, and a freshness label of `unverified`
with a note saying whether the bytes came off the live site in this run or out of the committed
snapshot. `unverified` is not a limitation here; it is the only honest value: freshness is
change-detection against a stored `modified_gmt` (§7), and this source publishes no modification
timestamp to compare against. An auditor can re-derive any cited answer from the snapshot, which
is how §6.1's hallucination count is now computed against *whichever* source an answer cites.

**Measured effect.** Failure rate 36.4% → **31.8%**, hallucinated documents **0**, and the
country's most-asked procedure moved from unanswerable to answered with a citation.

---

## 4. Prompts and iteration

Three prompts (`intent_classifier`, `research_agent`, `composer`), each with role, mandate, tool
list, **negative constraints** and an output schema, all loaded from `prompts/*.md` so the version
demoed is the version documented.

Full detail with before/after measurements is in **`prompts/ITERATION_LOG.md`**. Summary:

| # | iteration | observed failure | result |
|---|---|---|---|
| 1 | `intent_classifier` v1→v2 | **A domain expert's own question was refused as adversarial** | `invalid_request` → `clarification_needed`; adversarial 6/6, no regression |
| 2 | retrieval query handling v1→v2 | natural questions retrieved the wrong service while bare titles scored 1.000 | natural-phrasing top-1 **1/3 → 5/6** |
| 3 | retrieval ranking v2→v3 | a question returned a service **the expert had personally rejected** | expert-question top-1 **3/8 → 5/8** |

Iteration 1 is worth reading in full. The root cause was not the prompt's wording: **the prompt was
never being sent.** `system_prompt` defaulted to `""`, so the model was classifying with no
instructions at all. The deterministic guardrail was checked first, returned "valid", and that is
what located the bug in the model call.

---

## 5. The central finding: a flat document list cannot represent these services

Two domain experts independently reached the same conclusion during human verification, and it is
the most important result in this project. `required_documents` is a `list[str]`, but the source
encodes conditional logic that a flat list destroys:

- **branch by applicant type**: #11528 has three cases (minor / adult / outside the legal window)
  behind `I` `II` `III` headings; #11476 branches general / Syrian wife / Palestinian wife, each
  with different documents;
- **either/or within one requirement**: `اقامة صالحة` **أو** `تأشيرة دخول`;
- **eligibility preconditions**: #11476 requires the marriage registered ≥1 year before applying;
- **document recency windows differing by case**: Syrian `بيان قيد` < 6 months, Palestinian < 3.

**#11476 exhibits all four in a single service.**

Flattening turns *"bring A **or** B"* into *"bring A **and** B"* and shows every branch to every
applicant. The agent is therefore not merely incomplete; it can be **confidently wrong**, which is
the one failure mode this project exists to prevent.

**Measured: 113 of 180 services (63%) carry at least one marker; 46 (26%) carry a high-confidence
one.** Fixing the data model means a schema change, re-extraction and re-verification, not
possible before the deadline. So the system **detects and discloses**: a caveat in the answer, a
confidence penalty capped at 0.40, and a review-queue event. A branched core service can no longer
answer at 0.9.

This finding also touches FR6: the recency windows apply to the **citizen's own documents**, which
`check_freshness` does not cover at all; it checks whether the *source page* changed.

---

## 6. Evaluation

### 6.1 Headline numbers

24 test cases (5 normal, 13 edge, 6 adversarial). **Eight were written by the domain experts** in
their own procedure clusters; the only queries in this project not authored by a developer.

| metric | value |
|---|---|
| **Failure rate** | **31.8%** (7 of 22 scored) · range 31.8-36.4% across runs, see below |
| **Hallucinated documents** | **0** |
| **Latency** | mean 3.3 s · **p50 0.98 s** · max 31.3 s (first case, cold encoder load) |
| Adversarial | **6/6** |
| Normal | 3/5 |
| Edge | 6/11 |
| Retrieval top-1 (holdout) | 88% (7/8), 95% CI 53-98% |
| Extraction recall / precision | 90% / 81% on 8 human-verified services |

Two Arabizi cases are marked `known_fail` and **kept in the set and scored** (a failure excluded
from your own eval is a failure you are hiding), and reported separately so the headline rate stays
readable.

**The headline rate is not deterministic, and quoting it as though it were would be dishonest.**
Across repeated runs of the same commit it oscillates between **31.8% and 36.4%**, and the whole
difference is one case: «how do I open a bank account» is classified sometimes as
`invalid_request` (out of jurisdiction) and sometimes as `service_not_found` (a government service
we do not hold). The gold expects the latter. Both readings are defensible: a bank account is not
a government service at all, so this is a genuinely borderline input on which a non-zero-temperature
classifier is entitled to disagree with itself. With 22 scored cases, **one flipping case moves the
headline by 4.6 percentage points**, which is the more useful thing to take from this number than
either endpoint of the range.

**On the zero hallucinations.** The detector is real: we verified it by injecting a fabricated
document into a known-good answer, and it was caught. But the honest framing is architectural, not
behavioural, **documents are passed through from the retrieved record, not generated**, so
fabrication is structurally impossible in the document list. Zero reflects a design choice
(extractive, not generative). It is a meaningful property to claim, but it is not evidence that the
language model resists hallucination.

### 6.2 Three failures of measurement, not just of the system

All three are reported because they shaped every number above.

**We reported 100% top-1 and it was wrong.** The first retrieval gold set was dominated by bare
service titles, which score cosine 1.000 because the query is byte-identical to the indexed text.
Top-1 read 100% while natural questions were quietly failing: «شو المستندات المطلوبة لإعادة قيد
مطلقة؟» retrieved the **wrong service** at 0.483. Rebuilt so questions dominate: **88%**. *A
holdout only protects you if it resembles production, and ours did not.*

**The gate was not testing the system.** `check_g4` scored abstention on cosine while the live
retrieve node still thresholded on RRF score. The gate reported PASS while the agent abstained on a
valid demo query. Both now call one shared `classify_outcome()`.

**The hallucination detector counted 13 hallucinations that did not exist.** The moment an answer
legitimately cited a second source (§3.6), the check resolved its `source_url` against the Dawlati
corpus, found no matching file, and returned **every document in the answer as fabricated**: 13
phantom hallucinations on one passport answer, against a headline claim of zero. The detector was
not wrong so much as under-specified: it had silently assumed Dawlati was the only source that
could ever be cited. We changed the implementation, **not the definition**: a hallucination is
still *a document absent from the source it is attributed to*, so the check now rebuilds the
cited external record from its committed snapshot and compares against that. The zero in §6.1 is
therefore a **stronger** claim than before: it holds against whichever source each answer cites,
rather than against one hardcoded corpus. A metric that cannot see a new source will not report
that it is blind; it will report a number, and the number will be wrong.

The pattern in all three: **each time the test data or harness became more independent, measured
performance got worse, or the harness turned out to have been measuring something narrower than
we thought.** Retrieval scored 3/8 on the experts' questions versus 88% on ours.

### 6.3 Failure analysis

Of the 7 scored failures, roughly half are strict-scoring artefacts rather than defects: two are
`clarification_needed` where the gold expected an answer, and the candidates are genuine siblings
that the query does not disambiguate (#11542 divorce-after-sect-change vs #11546
marriage-after-sect-change). Asking rather than guessing is the behaviour we want. The genuine
defects are two abstentions on valid questions and two wrong-sibling retrievals.

**Failure mode 1, Arabizi is misrouted as English.** `detect_language` decides on
Arabic-vs-Latin letter ratio, so `shu badde la sajjel zawej` scores zero Arabic letters and routes
as English, and the agent answers an Arabic speaker in English. Arabizi is extremely common in
Lebanon. The fix is transliteration detection, real work, and not safe to attempt two days out.

**Failure mode 2, semantic similarity cannot detect absence.**
«شو بدي لأجدد جواز سفري؟» returns **إصدار جواز سفر للخيل**, a horse passport, at cosine 0.598.
Passports for people do not exist on Dawlati; horse passports do. An embedding has no way to
represent *"this does not exist"*, only *"here is the nearest thing that does"*. Abstention is
**1 of 3**. Boilerplate stripping made this worse, and the trade was taken knowingly: answering
real questions is the primary function, and the citation plus the confidence score are what make a
wrong retrieval recoverable for the user.

*Contained, not cured, and the containment initially missed most of the cases.* The retrieval
defect is unchanged: an embedding still cannot represent absence, and no threshold fixes that. What
changed is the **consequence**; the query is answered from General Security's own site with a
citation (§3.6).

The first attempt at that containment only covered queries where retrieval *abstained*. Because the
horse passport is frequently retrieved **above** threshold, four of six natural phrasings still
returned it, and the eval did not catch this because its single gold phrasing was one of the two
that abstained. **A gold case pins one wording; a citizen has many.** The fallback now also
overrides a wrong retrieval hit when the curated registry matches, with an animal-term veto so a
genuine horse-passport question still reaches Dawlati's record. Coverage is still limited to
procedures a curated source covers, the driving licence has none and still terminates in
`service_not_found`.

**Failure mode 3, a document resolver is not a rule detector, and the score cannot tell you
which it just matched.** Extending per-document resolution to the external passport record failed,
and the measurement is the interesting part. Of 13 lines extracted from the Arabic page, **exactly
one resolved against the corpus, and it was wrong.** «أما بالنسبة لطلبات عائلات عسكريي الأمن
العام…» is a *rule* about who may submit fewer documents, not a document, and it resolved to the
civil-registry directorate at **0.6367**, while a genuine requirement scored **0.7004** and
abstained. So the score does not separate right from wrong here, and no threshold tuned on it would
have: this is the same conclusion `accept_rescue` reached about alias retries (§3.3), reached again
by a different route.

The cause is structural rather than a resolver defect. General Security's Arabic page nests
procedural rules inside the same `<ul>` as the documents, under an applicant heading, where its
English twin puts them under "Remarks", so the extracted list is a mixture and the resolver has no
signal to tell the two apart. FR4 requires abstention rather than attaching a doubtful source, so
**per-document resolution is deliberately not offered for external records**: all 13 lines are
carried through to the citizen, marked unresolved and flagged for review. The complete checklist
survives; no document is attributed to an authority that did not issue it. One wrong *"go here to
obtain this"* costs more than thirteen honest *"not resolved"*.

This is the clearest example in the project of the rule that produced every other result in it:
**when the evidence does not support a claim, the system says so rather than degrading quietly.**

---

## 7. Freshness, human-in-the-loop, and honest limits

`check_freshness` compares live REST `modified_gmt` against the value stored at crawl time and
returns `unchanged | changed | unverified`. This is **change detection, not a currency guarantee**,
and is labelled that way everywhere it appears. Recrawl diffing uses one canonical
`fetch → render → extract → normalize → sha256` pipeline, never raw HTML.

Both producers feed one **append-only, file-locked, deduplicated** `review_queue.jsonl`. Dedupe is
by `(event_type, subject_post_id, subject_label)` so one stale service hit by ten users produces
one ticket, not ten. Queue reads happen inside the lock, through the same handle, checking before
locking would let concurrent writers both observe "absent" and both append.

**Known limitations, stated plainly:**

1. **Coverage is 3 of 22 ministries.** A source property, reported with four denominators.
2. **Conditional structure is detected, not represented** (§5), 63% of services affected.
3. **Abstention is weak (1/3)**, §6.3.
4. **Arabizi is unsupported**, §6.3.
4b. **The federated layer is three URLs, one authority, and it is not self-extending** (§3.6).
   Adding a source is a registry entry plus a snapshot capture, but each new *site* needs its own
   extractor, so this is a demonstrated mechanism rather than national coverage. External answers
   also carry two honest reductions in service: freshness can only ever be `unverified`, because
   the source publishes no modification timestamp to detect change against, and per-document
   resolution is withheld (§6.3, failure mode 3). A citizen asking about a passport gets a cited,
   complete checklist, not the *where do I obtain each document* they would get for a
   civil-registry service.
5. **Extraction recall is 90%, not 100%.** Human verification rated 3 of 8 services inadequate;
   the residual misses are documents living in the notes section rather than the documents field.
6. **Small n.** 12 holdout retrieval queries, 22 scored eval cases, 8 human-verified services.
   Confidence intervals are reported; the point estimates should not be quoted alone.
7. **Reviewer independence is partial, and unevenly so.** The team reduced to three during the
   build, so the technical gates have no independent technical reviewer. Where that applies it is
   named rather than papered over:
   - **G1, G1b, G2, G3**, independently reviewed. Maria and Ghina each verified their own
     procedure clusters and reviewed each other's; neither approved her own work. These are the
     gates the data claims rest on, and they are the ones with real independence.
   - **G0**, closed by the project lead, who had read the five Arabic classifications but had
     also run the bakeoff. Producer and reviewer are the same person. The auto half
     (10/10 schema-valid) is unaffected.
   - **G4, G5, G6, G8, G9**, automated checks only; the human halves remain open.
   No sign-off was fabricated. Where no independent reviewer existed the gate record says so,
   because a gate record that cannot be trusted is worth less than no gate record at all.

---

## 8. Verification and process

Eleven stage gates (G0-G11), each with an automated check and a human check, recorded in
`docs/PROGRESS.md`. Two rules were enforced throughout:

- **reviewer ≠ producer.** Maria and Ghina each verified their own clusters and reviewed each
  other's; neither approved her own work. Where no independent reviewer existed, the gate stayed
  open rather than being signed.
- **Gates were allowed to fail.** G2 sat at an honest FAIL (80% recall) until a validated fix
  raised it to 90%. G4 still fails 2 of 4 criteria and is reported as such.
- **A changed expectation was recorded, not quietly edited.** Adding the federated layer made one
  eval case (`edge_absent_1`, the passport) change from correctly abstaining to correctly
  answering. Rather than relax the expectation, we changed it *and* added an assertion that the
  answer cites `general-security.gov.lb`, because without it the loosened case would have passed
  on any answer at all, including a fallback to the horse passport. The reason is written into the
  test case itself.

Human verification was decisive rather than ceremonial. Two experts checked 8 services field by
field and found **two distinct extraction failure classes** plus the structural finding in §5.
Their skim-level checks found worse bugs than the deep checks did, without them we would have
shipped on false confidence.

Status at submission: **G0, G1, G1b, G2, G5, G6, G9 pass**; G3 is complete for the core-44 and gold but
lacks the source-checked lookup table; G4 passes 2 of 4; G7, G8, G10, G11 partial.

**AI usage** is logged in `report/AI_LOG.md` per the brief.

---

## Appendix, reproducing the numbers

```bash
python tools/crawler/enumerate.py                 # catalog (249)
python tools/crawler/fetch_service_directory.py   # corpus (193)
EMBED_MODEL=sentence-transformers/LaBSE python tools/indexer.py
EMBED_MODEL=sentence-transformers/LaBSE python tests/gates/check_g4.py   # retrieval
EMBED_MODEL=sentence-transformers/LaBSE python tests/gates/check_g6.py   # agent e2e
EMBED_MODEL=sentence-transformers/LaBSE python tests/run_eval.py         # the 24 cases
pytest tests/unit -q                                                     # 159 unit tests
streamlit run app/streamlit_app.py
```

The six external-source snapshots (§3.6) are **committed**, so nothing above requires the network
to reach general-security.gov.lb. To re-capture them, or to check that the committed copies still
parse after a source change:

```bash
python tools/crawler/fetch_external_snapshots.py            # re-capture all six
python tools/crawler/fetch_external_snapshots.py --verify   # re-extract from disk, write nothing
```

`data/` is gitignored and regenerated by the first two commands; the numbers in §6 come from
`tests/eval_report.json` and `report/evidence/`.
