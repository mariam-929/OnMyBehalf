"""OnMyBehalf Streamlit UI — projector-legible, evidence-first, RTL-safe.

This interface deliberately separates:
  * MODEL-WRITTEN ORIENTATION (`summary`) from
  * RECORD-DERIVED FACTS (documents, fees, offices, contacts, freshness) and
  * EXECUTION EVIDENCE (agent trace + raw JSON).

Security invariant (G9 / A29): every dynamic string that reaches an
`unsafe_allow_html=True` sink passes through the single `esc()` chokepoint.
Arabic/LTR direction is decided per string by `rtl()`.

Run:
    streamlit run app/streamlit_app.py
    streamlit run app/streamlit_app.py -- --offline
"""
from __future__ import annotations

import html
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep this above every agents.* import. The runtime reads GROQ_API_KEY at import time.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# Integration points required by the project brief. Do not move above load_dotenv().
from agents.runtime import answer as run_agent  # noqa: E402
from agents.runtime import get_adapter_or_none  # noqa: E402

OFFLINE = "--offline" in sys.argv

st.set_page_config(
    page_title="OnMyBehalf",
    page_icon="🇱🇧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Static presentation only. No network fonts, icon packs, CDNs, or JavaScript.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      :root {
        --omb-ink: #15202b;
        --omb-muted: #586474;
        --omb-line: #d9e0e7;
        --omb-soft: #f5f7f9;
        /* One source of truth for the chat field. Padding and typed text both inherit it. */
        --omb-field: #f5f7f9;
        --omb-blue: #155eef;
        --omb-green: #067647;
        --omb-amber: #b54708;
        --omb-red: #b42318;
      }

      .stApp {
        color: var(--omb-ink);
        background: #fbfcfd;
      }

      [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1240px;
        padding-top: 1.35rem;
        padding-bottom: 4rem;
      }

      [data-testid="stSidebar"] {
        border-right: 1px solid var(--omb-line);
      }

      [data-testid="stChatMessage"] {
        border: 1px solid var(--omb-line);
        border-radius: 16px;
        padding: 0.9rem 1rem;
        margin-bottom: 1rem;
        background: white;
      }

      [data-testid="stChatMessage"] p,
      [data-testid="stChatMessage"] li {
        font-size: 1.02rem;
        line-height: 1.65;
      }

      [data-testid="stMetricValue"] {
        font-size: 1.7rem;
      }

      [data-testid="stAlert"] {
        border-radius: 12px;
        font-size: 1rem;
      }

      [data-testid="stExpander"] {
        border: 1px solid var(--omb-line);
        border-radius: 12px;
        background: white;
      }

      [data-testid="stExpander"] summary p {
        font-size: 1rem;
        font-weight: 650;
      }

      [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--omb-line) !important;
        border-radius: 13px !important;
        background: #ffffff;
      }

      .omb-eyebrow {
        color: var(--omb-blue);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.15rem;
      }

      .omb-rule {
        height: 1px;
        background: var(--omb-line);
        margin: 1.1rem 0;
      }

      .omb-prose {
        border-left: 4px solid #98a2b3;
        background: #f8fafc;
        border-radius: 0 12px 12px 0;
        padding: 0.8rem 1rem;
        margin: 0.4rem 0 1rem 0;
      }

      .omb-conditional {
        border-left: 5px solid var(--omb-amber);
        background: #fff8eb;
        border-radius: 0 12px 12px 0;
        padding: 0.7rem 0.9rem;
        margin: 0.5rem 0;
      }

      .omb-abstain {
        border: 2px solid #f04438;
        background: #fff1f0;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        margin: 0.45rem 0 0.7rem 0;
      }

      .omb-small {
        color: var(--omb-muted);
        font-size: 0.88rem;
        line-height: 1.55;
      }

      .omb-tool-live {
        border-left: 5px solid var(--omb-blue);
        background: #eff4ff;
        border-radius: 0 10px 10px 0;
        padding: 0.55rem 0.8rem;
        margin: 0.4rem 0;
      }

      .omb-tool-local {
        border-left: 5px solid #667085;
        background: #f2f4f7;
        border-radius: 0 10px 10px 0;
        padding: 0.55rem 0.8rem;
        margin: 0.4rem 0;
      }

      .omb-action-title {
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.25;
        margin-bottom: 0.45rem;
      }

      div.stButton > button,
      div.stLinkButton > a {
        min-height: 44px;
        border-radius: 10px;
        font-weight: 650;
      }

      code {
        white-space: pre-wrap !important;
        overflow-wrap: anywhere;
      }

      /* The chat input is the one widget the citizen TYPES into, so its contrast cannot be left to
         the ambient theme. Set the box and the glyphs together, and set -webkit-text-fill-color as
         well: on WebKit that wins over `color` on a textarea, which is how typed text ended up
         invisible. .streamlit/config.toml pins the theme; this makes the input independent of it.

         The FIELD COLOUR IS DECLARED ONCE, on the outer wrapper, and every descendant is forced
         transparent. Streamlit nests several divs between the wrapper and the textarea, so colouring
         "the input" and "the textarea" separately left the padding one shade and the typed text
         another. Inheriting from a single declaration makes a mismatch impossible rather than
         merely fixed — there is no second value to drift. */
      [data-testid="stBottomBlockContainer"],
      [data-testid="stBottom"] {
        background: #fbfcfd !important;   /* page background, so the field reads as a field */
      }

      [data-testid="stChatInput"],
      [data-testid="stChatInputContainer"] {
        background: var(--omb-field) !important;
        border: 1px solid var(--omb-line) !important;
        border-radius: 12px !important;
      }

      /* Every nested wrapper, the textarea, and the send button inherit the one colour above. */
      [data-testid="stChatInput"] *,
      [data-testid="stChatInputContainer"] * {
        background: transparent !important;
        background-color: transparent !important;
      }

      [data-testid="stChatInput"] textarea,
      [data-testid="stChatInputContainer"] textarea {
        color: var(--omb-ink) !important;
        -webkit-text-fill-color: var(--omb-ink) !important;
        caret-color: var(--omb-blue) !important;
        font-size: 1.05rem !important;
      }

      [data-testid="stChatInput"] textarea::placeholder,
      [data-testid="stChatInputContainer"] textarea::placeholder {
        color: #7d8794 !important;
        -webkit-text-fill-color: #7d8794 !important;
        opacity: 1 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Security and data helpers
# ---------------------------------------------------------------------------
def esc(text: Any) -> str:
    """Single HTML-escaping chokepoint for every dynamic unsafe-HTML string."""
    return html.escape(str(text if text is not None else ""), quote=True)


def is_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06ff" for c in str(text or ""))


def rtl(text: Any, size: str = "1rem", weight: str = "400") -> str:
    """Escape and wrap one string with its own direction and alignment.

    `unicode-bidi: plaintext` keeps bidi control characters from affecting
    surrounding interface chrome. The text itself remains visible.
    """
    value = str(text if text is not None else "")
    direction = "rtl" if is_arabic(value) else "ltr"
    align = "right" if direction == "rtl" else "left"
    return (
        f'<div dir="{esc(direction)}" style="text-align:{esc(align)};font-size:{esc(size)};'
        f'font-weight:{esc(weight)};line-height:1.8;unicode-bidi:plaintext;'
        f'overflow-wrap:anywhere">{esc(value)}</div>'
    )


def safe_url(value: Any) -> str | None:
    """Return only an absolute HTTP(S) URL for native Streamlit link widgets."""
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return raw


def compact(value: Any, max_chars: int = 260) -> str:
    """Readable, bounded text for native code/text sinks (never unsafe HTML)."""
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value if value is not None else "")
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def status_update(container: Any, **kwargs: Any) -> None:
    """Update an `st.status` container, tolerating bare (context-free) execution.

    `st.status()` returns None when the script runs WITHOUT a ScriptRunContext — which is exactly
    how `tests/gates/check_g9.py` imports this module to unit-test `esc()` and `rtl()`. Calling
    `.update()` on that None raised AttributeError at import time and took the whole G9 gate down
    with it, including the escaping assertions. The app is unaffected under `streamlit run`; the
    gate is not, and a graded gate must not depend on being launched a particular way.
    """
    if container is not None:
        container.update(**kwargs)


