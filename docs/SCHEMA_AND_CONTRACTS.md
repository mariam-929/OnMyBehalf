# SCHEMA_AND_CONTRACTS.md — complete typed contracts (v3, 2026-07-25)

Closes A03/A07/A08/A09/A10/A11 with concrete artifacts (prose was not enough — reviewer rule).
This is the SINGLE source of truth for data shapes; `agents/models.py` implements it verbatim.
Enums, nullability, and cardinality are normative. Verified against live Dawlati REST 2026-07-25.

## 1. Pipeline contracts (producer → consumer)

```
crawler ─▶ CatalogRecord ─▶ (fetch+extract) ─▶ CorpusRecord ─▶ indexer ─▶ Chroma
directory crawl ─▶ ContactRecord ─▶ contacts store (local)
retrieve ─▶ RetrievedCandidate ─▶ research phase ─▶ ResolvedDocument / Duration / FreshnessResult / LiveLookupResult
research LLM ─▶ IntentResult (classifier) / ResearchPlan (planner)   # LLM output shapes, validated too
compose ─▶ Response (discriminated) ─▶ Streamlit + eval
any tool ─▶ QueueEvent ─▶ review_queue.jsonl
```

```python
# ---- ingestion ----
class CatalogRecord(BaseModel):
    post_id: int
    type: Literal["ministry_service_ser","services","useful-numbers-post"]
    url: str
    title_ar: str
    title_en: str | None
    ministry_term: str | None          # taxonomy slug, e.g. "agriculture"
    modified_gmt: str                   # ISO; VERIFIED present on all 3 types

class Sections(BaseModel):
    required_documents: list[str] | None   # None => extraction failed
    fees: str | None
    processing_time: str | None
    where_to_apply: str | None
    authority: str | None
    steps: str | None

class CorpusRecord(CatalogRecord):
    raw_text: str
    sections: Sections
    crawled_at: str
    modified_gmt_at_crawl: str          # snapshot of source's modified_gmt (freshness basis)
    content_hash: str                   # sha256(canonical normalized text) — recrawl-diff ONLY
    record_status: Literal["complete","incomplete"]   # incomplete if sections.required_documents is None (FR12)

class ContactRecord(BaseModel):        # A27: crawled from /en/directory (client-rendered; NOT in REST)
    source: Literal["useful-numbers-post","ministires_directory"]
    authority_name_ar: str
    authority_term: str | None          # normalized key for authority↔service mapping
    phones: list[str]
    address: str | None
    url: str
    crawled_at: str

# ---- retrieval / research ----
class RetrievedCandidate(BaseModel):
    post_id: int; title_ar: str; title_en: str | None
    rrf_score: float; dense_cos: float; bm25_rank: int | None

class FreshnessResult(BaseModel):      # A08: change-detection status, NOT a currentness guarantee
    status: Literal["unchanged","changed","unverified"]  # renamed from fresh/stale to be honest
    source_modified_gmt: str | None
    snapshot_modified_gmt: str
    checked_at: str
    note: str                          # e.g. "unchanged since snapshot 2026-07-21; substantive currency not guaranteed"

class LiveLookupResult(BaseModel):     # N6: typed output of live_service_lookup (2nd external call)
    query: str
    exists: bool                       # did the live REST search return any match?
    newest_post_id: int | None
    newest_modified_gmt: str | None
    is_newer: bool                     # live newest_modified_gmt > our snapshot for the chosen service
    # Consumer (N6): is_newer=True => composer adds review_reasons "newer_version_available"
    #   + needs_human_review=True + a caveat. exists=False for the retrieved service => same flag
    #   (our snapshot may reference a service removed live).

# ---- LLM output shapes (N2: these ARE part of the single source of truth; validated per FR9) ----
class IntentResult(BaseModel):         # intent_classifier output
    intent: Literal["service_query","follow_up","invalid_request"]
    reason: str
    language_advisory: Literal["ar","en"]

class PlanStep(BaseModel):
    tool: Literal["resolve_document","check_freshness","live_service_lookup"]  # invalid name => validation error
    args: dict

class ResearchPlan(BaseModel):         # research_agent output (per loop turn)
    plan: list[PlanStep]
    done: bool

class Duration(BaseModel):             # A10: explicit unit handling
    min_val: float | None; max_val: float | None
    unit: Literal["business_days","calendar_days","weeks","months","unknown"]
    # No cross-unit arithmetic. Aggregation combines only same-unit values;
    # mixed units are reported component-wise, never summed into one number.

class ResolvedDocument(BaseModel):     # A11: provenance + abstention
    name_ar: str; name_en: str | None; name_en_gloss: str | None
    resolution: Literal["corpus","lookup_table","unresolved"]
    match_score: float | None          # normalized 0-1; below θ_doc => forced "unresolved"
    where_to_obtain: str | None
    fees: str | None
    duration: Duration | None
    source_url: str | None
    verified_on: str | None            # lookup rows carry this; TTL 180d (A08) -> else freshness="unverified"
    freshness: FreshnessResult | None
    needs_human_review: bool           # True if unresolved OR match ambiguous OR source stale

# ---- output (discriminated union on `action`) ----
class Envelope(BaseModel):
    action: Literal["answer","clarification_needed","service_not_found","invalid_request","error"]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)   # brief mandates this field name; see FR7 note
    language: Literal["ar","en"]
    needs_human_review: bool
    review_reasons: list[Literal["stale_source","unverified_source","unresolved_document",
                                 "incomplete_record","schema_retry","ambiguous_match",
                                 "newer_version_available"]]   # N6: set when LiveLookupResult.is_newer
    output: AnswerOut | ClarifyOut | NotFoundOut | InvalidOut | ErrorOut  # per action

class ServiceOut(BaseModel):
    name_ar: str; name_en: str | None; name_en_gloss: str | None
    source_url: str; authority: str | None
    fees: str | None; stated_processing: Duration | None
    where_to_apply: str | None
    contacts: list[ContactOut]         # may be [] (contacts are best-effort local enrichment)
    freshness: FreshnessResult
    record_status: Literal["complete","incomplete"]

class ContactOut(BaseModel):
    authority_name_ar: str; phones: list[str]; address: str | None; source_url: str

class TimeEstimate(BaseModel):
    computable: bool                   # False when units are mixed/unknown (A10)
    total_min_days: float | None; total_max_days: float | None
    is_lower_bound: bool
    breakdown: list[BreakdownStep]     # always present; UI shows component-wise if not computable

class BreakdownStep(BaseModel):
    step: str; duration: Duration

class AnswerOut(BaseModel):
    service: ServiceOut
    required_documents: list[ResolvedDocument]
    time_estimate: TimeEstimate
    caveats: list[str]

class ClarifyOut(BaseModel):
    question: str
    candidates: list[Candidate]        # 2..3
class NotFoundOut(BaseModel):
    message: str; suggestions: list[Candidate]   # exactly 3
class Candidate(BaseModel):
    name_ar: str; name_en: str | None; url: str
class InvalidOut(BaseModel):
    reason_code: Literal["legal_advice","bribery","out_of_jurisdiction","pii","injection","gibberish"]
    message: str
class ErrorOut(BaseModel):
    stage: str; detail: str

# ---- HITL queue (A09: append-only, nullable subject) ----
class QueueEvent(BaseModel):
    event_id: str                      # uuid4
    event_type: Literal["stale_source","unreachable_source","unresolved_document",
                        "extraction_incomplete","changed_on_recrawl"]
    subject_post_id: int | None        # None for unresolved documents that are not a known service
    subject_label: str                 # always human-readable (doc name or service title)
    source_url: str | None
    detected_at: str
    source: Literal["agent","recrawl"]
    status: Literal["open","resolved"]
    details: str
```

