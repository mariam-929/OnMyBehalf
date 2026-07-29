"""External-source fallback: answer from another official government site when Dawlati cannot.

WHY THIS EXISTS
---------------
Report §2 records that passports and driving licences are simply not on Dawlati — the only
«جواز سفر» record in the whole corpus is «إصدار جواز سفر للخيل», a horse passport. So the single
most-asked transaction in the country terminates in `service_not_found`, correctly but uselessly.
The documents DO exist, published by the authority that actually issues them: the General
Directorate of General Security.

WHERE IT FIRES — AND WHERE IT CANNOT
------------------------------------
Only on the `not_found` branch, i.e. exactly where the graph already gives up. It is unreachable
from any path that produces an answer today, so **no currently-passing case can regress through
this module**. That is a structural property of the wiring (agents/graph.py), not a test result.

THE ARCHITECTURE RULE IS UNCHANGED: the model writes LANGUAGE, code owns FACTS.
Nothing here is model-driven. The query→source mapping is a hand-curated REGISTRY of three URLs
that a human verified; extraction is deterministic regex over the published HTML, the same house
style as tools/crawler/fetch_service_directory.py. No LLM reads this HTML and no LLM chooses the
URL. Adding a model to either step would reintroduce exactly the fabrication risk the project is
built to exclude.

WHY A SNAPSHOT AND A LIVE FETCH
-------------------------------
Measured 2026-07-28: general-security.gov.lb answers plain `requests` + a browser UA with 200 in
**2.0–7.7 s** (6/6 over one minute) — but an earlier attempt died in the TLS handshake at 10 s.
That variance is fine for a crawler and unacceptable on the critical path of a live 8-minute demo.
So: a committed snapshot always answers, and a live fetch (short timeout) upgrades it when the
network cooperates. `FreshnessResult` then states WHICH one served, so the honesty guarantee
covers the fallback itself rather than papering over it.

PROVENANCE IS NEVER LAUNDERED
-----------------------------
Records built here carry `post_id=None` (there is no Dawlati post), `type="external_gov_site"`
and a `source_domain`. `post_id=None` also means agents/nodes/research.py skips `check_freshness`,
which would otherwise ask Dawlati's REST API about an ID that is not Dawlati's — attaching one
site's freshness to another site's facts.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from tools.crawler.fetch_service_directory import html_to_lines
from tools.text_norm import normalize_ar

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "data" / "external"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Short on purpose. The demo budget is ~8 s per question end to end and the composer already owns
# 8 s of it; a slow external site must lose to the snapshot rather than stall the answer. Same
# reasoning as the 6 s/8 s model timeouts — do not raise these to "improve coverage".
LIVE_TIMEOUT_S = 4.0

SOURCE_DOMAIN = "general-security.gov.lb"


# ---------------------------------------------------------------- the curated registry
# Three URLs, each opened and read by a human on 2026-07-28. This is a lookup table, not a
# crawler: adding an entry means a person verified that the page publishes the documents it
# claims to. `qualifiers` disambiguate within a subject — matched BEFORE the base entry so
# "lost passport" never resolves to the ordinary issuance procedure.
REGISTRY: list[dict] = [
    {
        "key": "passport_certify_copies",
        "subject_ar": ["جواز سفر", "جواز السفر", "باسبور"],
        "subject_en": ["passport"],
        "qualifiers_ar": ["تصديق", "مصدقة", "نسخة", "صورة طبق", "صفحات"],
        "qualifiers_en": ["certif", "copies", "copy", "pages"],
        "title_ar": "تصديق صور عن صفحات جواز السفر",
        "title_en": "Certifying copies of passport pages",
        "url_ar": "https://www.general-security.gov.lb/ar/posts/86",
        "url_en": "https://www.general-security.gov.lb/en/posts/86",
    },
    {
        "key": "passport_modify",
        "subject_ar": ["جواز سفر", "جواز السفر", "باسبور"],
        "subject_en": ["passport"],
        "qualifiers_ar": ["تعديل", "تصحيح", "اسم اجنبي", "لغة اجنبية"],
        "qualifiers_en": ["modif", "correct", "letters", "spelling"],
        "title_ar": "تعديل بعض الأحرف في جواز السفر",
        "title_en": "Modification of some letters",
        "url_ar": "https://www.general-security.gov.lb/ar/posts/76",
        "url_en": "https://www.general-security.gov.lb/en/posts/76",
    },
    {
        # BASE entry — no qualifiers, so it matches any passport question the two above did not.
        # Must stay LAST: _match returns the first hit and specificity is expressed by order.
        "key": "passport_biometric",
        "subject_ar": ["جواز سفر", "جواز السفر", "باسبور"],
        "subject_en": ["passport"],
        "qualifiers_ar": [],
        "qualifiers_en": [],
        "title_ar": "جواز سفر بيومتري",
        "title_en": "Biometric passport",
        "url_ar": "https://www.general-security.gov.lb/ar/posts/11",
        "url_en": "https://www.general-security.gov.lb/en/posts/11",
    },
]

# An explicit animal term means the citizen wants Dawlati's «إصدار جواز سفر للخيل», not a human
# passport. Kept as one flat list rather than per-entry: every registry entry is currently a
# passport procedure, and a term that disqualifies one disqualifies all of them.
EXCLUDE_TERMS = ("خيل", "خيول", "حصان", "احصنة", "أحصنة", "حيوان", "حيوانات", "بهيمة",
                 "horse", "horses", "equine", "animal", "livestock")

AUTHORITY_AR = "المديرية العامة للأمن العام"
AUTHORITY_EN = "General Directorate of General Security"
WHERE_AR = "المراكز الإقليمية للأمن العام"
WHERE_EN = "General Security regional centres"


def _match(query: str, language: str) -> dict | None:
    """Return the registry entry this query is about, or None. Deliberately conservative.

    A miss costs the citizen nothing (they get today's `service_not_found`); a false hit would
    answer a question about service A with the documents for service B. So the SUBJECT must be
    present — a bare "I lost it" resolves to nothing.

    EXCLUSIONS exist because Dawlati publishes «إصدار جواز سفر للخيل» — a HORSE passport — and it
    is the only «جواز سفر» record in the corpus. A citizen asking about a horse passport must still
    be served that Dawlati record, so an explicit animal term vetoes the registry and lets ordinary
    retrieval answer.
    """
    q = normalize_ar(query or "")
    if not q:
        return None
    if any(normalize_ar(x) in q for x in EXCLUDE_TERMS):
        return None
    subj_key = "subject_en" if language == "en" else "subject_ar"
    qual_key = "qualifiers_en" if language == "en" else "qualifiers_ar"

    for entry in REGISTRY:
        # Subject terms are matched in BOTH languages: an Arabic query can carry the Latin word
        # "passport" and English queries from Arabic speakers frequently carry «جواز».
        subjects = [normalize_ar(s) for s in (entry["subject_ar"] + entry["subject_en"])]
        if not any(s and s in q for s in subjects):
            continue
        quals = [normalize_ar(x) for x in entry[qual_key]]
        if not quals:                       # the base entry matches on subject alone
            return entry
        if any(x and x in q for x in quals):
            return entry
        # also accept the other language's qualifiers — see note above
        other = [normalize_ar(x) for x in entry["qualifiers_ar" if qual_key.endswith("en")
                                                else "qualifiers_en"]]
        if any(x and x in q for x in other):
            return entry
    return None


# ---------------------------------------------------------------- extraction (deterministic)
# The body lives in `<div id="post-container">`. Bounded at the sidebar/footer so the "Related
# Links" list of sibling procedures can never be mistaken for document content.
_CONTAINER = re.compile(
    r'<div\s+id="post-container".*?>(.*?)(?:<div\s+id="post-right-side"|<div\s+id="footer"'
    r"|<footer|</body>)", re.S | re.I)

# Section headings are emphasised paragraphs: <p><strong><u>Requested documents:</u></strong></p>
# The AR page adds applicant sub-headings («بالنسبة للراشدين» / «بالنسبة للقاصرين») in the same
# shape — those are NOT section breaks, they are branch markers, and they must reach `raw_text`
# so tools/conditional_detect.py can flag the branch (_BRANCH already matches «بالنسبة ل»).
#
# `<div>` is accepted as well as `<p>`: /ar/posts/76 opens with its lead-in inside a bare <div>,
# and a <p>-only scan identified no section at all, silently dropping all four documents while the
# <p>-based EN twin of the same page extracted fine. A structural difference between two
# translations of one page is exactly the kind of thing that passes review and fails live.
_HEADING_BLOCK = re.compile(
    r"<(?:p|div)[^>]*>\s*(?:<[^>]+>\s*)*((?:(?!</(?:p|div)>).)*?)\s*(?:</[^>]+>\s*)*</(?:p|div)>",
    re.S | re.I)
_LI = re.compile(r"<li[^>]*>(.*?)</li>", re.S | re.I)
_TABLE = re.compile(r"<table.*?</table>", re.S | re.I)

# «المستندات التالية» (/ar/posts/76) is as much a document heading as «المستندات المطلوبة».
_DOCS_MARKER = re.compile(
    r"requested\s+documents|following\s+documents"
    r"|المستندات\s+(?:المطلوبة|التالية)|الوثائق\s+(?:المطلوبة|التالية)|تعتمد\s+المستندات", re.I)
# «الرسوم الشمسية» is PHOTOGRAPHS, not fees — /ar/posts/11 uses it for the photo specification.
# A bare «رسوم» match would file the passport photo rules under the fee the citizen must pay.
_FEES_MARKER = re.compile(r"^\s*fees\b|(?:ال)?رسوم(?!\s*(?:ال)?شمسي)", re.I)
_NOTES_MARKER = re.compile(r"remarks|ملاحظ", re.I)


def _text(fragment: str) -> str:
    return " ".join(html_to_lines(fragment))


def extract_sections(html: str) -> dict:
    """Published HTML -> the same Sections shape the Dawlati ingester produces.

    Returns required_documents=None (never []) when nothing could be extracted, so the caller can
    tell "no documents published" from "extraction failed" — the FR12 distinction that drives
    record_status.
    """
    body_m = _CONTAINER.search(html or "")
    body = body_m.group(1) if body_m else ""
    if not body:
        return {"required_documents": None, "fees": None, "notes": None, "raw_text": ""}

    # Split the body into (heading, content) runs in document order.
    marks = [(m.start(), _text(m.group(1))) for m in _HEADING_BLOCK.finditer(body)]
    marks = [(pos, h) for pos, h in marks if h]

    docs: list[str] = []
    fees_parts: list[str] = []
    notes_parts: list[str] = []
    raw_lines: list[str] = []
    section = None

    for i, (pos, heading) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        chunk = body[pos:end]

        # A heading only switches section when it names one; anything else (e.g. the AR applicant
        # sub-headings) stays inside the current section and is kept as branch evidence.
        if _DOCS_MARKER.search(heading):
            section = "docs"
        elif _FEES_MARKER.search(heading):
            section = "fees"
        elif _NOTES_MARKER.search(heading):
            section = "notes"
        raw_lines.append(heading)

        items = [_text(li) for li in _LI.findall(chunk)]
        items = [x for x in items if x]
        raw_lines.extend(items)

        if section == "docs":
            docs.extend(items)
        elif section == "fees":
            fees_parts.extend(items)
            for tbl in _TABLE.findall(chunk):
                rows = [ln for ln in html_to_lines(tbl) if ln]
                fees_parts.extend(rows)
                raw_lines.extend(rows)
        elif section == "notes":
            notes_parts.extend(items)

    # Last resort: a page whose lead-in matched no marker at all, but which carries a bulleted
    # list. On this site a <ul> on a procedure page IS the requirements list. Guarded by
    # `section is None` so it can never swallow the "Remarks" bullets on a page that DID declare
    # its sections (e.g. /posts/11, where Remarks and Fees follow the documents).
    if not docs and section is None:
        docs = [x for x in (_text(li) for li in _LI.findall(body)) if x]

    # NO last-resort sweep for fees. An earlier version fell back to "any <table> in the body" when
    # no fees section was found, and on /posts/14 and /posts/86 that captured the site's own
    # CONTACT DIRECTORY — "Beirut Port center 01/584400" would have been rendered to a citizen as
    # the fee for the service. A missing fee is a null the UI can state plainly; an invented one is
    # the failure this project exists to prevent. Fees come from a declared fees section or nowhere.

    return {
        "required_documents": docs or None,
        "fees": "\n".join(fees_parts) or None,
        "notes": "\n".join(notes_parts) or None,
        "raw_text": "\n".join(raw_lines),
    }


# ---------------------------------------------------------------- fetch (snapshot + live)
# A requirement line starts with the THING being required. A condition starts with the
# circumstance under which it applies. That is the whole rule, and it is lexical rather than
# semantic — the head-noun list is the one already validated for the conjoined-document split in
# tools/crawler/fetch_service_directory.py, extended with the identity nouns this source uses.
_DOC_START = re.compile(
    r"^\s*(?:صور[ةه]|وثيق[ةه]|بيان|شهاد[ةه]|[إا]فاد[ةه]|محضر|تقرير|طلب|نسخ[ةه]|[إا]قام[ةه]"
    r"|هوي[ةه]|جواز|[إا]خراج\s+قيد|مستند|بطاق[ةه]|رخص[ةه]|سند|وكال[ةه]"
    r"|the\s|a\s|an\s|copy|application|photo|certificate|passport|permit)", re.I)


# A condition sentence can still NAME a required document, in parentheses. On /ar/posts/11 the
# identity requirement is «… تحدّد ضوابط قبول المستند الثبوتي اللبناني ( هوية و/أو إخراج قيد ) …» —
# a real requirement (the English twin lists it as its own bullet, and /ar/posts/408 restates it),
# buried in a sentence that opens with «عند», so the head-noun test filed the whole line as a
# condition and the citizen lost a requirement.
#
# Extract the parenthesised group only when it looks like a NAME rather than a clause: it must
# start with a document head-noun, be short, and contain no temporal or conditional markers. The
# family-exception on the same page — «(هوية أو بيان قيد إفرادي لا يعود تاريخه لأكثر من سنة واحدة)»
# — is deliberately NOT extracted: it carries «لا يعود تاريخه», so it is a case-specific rule, not
# a document name, and hoisting it would put a second near-duplicate ID line in the checklist.
_PAREN_GROUP = re.compile(r"[（(]\s*([^)）]{3,45})\s*[)）]")
_CLAUSE_MARKER = re.compile(r"لا\s+يعود|في\s+حال|إذا|اذا|بشرط|لأكثر\s+من|اكثر\s+من")


def _document_inside(line: str) -> str | None:
    """The document named in parentheses inside a condition line, or None."""
    for match in _PAREN_GROUP.finditer(line or ""):
        inner = match.group(1).strip()
        if _DOC_START.match(inner) and not _CLAUSE_MARKER.search(inner):
            return inner
    return None


def split_documents_and_conditions(lines: list[str] | None) -> tuple[list[str], list[str]]:
    """Separate the papers a citizen collects from the conditions governing them.

    WHY. General Security's Arabic page puts both in one <ul>: «طلب جواز سفر…» (a document) sits
    beside «لا يُمنح القاصر دون الثامنة عشرة من العمر جواز سفر إلا بعد حيازته على موافقة الوالدين»
    (a rule). Measured on /ar/posts/11: 3 of 13 lines are documents and 10 are conditions. Listing
    all 13 as "required documents" asks the citizen to go and collect a sentence, and it is why
    every one of them reported that its source was unknown — a condition HAS no issuing office.

    Conditions are NEVER discarded. They carry things that change what a citizen must do — parental
    consent for a minor, the three-month validity of a travel permit — and dropping them would be
    the silent truncation this project treats as its worst failure (PROGRESS 2026-07-27). They are
    returned separately so the answer can show them as conditions instead of as papers.
    """
    documents: list[str] = []
    conditions: list[str] = []
    for line in lines or []:
        text = (line or "").strip()
        if not text:
            continue
        if _DOC_START.match(text):
            documents.append(text)
            continue
        conditions.append(text)
        # The line stays a condition — it genuinely carries one — but a document named inside it
        # is also surfaced as a requirement, because the citizen has to bring it.
        if (inner := _document_inside(text)) and inner not in documents:
            documents.append(inner)
    return documents, conditions


def _snapshot_path(key: str, language: str) -> Path:
    return SNAPSHOT_DIR / f"{key}.{language}.html"


def _load_snapshot(key: str, language: str) -> tuple[str | None, str | None]:
    """Returns (html, captured_at_iso). Committed to the repo so `--offline` and a fresh clone
    both work without a network round trip."""
    path = _snapshot_path(key, language)
    if not path.exists():
        return None, None
    html = path.read_text(encoding="utf-8", errors="replace")
    # `+` is load-bearing: datetime.isoformat() emits a UTC offset ("...T21:57:03+00:00") and a
    # class without it matched up to the `+`, then failed on the required `-->` and returned None —
    # so every snapshot-served answer told the citizen it was "captured unknown".
    stamp = re.search(r"<!--\s*captured_at:\s*([0-9TZ:.+\-]+)\s*-->", html)
    return html, (stamp.group(1) if stamp else None)


def _fetch_live(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=LIVE_TIMEOUT_S)
        r.raise_for_status()
        return r.text
    except Exception:  # noqa: BLE001 — a flaky external site degrades to the snapshot, never fails
        return None


def external_lookup(query: str, language: str = "ar", allow_live: bool = True) -> dict | None:
    """The whole fallback: query -> a service_record dict, or None when nothing matches.

    Shaped as a CorpusRecord dict (plain `.get()` access downstream), NOT validated as one:
    `CatalogRecord.post_id` is a required int and `type` is a Literal over the three Dawlati post
    types, neither of which an external record can honestly satisfy.
    """
    entry = _match(query, language)
    if entry is None:
        return None

    url = entry["url_en"] if language == "en" else entry["url_ar"]
    html, captured_at = _load_snapshot(entry["key"], language)
    served_from, live_html = "snapshot", None

    if allow_live:
        live_html = _fetch_live(url)
        if live_html:
            html, served_from = live_html, "live"

    if not html:
        return None  # no snapshot and the site is unreachable — honest silence

    sections = extract_sections(html)
    if not sections["required_documents"] and served_from == "live" and not live_html:
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fetched_at = now if served_from == "live" else (captured_at or "")

    documents, conditions = split_documents_and_conditions(sections["required_documents"])

    return {
        "post_id": None,                     # not a Dawlati post — keeps check_freshness away
        "type": "external_gov_site",
        "url": url,
        "title_ar": entry["title_ar"],
        "title_en": entry["title_en"],
        "raw_text": sections["raw_text"],
        # Conditions travel beside the record so compose can put them in the answer as conditions.
        "conditions": conditions,
        "sections": {
            "required_documents": documents or None,
            "fees": sections["fees"],
            "processing_time": None,
            "where_to_apply": WHERE_EN if language == "en" else WHERE_AR,
            "authority": AUTHORITY_EN if language == "en" else AUTHORITY_AR,
            "steps": sections["notes"],
        },
        "crawled_at": fetched_at,
        "modified_gmt": "",
        "modified_gmt_at_crawl": "",
        "content_hash": "",
        "record_status": "complete" if sections["required_documents"] else "incomplete",
        # --- external-only provenance, read by the composer and the UI badge ---
        "source_domain": SOURCE_DOMAIN,
        "external_key": entry["key"],
        "served_from": served_from,
        "fetched_at": fetched_at,
    }


def record_for_url(url: str) -> dict | None:
    """The external record a cited URL refers to, rebuilt from the committed snapshot.

    Exists so an auditor — the eval harness, a reviewer — can verify an answer's documents against
    the source the answer actually cites. Snapshot only: an audit must be reproducible and must not
    depend on the site being up, or on it having changed since the answer was produced.
    """
    for entry in REGISTRY:
        for language in ("ar", "en"):
            if entry[f"url_{language}"] != url:
                continue
            html, captured_at = _load_snapshot(entry["key"], language)
            if not html:
                return None
            sections = extract_sections(html)
            return {
                "url": url,
                "title_ar": entry["title_ar"],
                "title_en": entry["title_en"],
                "raw_text": sections["raw_text"],
                "sections": sections,
                "source_domain": SOURCE_DOMAIN,
                "captured_at": captured_at,
            }
    return None


def abstained_documents(record: dict) -> list[dict]:
    """External documents, all marked `unresolved` — resolution is NOT offered for these in v1.

    MEASURED, on the flagship record (/ar/posts/11, 2026-07-28): of 13 extracted lines, exactly one
    resolved against the Dawlati corpus — and it was WRONG. «أما بالنسبة لطلبات عائلات عسكريي الأمن
    العام…» is a rule about who may submit fewer documents, not a document, and it was attributed to
    «المديرية العامة للأحوال الشخصية» at 0.6367 while a genuine line scored 0.7004 and abstained. So
    the score does not separate right from wrong here and a threshold cannot be tuned on it — the
    same conclusion `accept_rescue` reached for alias retries, for the same reason.

    The cause is structural, not a resolver defect: this source nests procedural RULES under an
    applicant heading, inside the same <ul> as the documents, so the extracted list is a mixture and
    the resolver has no signal to tell a document from a rule.

    FR4 says abstain rather than attach a doubtful source. One wrong `where_to_obtain` on screen
    costs more than thirteen honest "not resolved" — so per-document resolution stays a Dawlati-only
    capability until an external record can be split into documents and rules reliably.
    """
    return [
        {
            "name_ar": name,
            "name_en": None,
            "name_en_gloss": None,
            "resolution": "unresolved",
            "match_score": None,
            "where_to_obtain": None,
            "fees": None,
            "duration": None,
            "source_url": record.get("url"),
            "verified_on": None,
            "freshness": None,
            "needs_human_review": True,
        }
        for name in ((record.get("sections") or {}).get("required_documents") or [])
    ]


def external_freshness(record: dict) -> dict:
    """A FreshnessResult dict for an external record.

    Always `unverified`, and that is the truthful answer rather than a limitation: `unchanged`
    means "modified_gmt matches the value stored at crawl time" (A08), and this source publishes
    no modification timestamp to compare against. The note carries what we DO know — whether the
    bytes came off the live site in this run or out of the committed snapshot.
    """
    served = record.get("served_from", "snapshot")
    at = record.get("fetched_at") or "unknown"
    note = (f"Fetched live from {record.get('source_domain')} at {at}. This source publishes no "
            "modification timestamp, so change-detection is not possible."
            if served == "live" else
            f"Served from the committed snapshot captured {at}; the live site was not reachable "
            "within the timeout. Verify against the official page before acting.")
    return {
        "status": "unverified",
        "source_modified_gmt": None,
        "snapshot_modified_gmt": "",
        "checked_at": at,
        "note": note,
    }