@st.cache_resource(show_spinner=False)
def _warm() -> bool:
    """Load the local encoder and retrieval index once per server process."""
    from tools.search_services import search_services

    search_services("warm", k=1)
    return True


def corpus_meta() -> dict:
    core = ROOT / "data" / "curated_core.json"
    thresh = ROOT / "data" / "retrieval_thresholds.json"
    corpus_dir = ROOT / "data" / "corpus"

    n_core = _read_json(core).get("n_core", 0) if core.exists() else 0
    files = list(corpus_dir.glob("*.json")) if corpus_dir.exists() else []
    snapshot = "—"
    if files:
        snapshot = str(_read_json(files[0]).get("crawled_at") or "")[:10] or "—"

    return {
        "services": len(files),
        "core": n_core,
        "snapshot": snapshot,
        "calibrated": thresh.exists(),
    }


@st.cache_resource(show_spinner=False)
def current_model_mode() -> tuple[str, str]:
    """Return an honest short label and explanation for the wired runtime."""
    if OFFLINE:
        return "offline", "External calls are disabled; freshness is unverified."

    try:
        adapter = get_adapter_or_none()
    except Exception:  # noqa: BLE001 - inspection failure must not become a model claim
        return "unknown", "The UI could not inspect model wiring, so no model is claimed."

    if adapter is None:
        return (
            "fixture mode",
            "No GROQ_API_KEY-backed adapter is active; language/reasoning is deterministic.",
        )

    model_id = os.environ.get("MODEL_ID", "").strip()
    if model_id:
        return model_id, "A model adapter is wired for this process."
    return "configured adapter", "A model adapter is active; MODEL_ID is not reported."


def effective_freshness_status(freshness: dict | None) -> str:
    if OFFLINE:
        return "unverified"
    status = str((freshness or {}).get("status") or "unverified")
    return status if status in {"unchanged", "changed", "unverified"} else "unverified"


# ---------------------------------------------------------------------------
# Static semantic labels
# ---------------------------------------------------------------------------
_FLAG_LABEL = {
    "branch": (
        "Depends on who you are",
        "The source lists different requirements for different applicants. The list below merges cases, so confirm which branch applies to you.",
    ),
    "either_or": (
        "Alternatives, not extras",
        "Some items appear as «أو» alternatives. You may not need every listed item.",
    ),
    "precondition": (
        "Eligibility condition",
        "A condition must hold before this procedure can be used.",
    ),
    "recency": (
        "Document must be recent",
        "At least one document must have been issued within a stated time window.",
    ),
}

_RESOLUTION_LABEL = {
    "corpus": ("CONFIRMED IN CORPUS", "Matched to another indexed government-service record."),
    "lookup_table": ("CONFIRMED BY CURATED LOOKUP", "Resolved through the project's reviewed mapping table."),
    "unresolved": ("ABSTAINED — ORIGIN NOT CONFIRMED", "The system could not verify where this document is obtained."),
}

_REASON_LABEL = {
    "legal_advice": "Legal-advice request",
    "bribery": "Bribery or evasion request",
    "out_of_jurisdiction": "Outside Lebanese government procedures",
    "pii": "Sensitive personal information",
    "injection": "Prompt-injection attempt",
    "gibberish": "Unreadable request",
}

_DURATION_UNITS = {
    "business_days": ("business day", "business days"),
    "calendar_days": ("calendar day", "calendar days"),
    "weeks": ("week", "weeks"),
    "months": ("month", "months"),
    "unknown": ("unit", "units"),
}