**Queue write discipline (A09):** one append-only file `data/review_queue.jsonl`, one line per
event, written with an OS file lock (`portalocker`), append mode only (never rewrite). Dedupe key
= `(event_type, subject_post_id or subject_label, status="open")` checked by a single reader pass;
concurrent research-loop writers serialize on the lock.

## 2. Confidence field (A23 — brief mandates the name)

The brief's output schema fixes the field name `confidence: float 0.0–1.0`, so we keep it. It is
computed by the FR7 formula and is an **evidence-quality heuristic, not a calibrated probability**
— the report and a `confidence_basis` sentence in `caveats` disclose this explicitly. We do not
claim probabilistic meaning.

## 3. Gold oracle (A03 — separate from verification sheet)

`core_verification.csv` = human review evidence (reviewer/date/`*_ok`/discrepancies) — NOT the
oracle. The eval oracle is `tests/gold_claims.json`, seeded from the verified core:

```json
{
  "case_id": "normal_passport_en",
  "query": "How do I renew my Lebanese passport?",
  "lang": "en",
  "expected_action": "answer",
  "gold": {
    "service_post_id": 11634,
    "required_documents_ar": ["إخراج قيد إفرادي", "بطاقة هوية", "صورتان"],
    "accepted_variants": {"إخراج قيد إفرادي": ["اخراج قيد افرادي","إخراج قيد فردي"]},
    "fees": "…", "authority": "الأمن العام",
    "stated_processing": {"min_val": 5, "max_val": 10, "unit": "business_days"},
    "null_fields": []
  }
}
```
Matching: doc set = normalized-Arabic exact-set match (strip diacritics/tatweel, unify alef/ya,
collapse whitespace) allowing `accepted_variants`; fees/authority = normalized string match;
duration = value+unit match; `null_fields` must be null in output (not invented). URL-membership
stays as a separate provenance check, never the correctness metric.
