# retrieval.md — G4 evidence (2026-07-25, owner Ali)

Evidence-register row "Retrieval quality". Produced by `tests/gates/check_g4.py`; thresholds land
in `data/retrieval_thresholds.json`, which `tools/search_services.py` reads at run time.

## Stack

| Layer | Choice |
|---|---|
| Embeddings | **BAAI/bge-m3**, 1024-dim, cosine, `normalize_embeddings=True` |
| Vector store | Chroma persistent, collection `dawlati_v1`, 193 vectors |
| Lexical | BM25Okapi over **normalised titles only** |
| Fusion | RRF, k=60 |
| Index build | 193 docs embedded in **49.5 s** (257 ms/doc), one-off |
| Query latency | **p50 0.09 s**, max 0.28 s (gate ≤2 s) |

**No chunking.** The plan specified sentence-aware chunking at a 500-token cap, written when the
corpus was expected to be long crawled pages. The ajax corpus is short structured records and
bge-m3 accepts 8192 tokens, so one vector per service is used. Chunking would have split a
document list away from the title that identifies it — the opposite of what these queries need.

## Two design corrections, both driven by measured failures

**1. RRF ranks; cosine decides.** Thresholding on the RRF score was implemented first, per the
literal plan, and it does not work. RRF scores are bounded (max 2/61 ≈ 0.0328) and encode mostly
*whether both channels returned a document*, not relevance. Measured with RRF thresholds:

| Query | Outcome with RRF thresholds |
|---|---|
| `ما هي الأوراق المطلوبة لتجديد جواز السفر؟` | **`found` → `إصدار جواز سفر للخيل`** (a horse passport), margin 0.0061 |
| `how do I apply for a French visa` | `ambiguous` at 0.0284 — higher than many correct Arabic hits |

Cosine is comparable across queries; RRF is not. Abstention and ambiguity now read dense cosine,
while RRF still orders the list. Both queries now correctly return `not_found`.

**2. The lexical channel is gated to positive BM25 scores.** An English query matches no Arabic
title, but BM25 still emits a full ranking of zero-scoring documents, and RRF treated a garbage
rank-1 as authoritative. Measured before the gate: `how do I get an ID card` returned an ISBN
request as top-1, with the correct `بطاقة هوية` pushed to #3 **despite cos 0.610**, and a document
at **cos 0.000** scoring 0.0164. After gating, English queries run effectively dense-only and
`بطاقة هوية` is top-1.

One deliberate subtlety: the abstention test reads the cosine of the **top-ranked** candidate, not
the best cosine present. We abstain when the document we would actually answer with is not similar
enough. For the passport query the channels disagree — RRF ranks the horse passport first
(cos 0.508) while `بطاقة هوية` scores 0.554 — so a **negative** cosine margin is a real signal of
channel disagreement, not a bug. Taking the max there would have answered with an unrelated
service instead of abstaining.

## Calibration (A12 — no leakage)

DEV and HOLDOUT are split **by service**, seed 7, so no service appears in both: 90 DEV queries,
90 HOLDOUT queries. θ is chosen on DEV only; the holdout number below was never optimised against.

**Chosen: θ_abs = 0.58, θ_amb = 0.04.**

| HOLDOUT metric | Result | Gate |
|---|---|---|
| top-1 or correct clarification | **96.7%** (top-1 83.3%, clarified 13.3%) | ≥90% ✅ |
| known-out queries abstained | **5 / 5** | 3/3 ✅ |
| under-specified → clarification | **2 / 2** | 2/2 ✅ |
| query latency p50 | **0.09 s** | ≤2 s ✅ |

Known-out set (all verified absent from Dawlati, issue #2): passport renewal AR + EN, driving
licence, French visa (out of jurisdiction), vehicle registration. Under-specified set:
`وثيقة زواج` (8+ marriage-document variants by spouse nationality) and `قيد مولود`.

**G4 AUTO GATE: PASS.**

## ⚠️ Two caveats that must reach the report

**The query set is synthetic.** Real citizen phrasings do not exist yet — the core-40 is being
rebuilt (issue #2) and `gold_claims.json` is still a seed. Queries are templated paraphrases of
service titles (`كيف أحصل على {title}؟`), which share vocabulary with the document in a way a real
question would not. **96.7% is an upper bound and a regression guard, not measured retrieval
quality.** Re-run this gate unchanged against human-written queries at G8 and report that number.

**The objective treats a clarification as equal to a correct top-1.** It shouldn't, quite: asking
the citizen a follow-up is real friction. The trade is visible in the DEV sweep at θ_abs=0.58:

| θ_amb | DEV top-1 | DEV clarify | DEV total |
|---|---|---|---|
| 0.02 | **92.2%** | 5.6% | 97.8% |
| 0.04 (chosen) | 84.4% | 15.6% | **100%** |
| 0.06 | 75.6% | 24.4% | 100% |

θ_amb=0.04 maximises total accuracy; θ_amb=0.02 answers directly far more often at a small cost in
total. That is a product judgement, not a tuning one — **the team should decide** whether the agent
should ask more or answer more. Easy to change: one value in `data/retrieval_thresholds.json`, no
code edit.

## Reproduce

```bash
python tools/indexer.py                 # rebuild data/chroma (~50 s)
python tests/gates/check_g4.py --write  # calibrate + measure + write thresholds
```

`data/chroma/` is gitignored and rebuilds from `data/corpus/`. Note it currently lives inside the
OneDrive-synced folder; if sync causes file locks during a rebuild, pause OneDrive or point
`CHROMA_DIR` outside it.