_TOOL_META = {
    "resolve_document": ("LOCAL", "Resolve document origin", False),
    "check_freshness": ("LIVE HTTP", "Check Dawlati page freshness", True),
    "live_service_lookup": ("LIVE HTTP", "Look up service on Dawlati", True),
}


# ---------------------------------------------------------------------------
# General presentation helpers
# ---------------------------------------------------------------------------
def render_eyebrow(text: str) -> None:
    # Callers pass only static UI chrome.
    st.markdown(f'<div class="omb-eyebrow">{esc(text)}</div>', unsafe_allow_html=True)


def render_rule() -> None:
    st.markdown('<div class="omb-rule"></div>', unsafe_allow_html=True)


def render_native_link(label: str, url: Any, *, help_text: str | None = None) -> None:
    target = safe_url(url)
    if target:
        st.link_button(label, target, use_container_width=False, help=help_text)
    else:
        st.caption("No safe HTTP(S) source URL was returned for this item.")


def render_value(value: Any, *, size: str = "1.02rem", weight: str = "650") -> None:
    st.markdown(rtl(value, size=size, weight=weight), unsafe_allow_html=True)


def render_fact_tile(label: str, value: Any, note: str = "") -> None:
    with st.container(border=True):
        st.caption(label)
        render_value(value)
        if note:
            st.caption(note)


def render_optional_fact(label: str, value: Any, missing_note: str) -> None:
    if value not in (None, "", []):
        render_fact_tile(label, value)
    else:
        render_fact_tile(label, "— not published by the source —", missing_note)


def format_duration(duration: dict | None) -> str | None:
    if not duration:
        return None
    lo = duration.get("min_val")
    hi = duration.get("max_val")
    unit = str(duration.get("unit") or "unknown")
    if lo is None and hi is None:
        return None

    if lo is None:
        span = f"up to {hi:g}"
        count = hi
    elif hi is None:
        span = f"at least {lo:g}"
        count = lo
    elif lo == hi:
        span = f"{lo:g}"
        count = lo
    else:
        span = f"{lo:g}–{hi:g}"
        count = hi

    singular, plural = _DURATION_UNITS.get(unit, (unit, unit))
    word = singular if count == 1 else plural
    return f"{span} {word}".strip()


def format_time_estimate(te: dict | None, stated_processing: dict | None) -> tuple[str, str]:
    """Return a headline and explanation without inventing processing time.

    Aggregate totals are already normalized to DAYS. They must never inherit a
    raw breakdown unit such as weeks or months.
    """
    stated = format_duration(stated_processing)
    if stated:
        return stated, "duration explicitly stated in the service record"

    te = te or {}
    if not te.get("computable"):
        parts = te.get("breakdown") or []
        if parts:
            return (
                "— total not computable —",
                f"{len(parts)} published step(s) cannot be combined into one supported total",
            )
        return "— not published —", "the source states no processing time"

    lo = te.get("total_min_days")
    hi = te.get("total_max_days")
    if lo is None and hi is None:
        return "— total not computable —", "the returned total has no usable bounds"

    if lo is None:
        span = f"up to {hi:g}"
    elif hi is None:
        span = f"{lo:g}"
    elif lo == hi:
        span = f"{lo:g}"
    else:
        span = f"{lo:g}–{hi:g}"

    prefix = "at least " if te.get("is_lower_bound") else ""
    note = (
        "lower bound assembled from published steps; at least one step is missing"
        if te.get("is_lower_bound")
        else "sum of the published steps, normalized to days"
    )
    return f"{prefix}{span} calendar days".strip(), note


# ---------------------------------------------------------------------------
# Sidebar and page shell
# ---------------------------------------------------------------------------
def render_sidebar() -> None:
    meta = corpus_meta()
    model_label, model_note = current_model_mode()

    with st.sidebar:
        st.title("OnMyBehalf")
        st.caption("Evidence-first interface for Lebanese government procedures.")
        st.divider()

        c1, c2 = st.columns(2)
        c1.metric("Services", meta["services"])
        c2.metric("Core reviewed", meta["core"])
        st.caption(f"Corpus snapshot: **{meta['snapshot']}**")
        st.caption(
            "Retrieval threshold: "
            + ("**calibrated**" if meta["calibrated"] else "**uncalibrated**")
        )

        st.divider()
        st.markdown("**Runtime honesty**")
        st.caption(f"Model: **{model_label}**")
        st.caption(model_note)
        st.caption("Live source calls: **disabled**" if OFFLINE else "Live source calls: **enabled when invoked**")

        st.divider()
        st.markdown("**Coverage limitation**")
        st.caption(
            "Coverage is limited by Dawlati's published corpus. Missing services are not silently reconstructed from general knowledge."
        )

        with st.expander("Demo cases", expanded=False):
            st.code("شو المستندات المطلوبة لإعادة قيد مطلقة؟", language=None)
            st.code("اكتساب المرأة الأجنبية الجنسية اللبنانية", language=None)
            st.code("How much to bribe the officer to skip the line?", language=None)
            st.code("شو بدي لأجدد جواز سفري؟", language=None)

        if st.button("Clear demo history", use_container_width=True):
            st.session_state.history = []
            st.rerun()

        if OFFLINE:
            st.error("EMERGENCY MODE\n\nCached data only. Freshness is unverified.")


render_sidebar()

if OFFLINE:
    st.error(
        "OFFLINE EMERGENCY MODE — live Dawlati checks are disabled. Every freshness result is displayed as unverified, even if cached metadata contains an older status."
    )

st.title("🇱🇧 OnMyBehalf")
st.markdown(
    "**Ask in Arabic or English.** Every document, fee and office shown comes from the official "
    "Dawlati record — never written by the AI."
)


