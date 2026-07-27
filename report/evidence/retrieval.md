# G4 — retrieval evidence (2026-07-27/28)

## Result

| Criterion | Target | Measured | |
|---|---|---|---|
| Holdout top-1 | ≥90% | **88% (7/8)**, 95% CI 53–98% | FAIL |
| Abstain on known-out | 3/3 | **1/3** | FAIL |
| Clarify on ambiguous | 1/1 | **1/1** | PASS |
| Latency | ≤2 s/query | ~1.27 s/query incl. encode | PASS |

Thresholds calibrated on the **dev set only** (n=9, balanced accuracy 0.93), measured on a
**holdout never used for calibration** (n=12): `θ_abs = 0.55` (cosine), `θ_amb = 0.0`.

> ### ⚠ An earlier version of this file reported top-1 = 100%. That number was wrong and is
> ### retracted here.
>
> The first gold set was dominated by **bare service titles** (`تسجيل طلاق`, `إعادة قيد مطلقة`).
> Those score cosine **1.000** because the query is byte-identical to the indexed title, so top-1
> looked perfect while natural questions were quietly failing: `شو المستندات المطلوبة لإعادة قيد
> مطلقة؟` retrieved the **wrong service** at 0.483. Real users type questions, not titles.
> The gold set was rebuilt so questions dominate and only 2 bare titles remain, and **88% is the
> number on that representative set.** The lesson is in the report: a holdout only protects you
> if it resembles production, and ours did not.

## Design decisions, with the measurements behind them

**1. RRF ranks; cosine abstains.** RRF was specified for both. It cannot do abstention, and this
was measured rather than assumed: RRF scores depend only on RANK, so the top-1 score was
0.0164–0.0328 across *every* query in the gold set — identical for a perfect match and for
`"how do I open a bank account"`. No RRF threshold separates in-scope from out-of-scope. Dense
cosine is a genuine quality signal, so both thresholds read cosine instead. RRF is kept for
ranking, which is what it is good at.

**2. A title-only vector per service, alongside the full-text chunks.** Nearly every
civil-registry service *requires* an ID card as a document, so a query about *obtaining* an ID
matched the document lists of dozens of unrelated services. Before: `بطاقة هوية` (#11464) lost
top-1 to a building-restoration permit. After: top-1. This single change moved overall top-1 from
4/8 to 8/9.

**3. Arabic definite-article stripping in the BM25 tokenizer.** `بطاقة الهوية` in a query did not
match `بطاقة هوية` in a title, because `الهويه` and `هويه` are different BM25 terms. Tokens ≤3
chars are left alone (`ال` is most of a short word).

**4. Balanced accuracy, not raw hit-count, for calibration.** Dev classes are imbalanced (5 found
vs 2 abstain). With raw hits, "never abstain" *tied* with a properly calibrated threshold and the
tie-break selected θ=0 — a system that answers everything. Per-class recall makes abstention count
as much as retrieval.

**5. Interrogative-boilerplate stripping as extra RRF channels.** `شو المستندات المطلوبة لـ…`,
`كيف بسجل…`, `what documents do I need to…` are 60% of a typical query and dilute the embedding
until the service name stops dominating. Stripping them and searching BOTH forms (4 RRF channels,
never a replacement — a misfiring pattern cannot lose what the raw query found) moved
natural-phrasing top-1 from 1/3 to 5/6 in spot checks.

## The failures, and why they are not tuned away

**Abstention is genuinely weak: 1 of 3.** The headline limitation, and it is a property of the
approach rather than a bug:

> **`شو بدي لأجدد جواز سفري؟` ("what do I need to renew my passport?") returns
> `إصدار جواز سفر للخيل` — the issuing of a HORSE passport — at cosine 0.598.**

Passports for people do not exist on Dawlati; a horse passport does. Semantic similarity measures
resemblance, and `جواز سفر` genuinely resembles `جواز سفر`. **Embedding similarity cannot detect
absence** — it has no way to represent "this thing is not here", only "this is the nearest thing
that is". The same effect makes `رخصة سياقة` land on grazing and fishing licences.

Boilerplate stripping made this *worse*, not better: it improves matching for out-of-scope
queries too, raising `جواز سفر` from 0.423 to 0.598 and pushing it over θ_abs. That trade was
accepted knowingly — answering real questions is the primary function, and the confidence
heuristic plus the citation are what protect the citizen when retrieval is wrong. A user who sees
"horse passport" with a source link will notice; the design does not depend on the retriever being
right, which is the point of citing everything.

**`how to register a marriage in Lebanon` → #11508 instead of #11552.** Both are marriage
registration services; this is a near-miss between siblings, not a category error.

## A disputed gold label, left failing

`"بيان قيد"` was labelled **clarify** in the gold; the system returns **found → #11548
بيان قيد عائلي وإفرادي**.

This is a genuine judgement call, not obviously a system error. #11548 covers *both* the family
and individual extract, so returning it may be the correct answer. But #11470
(`بيان قيد عن سجلات إحصاء ما قبل 1932`) also exists, so the term is arguably ambiguous.

**Deliberately left failing.** Changing the gold label would make the gate pass without changing
the system, which is the definition of tuning to the metric. **This needs a domain expert's
verdict (Maria/Ghina), not a developer's.**

## Honest caveats

- **n is small.** 12 holdout queries; the 95% CI on top-1 is 68–100%. The point estimate should
  not be quoted without the interval.
- **5 of 12 holdout queries are near-verbatim service titles** (`تسجيل طلاق`, `إعادة قيد مطلقة`),
  which score cosine 1.000 and inflate top-1. Real users do not type exact titles. The dialect and
  English queries are the honest test, and those also pass — but the headline 100% is flattered by
  the verbatim cases.
- **Semantic similarity cannot detect absence.** `"driving licence renewal"` scored 0.544 against
  real licence services (grazing, fishing, forestry) — higher than several *correct* matches. It
  abstains only because θ_abs sits at 0.55. Absence is detectable here by threshold, not by
  understanding; a query for a non-existent service that happens to resemble an existing category
  is the standing weakness of this design.

## Encoder

**`sentence-transformers/LaBSE`**, not the planned `BAAI/bge-m3`. BGE-M3 is a ~2.3 GB download that
had transferred 36 KB after several minutes on the build machine and would have blocked the
critical path two days before submission. LaBSE was already cached, is purpose-built for
cross-lingual sentence retrieval across 109 languages including Arabic, and delivers the numbers
above. `EMBED_MODEL` is an environment variable, so the comparison the G4 human check asks for can
be run without code changes if BGE-M3 finishes downloading.

## Reproduce

```bash
EMBED_MODEL=sentence-transformers/LaBSE python tools/indexer.py
EMBED_MODEL=sentence-transformers/LaBSE python tests/gates/check_g4.py
```

Index: 193 services → 395 vectors (1 title + ~1.05 content chunks each), Chroma `dawlati_v1`,
cosine. Gold: `tests/retrieval_gold.json`. Thresholds written to
`data/retrieval_thresholds.json`.
