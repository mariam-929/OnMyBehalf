# G4 — retrieval evidence (2026-07-27/28)

## Result

| Criterion | Target | Measured | |
|---|---|---|---|
| Holdout top-1 | ≥90% | **100% (8/8)**, 95% CI 68–100% | PASS |
| Abstain on known-out | 2/2 | **2/2** | PASS |
| Clarify on ambiguous | 2/2 | **1/2** | FAIL |
| Latency | ≤2 s/query | ~1.35 s/query incl. encode | PASS |

Thresholds calibrated on the **dev set only** (n=7), measured on a **holdout never used for
calibration** (n=12): `θ_abs = 0.55` (cosine), `θ_amb = 0.0`.

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

## The one failure, and why it is not being tuned away

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