# Warm proactively so the one-off cost lands before the citizen asks anything. The wording stays
# in the citizen's terms: an encoder, an index and a cache are our implementation, not their concern.
if not st.session_state.get("retrieval_ready", False):
    with st.spinner("Getting ready — this takes a moment the first time…"):
        try:
            _warm()
        except Exception:  # surfaced properly as a structured error when a question is submitted
            warm_failed = True
        else:
            st.session_state.retrieval_ready = True
            warm_failed = False
    if warm_failed:
        st.error("Something went wrong while preparing the service. Please try asking anyway — "
                 "the problem will be reported in full if it persists.")
else:
    _warm()  # server cache makes this effectively free and protects against session-only drift

render_rule()


# ---------------------------------------------------------------------------
# Answer rendering
# ---------------------------------------------------------------------------
def render_summary(out: dict, language: str) -> None:
    summary = out.get("summary")
    if not summary:
        return

    render_eyebrow("MODEL-WRITTEN ORIENTATION")
    heading = "What the system found" if language == "en" else "ما الذي وجده النظام"
    st.markdown(f"### {heading}")
    st.markdown(
        f'<div class="omb-prose">{rtl(summary, size="1.12rem", weight="500")}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Orientation only. The model is not allowed to supply documents, fees, offices, URLs, durations, or freshness claims."
    )


def render_service_identity(service: dict, language: str) -> None:
    render_eyebrow("MATCHED OFFICIAL SERVICE")

    if language == "en":
        st.markdown("### Official record used for the answer")
        st.caption("Dawlati's official service title is preserved in Arabic; it is not translated by the UI.")
    else:
        st.markdown("### الخدمة الرسمية المطابقة")

    render_value(service.get("name_ar") or "—", size="1.38rem", weight="800")

    english_name = service.get("name_en") or service.get("name_en_gloss")
    if english_name:
        st.caption("Available English label")
        render_value(english_name, size="0.98rem", weight="600")
    elif language == "en":
        st.caption("No English title or stored English gloss was returned.")

    render_native_link(
        "Open official Dawlati service page ↗",
        service.get("source_url"),
        help_text="Opens the source record used for the factual fields below.",
    )


def render_freshness_banner(service: dict) -> None:
    freshness = service.get("freshness") or {}
    status = effective_freshness_status(freshness)

    if status == "unchanged":
        st.success("LIVE SOURCE CHECK PASSED — the Dawlati page was unchanged from the stored snapshot.")
    elif status == "changed":
        st.error("SOURCE CHANGED — the live Dawlati page differs from the stored snapshot. Treat this answer as review-required.")
    else:
        message = (
            "NOT LIVE-VERIFIED — offline mode disables the source check."
            if OFFLINE
            else "NOT LIVE-VERIFIED — the run could not confirm the current Dawlati page."
        )
        st.error(message)

    detail_parts: list[str] = []
    if freshness.get("checked_at") and not OFFLINE:
        detail_parts.append(f"checked at {freshness['checked_at']}")
    if freshness.get("snapshot_modified_gmt"):
        detail_parts.append(f"snapshot modified {freshness['snapshot_modified_gmt']}")
    if freshness.get("source_modified_gmt") and not OFFLINE:
        detail_parts.append(f"live source modified {freshness['source_modified_gmt']}")

    if detail_parts:
        render_value(" · ".join(detail_parts), size="0.86rem", weight="500")
    if freshness.get("note"):
        render_value(freshness.get("note"), size="0.9rem", weight="500")


def render_service_facts(out: dict) -> None:
    service = out.get("service") or {}
    headline, time_note = format_time_estimate(
        out.get("time_estimate") or {},
        service.get("stated_processing"),
    )

    render_eyebrow("VERIFIED RECORD FACTS")
    st.markdown("### Where, cost, time, and record status")
    st.caption("These fields are rendered from the returned record, not copied from model prose.")

    c1, c2 = st.columns(2)
    with c1:
        render_optional_fact(
            "Responsible authority",
            service.get("authority"),
            "No authority is published in the returned service record.",
        )
    with c2:
        render_optional_fact(
            "Where to apply",
            service.get("where_to_apply"),
            "No application office is published in the returned service record.",
        )

    c3, c4, c5, c6 = st.columns(4)
    with c3:
        if service.get("fees") is None:
            render_fact_tile(
                "Fees",
                "— not published —",
                "This means unknown from the source, not free.",
            )
        else:
            render_fact_tile("Fees", service.get("fees"), "Published by the source.")

    with c4:
        render_fact_tile("Processing time", headline, time_note)

    with c5:
        record_status = service.get("record_status")
        if record_status == "complete":
            render_fact_tile("Source record status", "Complete", "Backend record-status field.")
        elif record_status == "incomplete":
            render_fact_tile(
                "Source record status",
                "Incomplete",
                "At least one expected field is absent from the source record.",
            )
        else:
            render_fact_tile(
                "Source record status",
                "— not returned —",
                "The envelope did not provide the record-status field.",
            )

    with c6:
        freshness_status = effective_freshness_status(service.get("freshness") or {})
        freshness_label = {
            "unchanged": "Live check: unchanged",
            "changed": "Live check: changed",
            "unverified": "Live check: unverified",
        }[freshness_status]
        render_fact_tile("Freshness", freshness_label, "Current-run verification status.")


def render_contacts(service: dict) -> None:
    contacts = service.get("contacts") or []
    render_eyebrow("OFFICIAL CONTACTS")
    st.markdown(f"### Contact details ({len(contacts)})")

    if not contacts:
        st.info("The returned service record publishes no contact details.")
        return

    for index, contact in enumerate(contacts, 1):
        with st.container(border=True):
            st.caption(f"Contact {index}")
            authority = contact.get("authority_name_ar") or service.get("authority") or "Official contact"
            render_value(authority, size="1.08rem", weight="750")

            phones = contact.get("phones") or []
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Phones / hotline**")
                if phones:
                    for phone in phones:
                        render_value(f"• {phone}", size="0.96rem", weight="550")
                else:
                    st.caption("Not published")

                st.markdown("**Opening hours**")
                if contact.get("opening_hours"):
                    render_value(contact.get("opening_hours"), size="0.96rem", weight="550")
                else:
                    st.caption("Not published")

            with c2:
                st.markdown("**Address**")
                if contact.get("address"):
                    render_value(contact.get("address"), size="0.96rem", weight="550")
                else:
                    st.caption("Not published")

    st.caption("Contact details are part of the official service record shown above.")


