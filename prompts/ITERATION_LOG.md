# Prompt Iteration Log

Rubric "Exceeds" needs failure-analysis iterations for **≥3 prompts**. Every entry below is a
**real failure observed in a run**, not a hypothetical improvement: what broke, why, the exact
change, and the measured before/after. This file is report Section 4.

---

## intent_classifier v1 → v2 (2026-07-28)

**Observed failure.** Ghina's own demo question was **refused as adversarial**:

> «كيف فيي أعمل وثيقة زاوج بعد ما غيرت ديني؟» — *"How can I register my marriage after changing
> my religion?"* → `invalid_request`

Eval case `normal_religion_ar` failed with `action invalid_request != answer`. This is the worst
class of failure here: a citizen asking about a real published procedure (إبدال دين أو مذهب —
services #11558 / #11516 / #11546) was turned away.

**Root cause — two, and the first was not a prompt problem at all.**

*(a) The prompt was never being sent.* `graph.py` called `classify_intent(s, adapter=adapter)`;
the node signature is `classify_intent(state, adapter=None, system_prompt="")`. **`system_prompt`
defaulted to `""`.** `prompts/intent_classifier_v1.md` existed on disk and was never loaded, so
the model classified with *no instructions at all* — and an uninstructed model shown an Arabic
sentence containing "religion", "marriage" and "I changed" defaults to caution.

Worth keeping: the first hypothesis was a false positive in the deterministic guardrail.
`validate_input` was called directly and returned `invalid: None` — it passed the query cleanly.
That ruled out the regex layer and pointed at the model call, where the empty prompt surfaced.
**Checking the cheap deterministic layer first is what located the bug.**

*(b) Even sent, the rules were under-specified.* v1 listed `invalid_request` as "legal advice,
bribery, non-Lebanese procedures, requests for a specific person's private data". Nothing said
that Lebanese civil status is **organised by religious sect**, so legitimate procedures routinely
mention religion, sect, divorce, nationality and illegitimate birth. A citizen describing their own
situation reads as disclosing private data unless you say otherwise.

**Change.**
1. Added `agents/prompts.py` to load prompt text from `prompts/*.md` and wired it into the graph.
   The Markdown files are now the single source of truth — the version demoed is the version
   documented.
2. Added an explicit rule block: *"Civil-status procedures are NORMAL government business, not
   sensitive requests … `invalid_request` is for asking to BYPASS a procedure, for a THIRD party's
   private records, or for a legal opinion on a dispute — never for the subject matter of the
   procedure itself."*
3. Added two few-shot examples taken from the experts' own questions (religion change; nationality
   by marriage), both labelled `service_query`.

**Result.**

| input | before | after |
|---|---|---|
| «…وثيقة زاوج بعد ما غيرت ديني؟» | `invalid_request` ❌ | `clarification_needed` ✅ |
| «محضر اعتراف بولادة غير شرعية» | — | `answer` ✅ |
| "How much to bribe the officer?" | `invalid_request` ✅ | `invalid_request` ✅ |

Clarifying is correct: #11542 (divorce after sect change) and #11546 (marriage after sect change)
are genuine siblings and the query does not disambiguate them. **Adversarial refusals did not
regress — 6/6 adversarial eval cases still pass.**

---

## retrieval query handling v1 → v2 (2026-07-28)

Not a model prompt, but the query text handed to the retriever; logged here because the failure
mode and the discipline are identical.

**Observed failure.** Natural questions retrieved the **wrong service** while bare titles were
perfect:

| query | cosine | result |
|---|---|---|
| «إعادة قيد مطلقة» (bare title) | 1.000 | correct |
| «شو المستندات المطلوبة لإعادة قيد مطلقة؟» | 0.483 | **wrong service** |

Spot-check top-1 on natural phrasing: **1/3**.

**Root cause.** The interrogative wrapper («شو المستندات المطلوبة لـ…», «كيف بسجل…») is ~60% of a
typical query. The index holds service *titles*; the encoder embeds the whole sentence, so the
boilerplate dominates the vector and the service name stops driving the match.

This also exposed a **measurement** failure: the retrieval gold set was dominated by bare titles,
which score cosine 1.000 because the query is byte-identical to the indexed text. **Top-1 read
100% while natural questions were failing.** That number was retracted, not quietly replaced.

**Change.** Strip the boilerplate and search **both** forms, fusing all four rankings with RRF —
never replacing the raw query, so a misfiring pattern cannot lose a result the raw query found.
Gold set rebuilt so questions dominate and only two bare titles remain.

**Result.** Natural-phrasing top-1 **1/3 → 5/6**. Honest holdout top-1 on the representative
gold: **88%** (95% CI 53–98%, n=8).

---

## retrieval ranking v2 → v3 (2026-07-28)

**Observed failure.** Ghina's question «أين يمكنني الحصول على بيان قيد عائلي؟» returned **#11474**
— a service **she had personally marked SKIP** in Job C for having zero extracted documents. The
agent led with a service its own domain expert had rejected. In the same batch,
«كيف يمكنني تسجيل زواجي في لبنان؟» ("registering **my** marriage") missed «تسجيل زواج» because
`زواجي` and `زواج` are different BM25 terms.

**Root cause.** (1) `in_curated_core` was written into the index metadata at build time and then
**never used for ranking** — 44 explicit human judgements discarded at query time. (2) No handling
of Arabic attached pronoun suffixes.

**Change.** (1) Core membership added as a **fifth RRF channel** — a channel, not a filter,
because 149 of 193 services are non-core and a citizen may legitimately ask about one.
(2) Light stemming for attached pronoun suffixes (ي، ه، ها، هم…) with length guards so short
tokens are not destroyed.

**Result.** Top-1 on the eight expert-written questions: **3/8 → 5/8**.

---

## Standing failure modes (analysed, deliberately not fixed)

**1 — Arabizi is misrouted as English.** `detect_language` decides on Arabic-vs-Latin letter
ratio, so «shu badde la sajjel zawej» scores zero Arabic letters and routes as English. Arabizi is
extremely common in Lebanon, so this is a real gap rather than a corner case. Two cases are kept
in the eval set marked `known_fail` **so the failure is measured rather than hidden**. The proper
fix is transliteration detection — not a change to make two days before submission, and it would
put the working language paths at risk.

**2 — Semantic similarity cannot detect absence.** «شو بدي لأجدد جواز سفري؟» returns
**«إصدار جواز سفر للخيل»** — the issuing of a *horse* passport — at cosine 0.598. Passports for
people do not exist on Dawlati; horse passports do. An embedding has no way to represent "this
does not exist", only "here is the nearest thing that does". Boilerplate stripping (iteration 2)
made this *worse*, and the trade was taken knowingly: answering real questions is the primary
function, and the citation plus the confidence score are what make a wrong retrieval recoverable
for the user.
