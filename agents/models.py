"""Single source of truth for all data shapes (implements ../Final Project/SCHEMA_AND_CONTRACTS.md).

Every LLM output and pipeline record is one of these Pydantic models (FR9). Imported by nodes,
tools, the Streamlit UI, and the eval harness — nothing passes untyped dicts across a stage.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------------- ingestion
class CatalogRecord(BaseModel):
    post_id: int
    type: Literal["ministry_service_ser", "services", "useful-numbers-post"]
    url: str
    title_ar: str
    title_en: Optional[str] = None
    ministry_term: Optional[str] = None
    modified_gmt: str  # verified present on all 3 post types


class Sections(BaseModel):
    required_documents: Optional[list[str]] = None  # None => extraction failed
    fees: Optional[str] = None
    processing_time: Optional[str] = None
    where_to_apply: Optional[str] = None
    authority: Optional[str] = None
    steps: Optional[str] = None


class CorpusRecord(CatalogRecord):
    raw_text: str
    sections: Sections
    crawled_at: str
    modified_gmt_at_crawl: str
    content_hash: str  # sha256(canonical normalized text) — recrawl-diff ONLY
    record_status: Literal["complete", "incomplete"]


class ContactRecord(BaseModel):  # A27: crawled from /en/directory (NOT in REST)
    source: Literal["useful-numbers-post", "ministires_directory"]
    authority_name_ar: str
    authority_term: Optional[str] = None
    phones: list[str] = Field(default_factory=list)
    address: Optional[str] = None
    url: str
    crawled_at: str


# ---------------------------------------------------------------- retrieval / research
class RetrievedCandidate(BaseModel):
    post_id: int
    title_ar: str
    title_en: Optional[str] = None
    rrf_score: float
    dense_cos: float
    bm25_rank: Optional[int] = None


class FreshnessResult(BaseModel):  # A08: change-detection, NOT a currentness guarantee
    status: Literal["unchanged", "changed", "unverified"]
    source_modified_gmt: Optional[str] = None
    snapshot_modified_gmt: str
    checked_at: str
    note: str


class LiveLookupResult(BaseModel):  # N6: typed output of the 2nd external call
    query: str
    exists: bool
    newest_post_id: Optional[int] = None
    newest_modified_gmt: Optional[str] = None
    is_newer: bool = False


class Duration(BaseModel):  # A10: explicit units; no cross-unit arithmetic
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: Literal["business_days", "calendar_days", "weeks", "months", "unknown"] = "unknown"


class ResolvedDocument(BaseModel):  # A11: provenance + abstention
    name_ar: str
    name_en: Optional[str] = None
    name_en_gloss: Optional[str] = None
    resolution: Literal["corpus", "lookup_table", "unresolved"]
    match_score: Optional[float] = None
    where_to_obtain: Optional[str] = None
    fees: Optional[str] = None
    duration: Optional[Duration] = None
    source_url: Optional[str] = None
    verified_on: Optional[str] = None
    freshness: Optional[FreshnessResult] = None
    needs_human_review: bool = False


# ---------------------------------------------------------------- LLM output shapes (N2)
class IntentResult(BaseModel):
    intent: Literal["service_query", "follow_up", "invalid_request"]
    reason: str
    language_advisory: Literal["ar", "en"]


class PlanStep(BaseModel):
    tool: Literal["resolve_document", "check_freshness", "live_service_lookup"]
    args: dict


class ResearchPlan(BaseModel):
    plan: list[PlanStep]
    done: bool


# ---------------------------------------------------------------- output (discriminated on `action`)
ReviewReason = Literal[
    "stale_source", "unverified_source", "unresolved_document",
    "incomplete_record", "schema_retry", "ambiguous_match", "newer_version_available",
]


class ContactOut(BaseModel):
    authority_name_ar: str
    phones: list[str] = Field(default_factory=list)
    address: Optional[str] = None
    source_url: str


class ServiceOut(BaseModel):
    name_ar: str
    name_en: Optional[str] = None
    name_en_gloss: Optional[str] = None
    source_url: str
    authority: Optional[str] = None
    fees: Optional[str] = None
    stated_processing: Optional[Duration] = None
    where_to_apply: Optional[str] = None
    contacts: list[ContactOut] = Field(default_factory=list)
    freshness: FreshnessResult
    record_status: Literal["complete", "incomplete"]


class BreakdownStep(BaseModel):
    step: str
    duration: Duration


class TimeEstimate(BaseModel):
    computable: bool
    total_min_days: Optional[float] = None
    total_max_days: Optional[float] = None
    is_lower_bound: bool = False
    breakdown: list[BreakdownStep] = Field(default_factory=list)


class Candidate(BaseModel):
    name_ar: str
    name_en: Optional[str] = None
    url: str


class AnswerOut(BaseModel):
    service: ServiceOut
    required_documents: list[ResolvedDocument] = Field(default_factory=list)
    time_estimate: TimeEstimate
    caveats: list[str] = Field(default_factory=list)


class ClarifyOut(BaseModel):
    question: str
    candidates: list[Candidate]  # 2..3


class NotFoundOut(BaseModel):
    message: str
    suggestions: list[Candidate]  # exactly 3


class InvalidOut(BaseModel):
    reason_code: Literal["legal_advice", "bribery", "out_of_jurisdiction", "pii", "injection", "gibberish"]
    message: str


class ErrorOut(BaseModel):
    stage: str
    detail: str


class Envelope(BaseModel):
    action: Literal["answer", "clarification_needed", "service_not_found", "invalid_request", "error"]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)  # brief-mandated name; evidence-quality heuristic (A23)
    language: Literal["ar", "en"]
    needs_human_review: bool = False
    review_reasons: list[ReviewReason] = Field(default_factory=list)
    output: AnswerOut | ClarifyOut | NotFoundOut | InvalidOut | ErrorOut


# ---------------------------------------------------------------- HITL queue (A09)
class QueueEvent(BaseModel):
    event_id: str
    event_type: Literal[
        "stale_source", "unreachable_source", "unresolved_document",
        "extraction_incomplete", "changed_on_recrawl",
    ]
    subject_post_id: Optional[int] = None  # None for a doc that isn't a known service
    subject_label: str
    source_url: Optional[str] = None
    detected_at: str
    source: Literal["agent", "recrawl"]
    status: Literal["open", "resolved"] = "open"
    details: str = ""