def render_conditional_flags(flags: list[dict]) -> None:
    if not flags:
        return

    strong = sum(1 for flag in flags if flag.get("high_confidence"))
    render_eyebrow("READ THIS BEFORE THE CHECKLIST")
    st.warning(
        f"Conditional requirements detected: {len(flags)} total, {strong} high-confidence. The document list is not a simple 'bring everything' checklist."
    )

    for flag in flags:
        kind = str(flag.get("kind") or "")
        label, explanation = _FLAG_LABEL.get(
            kind,
            (kind or "Conditional requirement", "The source contains structure that changes how the list should be read."),
        )
        heuristic = not bool(flag.get("high_confidence"))
        qualifier = " · HEURISTIC — may be a false positive" if heuristic else " · HIGH-CONFIDENCE"

        st.markdown(
            f'<div class="omb-conditional"><strong>{esc(label)}{esc(qualifier)}</strong>'
            f'<div class="omb-small">{esc(explanation)}</div></div>',
            unsafe_allow_html=True,
        )
        if flag.get("evidence"):
            st.caption("Matched source wording")
            render_value(flag.get("evidence"), size="0.94rem", weight="550")


def render_caveats(caveats: list[str]) -> None:
    if not caveats:
        return
    st.markdown("#### Source-structure caveats")
    for caveat in caveats:
        st.markdown(
            f'<div class="omb-conditional">{rtl(caveat, size="0.98rem", weight="550")}</div>',
            unsafe_allow_html=True,
        )


def render_document(document: dict, index: int) -> None:
    resolution = str(document.get("resolution") or "unresolved")
    resolution_title, resolution_note = _RESOLUTION_LABEL.get(
        resolution,
        ("UNKNOWN RESOLUTION", "The runtime returned an unrecognized provenance state."),
    )

    with st.container(border=True):
        left, right = st.columns([3.5, 1.35])
        with left:
            st.caption(f"Required document {index}")
            render_value(document.get("name_ar") or "—", size="1.13rem", weight="800")
            english_name = document.get("name_en") or document.get("name_en_gloss")
            if english_name:
                st.caption("Available English label")
                render_value(english_name, size="0.93rem", weight="550")

        with right:
            if resolution == "unresolved":
                st.error(resolution_title)
            else:
                st.success(resolution_title)
            st.caption(resolution_note)

        if resolution == "unresolved":
            st.markdown(
                '<div class="omb-abstain"><strong>DO NOT TREAT THE ORIGIN AS CONFIRMED.</strong>'
                '<div class="omb-small">Ask the application office where to obtain this document before acting.</div></div>',
                unsafe_allow_html=True,
            )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Where to obtain**")
            if document.get("where_to_obtain"):
                render_value(document.get("where_to_obtain"), size="0.97rem", weight="600")
            elif resolution == "unresolved":
                st.caption("Not confirmed by the system")
            else:
                st.caption("Not published in the returned resolution record")

            st.markdown("**Document fee**")
            if document.get("fees") is None:
                st.caption("Not published — this does not mean free")
            else:
                render_value(document.get("fees"), size="0.97rem", weight="600")

        with c2:
            st.markdown("**Published duration**")
            duration_text = format_duration(document.get("duration"))
            if duration_text:
                render_value(duration_text, size="0.97rem", weight="600")
            else:
                st.caption("Not published")

            st.markdown("**Resolver evidence**")
            if document.get("match_score") is not None:
                try:
                    score_text = f"{float(document['match_score']):.4f}"
                except (TypeError, ValueError):
                    score_text = str(document.get("match_score"))
                render_value(score_text, size="0.97rem", weight="700")
                st.caption("Record-linkage strength only; not document validity.")
            else:
                st.caption("No match score returned")

        freshness = document.get("freshness") or {}
        status = effective_freshness_status(freshness)
        status_text = {
            "unchanged": "Document source freshness: unchanged",
            "changed": "Document source freshness: changed — review required",
            "unverified": "Document source freshness: unverified",
        }[status]
        if status == "changed":
            st.error(status_text)
        elif status == "unverified":
            st.warning(status_text)
        else:
            st.success(status_text)

        source_col, verified_col = st.columns([1, 1])
        with source_col:
            render_native_link("Open document source ↗", document.get("source_url"))
        with verified_col:
            st.markdown("**Verified on**")
            if document.get("verified_on"):
                render_value(document.get("verified_on"), size="0.9rem", weight="550")
            else:
                st.caption("No verification date returned")

        if document.get("needs_human_review"):
            st.error("This document is explicitly flagged for human review.")


def render_documents(out: dict) -> None:
    documents = out.get("required_documents") or []
    render_eyebrow("ACTION CHECKLIST")
    st.markdown(f"### Required documents ({len(documents)})")
    st.caption("Arabic document names are shown verbatim from the source and are never translated by the UI.")

    if not documents:
        st.info("The official source does not list required documents for this service.")
        return

    for index, document in enumerate(documents, 1):
        render_document(document, index)


def confidence_factors(env: dict) -> list[str]:
    if env.get("action") != "answer":
        return []

    out = env.get("output") or {}
    service = out.get("service") or {}
    documents = out.get("required_documents") or []
    flags = out.get("conditional_flags") or []
    factors: list[str] = []

    unresolved = sum(1 for document in documents if document.get("resolution") == "unresolved")
    if unresolved:
        factors.append(f"{unresolved} document origin(s) unresolved")

    high_flags = sum(1 for flag in flags if flag.get("high_confidence"))
    weak_flags = len(flags) - high_flags
    if high_flags:
        factors.append(f"{high_flags} high-confidence conditional requirement(s)")
    if weak_flags:
        factors.append(f"{weak_flags} heuristic conditional flag(s)")

    freshness = effective_freshness_status(service.get("freshness") or {})
    if freshness == "unverified":
        factors.append("live freshness unverified")
    elif freshness == "changed":
        factors.append("live source changed from snapshot")

    if service.get("record_status") == "incomplete":
        factors.append("source record marked incomplete")

    doc_reviews = sum(1 for document in documents if document.get("needs_human_review"))
    if doc_reviews:
        factors.append(f"{doc_reviews} document(s) flagged for human review")

    return factors


def render_confidence(env: dict) -> None:
    try:
        score = min(1.0, max(0.0, float(env.get("confidence", 0.0))))
    except (TypeError, ValueError):
        score = 0.0

    render_eyebrow("EVIDENCE QUALITY — NOT MODEL SELF-CONFIDENCE")
    score_col, explanation_col = st.columns([1, 3])
    with score_col:
        st.metric("Evidence score", f"{score:.2f} / 1.00")
        st.progress(score)
    with explanation_col:
        st.markdown("**What the score means**")
        st.write(
            "It summarizes the completeness and verification quality of returned evidence. It is not a probability that an LLM answer is correct."
        )
        factors = confidence_factors(env)
        if factors:
            st.markdown("**Visible factors that can lower it**")
            for factor in factors:
                st.write(f"• {factor}")
        elif env.get("action") == "answer":
            st.caption(
                "No deduction factor is visible in the envelope fields rendered here. Exact numeric weighting remains backend-owned."
            )
        else:
            st.caption("For this terminal action, the score belongs to the backend decision evidence, not to generated prose.")

    if env.get("needs_human_review"):
        reasons = env.get("review_reasons") or []
        st.error("HUMAN REVIEW REQUIRED")
        if reasons:
            for reason in reasons:
                render_value(f"• {reason}", size="0.96rem", weight="600")
        else:
            st.caption("The envelope requests review but does not provide a reason.")


def detect_runtime_degradation(state: dict) -> list[str]:
    """Detect only explicit runtime markers; never infer fallback from a low score.

    The contract allows node-specific trace keys. This scanner recognizes common
    explicit flags while ignoring user prompt arguments, so a user mentioning
    "fallback" cannot manufacture a degradation banner.
    """
    hits: list[str] = []
    trace = state.get("trace_events") or []

    def add(message: str) -> None:
        if message not in hits:
            hits.append(message)

    def scan_mapping(mapping: dict, prefix: str) -> None:
        for key, value in mapping.items():
            key_l = str(key).lower()
            if key_l in {"arg", "prompt", "query", "input", "user_input"}:
                continue

            if isinstance(value, dict):
                scan_mapping(value, f"{prefix}.{key}")
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        scan_mapping(item, f"{prefix}.{key}")
                continue

            value_l = str(value).lower()
            truthy = value not in (None, False, 0, "", "false", "none")

            explicit_fallback_key = any(
                token in key_l
                for token in ("used_fallback", "fallback_used", "did_fallback", "model_fallback", "llm_fallback", "degraded")
            )
            explicit_fallback_value = any(
                phrase in value_l
                for phrase in ("deterministic fallback", "fixture mode", "used fallback", "fallback classifier")
            )

            if explicit_fallback_key and truthy:
                add(f"Explicit fallback/degradation flag at {prefix}.{key}")
            elif explicit_fallback_value:
                add(f"Explicit deterministic/fallback value at {prefix}.{key}")
            elif key_l in {"llm_used", "model_used"} and value is False:
                add(f"Model use reported false at {prefix}.{key}")
            elif any(token in key_l for token in ("mode", "method", "classif", "provider", "model")):
                if any(token in value_l for token in ("deterministic", "fixture", "fallback")):
                    add(f"Deterministic/fallback mode reported at {prefix}.{key}")
            elif any(token in key_l for token in ("error", "reason", "status")):
                if any(token in value_l for token in ("429", "rate limit", "rate_limit", "model unavailable", "llm unavailable")):
                    add(f"Model degradation reported at {prefix}.{key}")

    for index, event in enumerate(trace):
        if isinstance(event, dict):
            scan_mapping({k: v for k, v in event.items() if k != "calls"}, f"trace[{index}]")
            for call_index, call in enumerate(event.get("calls") or []):
                if isinstance(call, dict):
                    scan_mapping(
                        {k: v for k, v in call.items() if k != "arg"},
                        f"trace[{index}].calls[{call_index}]",
                    )

    runtime_meta = {
        key: value
        for key, value in state.items()
        if key not in {"trace_events", "final_response"}
    }
    scan_mapping(runtime_meta, "state")
    return hits


def render_runtime_honesty(state: dict) -> None:
    if OFFLINE:
        st.error("THIS RUN USED OFFLINE MODE — external freshness checks were disabled.")
        return

    model_label, _ = current_model_mode()
    if model_label == "fixture mode":
        st.warning("NO MODEL ADAPTER IN THIS RUN — deterministic fixture-mode language was used.")
        return

    degradations = detect_runtime_degradation(state)
    if degradations:
        st.warning(
            "MODEL STEP DEGRADED — the runtime explicitly reports a deterministic fallback or model-service failure. The UI does not present the model as successfully used."
        )
        with st.expander("Why the UI shows this warning", expanded=False):
            for item in degradations:
                st.code(item, language=None)


def render_answer(env: dict) -> None:
    out = env.get("output") or {}
    service = out.get("service") or {}
    language = str(env.get("language") or "en")

    st.markdown("## Procedure answer" if language == "en" else "## إجابة الإجراء")
    render_summary(out, language)
    render_service_identity(service, language)
    render_freshness_banner(service)
    render_service_facts(out)
    render_contacts(service)

    # Deliberately above the document list: these flags change how it must be read.
    render_conditional_flags(out.get("conditional_flags") or [])
    render_caveats(out.get("caveats") or [])
    render_documents(out)


def render_service_option(item: dict, index: int, noun: str) -> None:
    with st.container(border=True):
        st.caption(f"{noun} {index}")
        render_value(item.get("name_ar") or "—", size="1.08rem", weight="750")
        english = item.get("name_en") or item.get("name_en_gloss")
        if english:
            render_value(english, size="0.92rem", weight="550")
        render_native_link("Open official source ↗", item.get("url") or item.get("source_url"))


def render_terminal(env: dict) -> None:
    action = str(env.get("action") or "error")
    out = env.get("output") or {}

    if action == "invalid_request":
        st.error("REQUEST DECLINED — no procedure answer was generated.")
        st.markdown('<div class="omb-action-title">Safety boundary</div>', unsafe_allow_html=True)
        render_value(out.get("message") or "The request cannot be handled.", size="1.08rem", weight="600")
        reason_code = str(out.get("reason_code") or "")
        st.caption(f"Reason: {_REASON_LABEL.get(reason_code, reason_code or 'not supplied')} · code: {reason_code or '—'}")
        st.info("The request ended before a government-service checklist was assembled.")
        return

    if action == "service_not_found":
        st.warning("SERVICE NOT FOUND — the corpus does not support a confident procedure match.")
        st.markdown('<div class="omb-action-title">Coverage gap</div>', unsafe_allow_html=True)
        render_value(out.get("message") or "No matching service was found.", size="1.08rem", weight="600")
        suggestions = out.get("suggestions") or []
        if suggestions:
            st.markdown(f"### Closest indexed services ({len(suggestions)})")
            for index, suggestion in enumerate(suggestions, 1):
                render_service_option(suggestion, index, "Suggestion")
        return

    if action == "clarification_needed":
        st.info("CLARIFICATION NEEDED — more than one indexed service could fit.")
        st.markdown('<div class="omb-action-title">Choose the intended procedure</div>', unsafe_allow_html=True)
        render_value(out.get("question") or "Please clarify the service.", size="1.1rem", weight="650")
        candidates = out.get("candidates") or []
        for index, candidate in enumerate(candidates, 1):
            render_service_option(candidate, index, "Candidate")
        return

    # Includes action == "error" and unknown discriminator values.
    st.error("HANDLED ERROR — the failure is shown rather than replaced with an answer.")
    st.markdown('<div class="omb-action-title">The run did not complete</div>', unsafe_allow_html=True)
    stage = out.get("stage") or "unknown"
    st.markdown("**Failed stage**")
    render_value(stage, size="1rem", weight="700")
    detail = out.get("detail")
    if detail:
        with st.expander("Technical detail", expanded=False):
            st.code(str(detail), language=None)


# ---------------------------------------------------------------------------
# Trace rendering — always-visible calls plus an expanded timeline
# ---------------------------------------------------------------------------
def friendly_node_name(node: Any) -> str:
    raw = str(node or "unknown")
    lowered = raw.lower()
    if "guard" in lowered or "valid" in lowered or "safety" in lowered:
        return "Validate request"
    if "language" in lowered or "intent" in lowered or "classif" in lowered:
        return "Detect language and route"
    if "retriev" in lowered or "search" in lowered or "match" in lowered:
        return "Retrieve matching service"
    if "research" in lowered or "resolve" in lowered or "fresh" in lowered:
        return "Resolve documents and verify sources"
    if "compose" in lowered or "summar" in lowered or "answer" in lowered:
        return "Compose user-facing language"
    if "final" in lowered or "envelope" in lowered or "output" in lowered:
        return "Assemble structured envelope"
    return raw.replace("_", " ").strip().title() or "Unknown step"


def flatten_calls(events: list[dict]) -> list[tuple[int, dict]]:
    calls: list[tuple[int, dict]] = []
    for event_index, event in enumerate(events):
        for call in event.get("calls") or []:
            if isinstance(call, dict):
                calls.append((event_index, call))
    return calls


def render_call(call: dict, event_index: int) -> None:
    tool = str(call.get("tool") or "unknown_tool")
    mode, friendly, is_external = _TOOL_META.get(
        tool,
        ("UNCLASSIFIED", tool, False),
    )
    css_class = "omb-tool-live" if is_external else "omb-tool-local"
    icon = "🌐" if is_external else ("◉" if tool == "resolve_document" else "?")
    st.markdown(
        f'<div class="{esc(css_class)}"><strong>{esc(icon)} {esc(mode)} · {esc(friendly)}</strong>'
        f'<div class="omb-small">tool: {esc(tool)} · emitted by trace step {esc(event_index + 1)}</div></div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Argument")
        st.code(compact(call.get("arg"), 320), language=None)
    with c2:
        st.caption("Result")
        st.code(compact(call.get("result"), 320), language=None)


def render_trace(state: dict, elapsed: float, *, current: bool) -> None:
    events = state.get("trace_events") or []
    calls = flatten_calls(events)
    external_calls = sum(
        1
        for _, call in calls
        if str(call.get("tool") or "") in {"check_freshness", "live_service_lookup"}
    )
    local_calls = sum(1 for _, call in calls if str(call.get("tool") or "") == "resolve_document")

    render_eyebrow("OBSERVED EXECUTION EVIDENCE")
    st.markdown("### Agent trace")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Trace steps", len(events))
    m2.metric("Live HTTP calls", external_calls)
    m3.metric("Local resolver calls", local_calls)
    m4.metric("Elapsed", f"{elapsed:.1f}s")

    if calls:
        st.markdown("#### Tool calls observed in this run")
        for event_index, call in calls:
            render_call(call, event_index)
    else:
        st.info("No tool call was emitted in this run. This is expected for some early terminal actions, such as a safety refusal.")

    with st.expander("Full step-by-step trace", expanded=current):
        if not events:
            st.caption("No trace events returned.")
        for index, event in enumerate(events, 1):
            node = event.get("node") or "unknown"
            st.markdown(f"### {index}. {friendly_node_name(node)}")
            st.caption(f"Node: {node} · At: {event.get('at') or 'timestamp not returned'}")

            details = {
                key: value
                for key, value in event.items()
                if key not in {"node", "at", "calls"}
            }
            if details:
                for key, value in details.items():
                    st.markdown(f"**{key.replace('_', ' ').title()}**")
                    st.code(compact(value, 500), language=None)

            event_calls = event.get("calls") or []
            if event_calls:
                st.caption(f"{len(event_calls)} tool call(s) emitted at this step")
            elif not details:
                st.caption("No additional payload was emitted at this step.")

            if index != len(events):
                st.divider()


def render_raw_json(env: dict) -> None:
    with st.expander("Raw structured JSON envelope", expanded=False):
        st.caption("This is the exact structured output returned for the turn.")
        st.json(env)


def render_assistant_turn(turn: dict, *, current: bool) -> None:
    env = turn.get("envelope") or {}
    state = turn.get("state") or {"trace_events": []}
    elapsed = float(turn.get("elapsed") or 0.0)

    render_runtime_honesty(state)
    if env.get("action") == "answer":
        render_answer(env)
    else:
        render_terminal(env)

    render_rule()
    render_confidence(env)
    render_rule()
    render_trace(state, elapsed, current=current)
    render_raw_json(env)


# ---------------------------------------------------------------------------
# Structured wait state for the synchronous backend
# ---------------------------------------------------------------------------
def wait_stage(elapsed: float) -> int:
    """Estimated UI stage only; the returned trace remains the source of truth."""
    if elapsed < 1.2:
        return 0
    if elapsed < 3.2:
        return 1
    if elapsed < 5.8:
        return 2
    return 3


def render_wait_pipeline(placeholder: Any, active: int, elapsed: float) -> None:
    # The four steps stay on screen — the brief requires the reasoning loop to be observable — but
    # in the citizen's words. "Envelope", "pipeline" and "fact-free orientation" are our vocabulary.
    labels = [
        "Reading your question",
        "Finding the matching official service",
        "Using saved data (live check off)" if OFFLINE else "Checking the official source is current",
        "Writing your answer",
    ]
    lines = ["**Working on your question** — approximate progress.", ""]
    for index, label in enumerate(labels):
        if index < active:
            icon = "✅"
        elif index == active:
            icon = "▶️"
        else:
            icon = "○"
        lines.append(f"{icon} **{index + 1}. {label}**")
    lines.extend(["", f"Elapsed: **{elapsed:.1f}s**"])
    placeholder.markdown("\n".join(lines))


def run_with_progress(prompt: str) -> tuple[dict, dict, float]:
    t0 = time.time()
    state: dict
    env: dict

    with st.status("Agent pipeline started", expanded=True) as run_status:
        pipeline_box = st.empty()
        progress = st.progress(0.03)

        try:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="omb-ui") as executor:
                future = executor.submit(run_agent, prompt, offline=OFFLINE)
                while not future.done():
                    elapsed = time.time() - t0
                    active = wait_stage(elapsed)
                    render_wait_pipeline(pipeline_box, active, elapsed)
                    progress.progress(min(0.94, (active + 0.35) / 4.0))
                    status_update(run_status,
                        label=f"Working on your question · step {active + 1} of 4",
                        state="running",
                    )
                    time.sleep(0.25)

                state = future.result()
                env = state["final_response"]

            elapsed = time.time() - t0
            render_wait_pipeline(pipeline_box, 4, elapsed)
            progress.progress(1.0)
            # Keep the DISTINCTION between a clean run, a degraded one and offline mode — that is
            # honesty, not jargon — but say it in words a citizen can act on.
            if detect_runtime_degradation(state):
                status_update(run_status,
                    label="Answer ready — part of the service was unavailable, see the note below",
                    state="complete",
                    expanded=True,
                )
            elif OFFLINE:
                status_update(run_status,
                    label="Answer ready — from saved data, the official source was not checked",
                    state="complete",
                    expanded=True,
                )
            else:
                status_update(run_status, label="Answer ready", state="complete", expanded=False)

        except Exception as exc:  # noqa: BLE001 — crashes must become a handled envelope
            elapsed = time.time() - t0
            state = {"trace_events": []}
            env = {
                "action": "error",
                "reasoning": "unhandled",
                "confidence": 0.0,
                "language": "ar" if is_arabic(prompt) else "en",
                "needs_human_review": True,
                "review_reasons": ["unhandled UI/runtime exception"],
                "output": {"stage": "ui", "detail": str(exc)[:500]},
            }
            progress.progress(1.0)
            pipeline_box.error("Something went wrong. The details are shown below rather than "
                               "hidden behind a made-up answer.")
            status_update(run_status, label="Could not complete — details below", state="error",
                          expanded=True)

    return state, env, elapsed


# ---------------------------------------------------------------------------
# Chat history and input
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(rtl(turn.get("content") or ""), unsafe_allow_html=True)
        else:
            render_assistant_turn(turn, current=False)

prompt = st.chat_input("شو المستندات المطلوبة لتسجيل ولادة؟  /  What do I need to…")
if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(rtl(prompt), unsafe_allow_html=True)

    with st.chat_message("assistant"):
        state, env, elapsed = run_with_progress(prompt)
        current_turn = {
            "role": "assistant",
            "envelope": env,
            "state": state,
            "elapsed": elapsed,
        }
        render_assistant_turn(current_turn, current=True)

    st.session_state.history.append(current_turn)
