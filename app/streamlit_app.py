"""Streamlit chat UI — RTL, agent trace, raw JSON, --offline emergency mode (SCOPE FR10, G9).

Three things on this screen are graded and none of them is decoration:
  * the ANSWER as a checklist with a source link on every claim,
  * the AGENT TRACE, because the brief requires a tool call to be visible during the demo,
  * the RAW JSON, because the brief requires structured output.

SECURITY (A29): every dynamic string is rendered through `esc()`. The corpus is scraped from a
government site and contains raw HTML entities and stray markup already; Streamlit's `markdown`
with `unsafe_allow_html=True` is needed for the RTL wrapper, which means unescaped content would
be live HTML. `check_g9.py` asserts a `<script>` payload survives as text.

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
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env BEFORE anything reads GROQ_API_KEY. Without this the UI silently ran in fixture mode —
# no model in the loop, `reasoning` falling back to the deterministic string — while the sidebar
# still captioned MODEL_ID's default. The eval harness loads .env, so the demo and the measured
# numbers came from differently-wired graphs. Keep this above the `agents.*` imports.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

OFFLINE = "--offline" in sys.argv

st.set_page_config(page_title="OnMyBehalf", page_icon="🇱🇧", layout="wide")


# ---------------------------------------------------------------- helpers
def esc(text) -> str:
    """HTML-escape anything before it reaches an unsafe_allow_html sink. Never bypass this."""
    return html.escape(str(text if text is not None else ""))


def is_arabic(text: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in str(text or ""))


def rtl(text: str, size: str = "1rem", weight: str = "400") -> str:
    """Wrap in a direction-correct block. Arabic must render RTL or it is unreadable."""
    d = "rtl" if is_arabic(text) else "ltr"
    align = "right" if d == "rtl" else "left"
    return (f'<div dir="{d}" style="text-align:{align};font-size:{size};'
            f'font-weight:{weight};line-height:1.9">{esc(text)}</div>')


@st.cache_resource(show_spinner="Loading the retrieval index…")
def _warm():
    """Load the encoder + index ONCE per server, not per query.

    Cold load is ~25 s. Without this the first demo question looks like a hang, and Streamlit
    re-runs the whole script on every interaction.
    """
    from tools.search_services import search_services
    search_services("warm", k=1)
    return True


def corpus_meta() -> dict:
    core = ROOT / "data" / "curated_core.json"
    thresh = ROOT / "data" / "retrieval_thresholds.json"
    n_core = n_svc = 0
    snapshot = "—"
    if core.exists():
        n_core = json.loads(core.read_text(encoding="utf-8")).get("n_core", 0)
    corpus_dir = ROOT / "data" / "corpus"
    if corpus_dir.exists():
        files = list(corpus_dir.glob("*.json"))
        n_svc = len(files)
        if files:
            rec = json.loads(files[0].read_text(encoding="utf-8"))
            snapshot = (rec.get("crawled_at") or "")[:10]
    calibrated = thresh.exists()
    return {"services": n_svc, "core": n_core, "snapshot": snapshot, "calibrated": calibrated}


# ---------------------------------------------------------------- sidebar
meta = corpus_meta()
with st.sidebar:
    st.header("OnMyBehalf")
    st.caption("Lebanese government procedures, from Dawlati, with a source for every claim.")
    st.divider()
    st.metric("Services indexed", meta["services"])
    st.metric("Hand-verified core", meta["core"])
    st.caption(f"Corpus snapshot: **{meta['snapshot']}**")
    # Report the model only when one is actually wired in. Captioning MODEL_ID's default while the
    # graph ran in fixture mode put a claim on screen that the run did not support.
    from agents.runtime import get_adapter_or_none  # local: keeps module import cheap, as elsewhere

    if OFFLINE:
        st.caption("Model: **offline** — external calls disabled")
    elif get_adapter_or_none() is not None:
        st.caption(f"Model: `{os.environ.get('MODEL_ID', 'openai/gpt-oss-120b')}`")
    else:
        st.caption("Model: **none — fixture mode** (no `GROQ_API_KEY`); "
                   "reasoning is deterministic, not model-written")
    st.caption(f"Retrieval θ: {'calibrated' if meta['calibrated'] else '**uncalibrated**'}")
    st.divider()
    st.caption("**Coverage is partial by source.** Only 3 of Lebanon's 22 ministries have "
               "published services on Dawlati. Passports and driving licences are not there.")
    if OFFLINE:
        st.error("EMERGENCY MODE — cached answers, no live source check.")

if OFFLINE:
    st.warning("⚠️ **CACHED — EMERGENCY MODE.** Answers are served from a local cache and the "
               "live source check is disabled. Freshness cannot be verified in this mode.",
               icon="⚠️")

st.title("🇱🇧 OnMyBehalf")
st.caption("Ask about a Lebanese government procedure — in Arabic or English.")


# ---------------------------------------------------------------- rendering
# What each conditional KIND means for the citizen reading the list below it. The source encodes
# branching logic that `required_documents: list[str]` flattens away (REPORT §5), so the flags are
# the only thing on screen telling a reader the list is not a plain "bring all of these".
_FLAG_LABEL = {
    "branch": ("Depends on who you are",
               "The source lists different documents for different applicants. "
               "The list below merges every case — confirm which one is yours."),
    "either_or": ("Alternatives, not extras",
                  "Some items are «أو» (or) alternatives. You may not need all of them."),
    "precondition": ("Eligibility condition",
                     "This procedure has a condition that must hold before you apply."),
    "recency": ("Document must be recent",
                "At least one document must be issued within a time window."),
}

# `aggregate()` converts every total to DAYS (weeks x7, months x30) and business/calendar days pass
# through 1:1, so a total is only ever expressible in days. Labelling it with the breakdown's raw
# unit read "14 weeks" for 2 weeks — a 7x overstatement of an official processing time.
_TOTAL_UNIT_WORD = {"business_days": "business days"}  # everything else aggregates to calendar days


def render_conditional_flags(flags: list) -> None:
    """The project's headline structural finding, shown rather than buried in caveat prose.

    Placed ABOVE the document list on purpose: it changes how the list should be read. `either_or`
    keys on «أو», which is ubiquitous in Arabic, so it is marked heuristic — the same reason it
    never escalates to human review on its own.
    """
    if not flags:
        return
    strong = sum(1 for f in flags if f.get("high_confidence"))
    st.markdown(f"**⚠️ This service has conditional requirements** "
                f"({len(flags)} detected, {strong} high-confidence)")
    st.caption("Detected automatically in the source text. A flat checklist cannot express these, "
               "so we flag them instead of silently flattening them.")
    for f in flags:
        kind = f.get("kind", "")
        label, explain = _FLAG_LABEL.get(kind, (kind or "conditional", ""))
        weak = "" if f.get("high_confidence") else " · heuristic, may be a false positive"
        st.markdown(
            f'<div style="border-left:3px solid #d68000;padding:0.35rem 0.8rem;margin:0.35rem 0;'
            f'background:rgba(214,128,0,0.07)">'
            f'<strong>{esc(label)}</strong>'
            f'<span style="opacity:0.7;font-size:0.85rem"> — {esc(explain)}{esc(weak)}</span>'
            f'</div>', unsafe_allow_html=True)
        if f.get("evidence"):
            st.markdown(
                f'<div style="margin:-0.2rem 0 0.6rem 1.1rem;opacity:0.75;font-size:0.9rem">'
                f'↳ source: {rtl(f["evidence"], size="0.9rem")}</div>', unsafe_allow_html=True)


def format_time_estimate(te: dict) -> tuple[str, str]:
    """(headline, caption) for the processing-time tile.

    Returns an honest refusal rather than a number whenever the estimate is not computable — which
    is currently ALWAYS, because no node populates `state["time_estimate"]` and Dawlati does not
    publish processing durations. Showing "not published" keeps a promise the pitch makes; inventing
    a plausible number would break the one rule this system is built on.
    """
    if not te:
        return "— not published —", ""
    if not te.get("computable"):
        parts = te.get("breakdown") or []
        if parts:
            return ("— total not computable —",
                    f"{len(parts)} step(s) published, but their units cannot be summed")
        return "— not published —", "the source states no processing time"

    raw_unit = ""
    if te.get("breakdown"):
        raw_unit = (te["breakdown"][0].get("duration") or {}).get("unit", "")
    unit = _TOTAL_UNIT_WORD.get(raw_unit, "calendar days")
    lo, hi = te.get("total_min_days"), te.get("total_max_days")
    span = f"{lo:g}" if hi in (None, lo) else f"{lo:g}–{hi:g}"
    prefix = "at least " if te.get("is_lower_bound") else ""
    caption = ("assembled from steps where at least one duration was missing"
               if te.get("is_lower_bound") else "sum of the published steps")
    return f"{prefix}{span} {unit}".strip(), caption


def render_answer(out: dict) -> None:
    svc = out.get("service") or {}
    st.markdown(rtl(svc.get("name_ar") or "", size="1.35rem", weight="700"),
                unsafe_allow_html=True)
    if svc.get("source_url"):
        st.markdown(f"[↗ Official source on Dawlati]({svc['source_url']})")

    # Model-written and deliberately fact-free — every number, document and office below this
    # line is rendered from the verified record, never from the model.
    if out.get("summary"):
        st.markdown(
            f'<div style="border-left:3px solid #4c8bf5;padding:0.5rem 0.9rem;margin:0.6rem 0;'
            f'background:rgba(76,139,245,0.06)">{rtl(out["summary"])}</div>',
            unsafe_allow_html=True)

    for caveat in out.get("caveats") or []:
        st.warning(caveat, icon="⚠️")

    # Before the list, not after: these flags change how the list must be read.
    render_conditional_flags(out.get("conditional_flags") or [])

    docs = out.get("required_documents") or []
    st.subheader(f"Required documents ({len(docs)})")
    if not docs:
        st.info("The official source does not list required documents for this service.")
    for i, d in enumerate(docs, 1):
        st.markdown(rtl(f"{i}. {d.get('name_ar','')}"), unsafe_allow_html=True)
        where, res = d.get("where_to_obtain"), d.get("resolution")
        if res == "unresolved":
            st.caption("↳ ⚠️ we could not confirm where to obtain this — verify with the office")
        elif where:
            st.markdown(
                f'<div style="margin:-0.4rem 0 0.6rem 1.2rem;opacity:0.75">'
                f'↳ {rtl(where)}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**Fees**")
        # None means the source PUBLISHES no fee, which is not the same as the service being free —
        # the agent was specifically criticised for collapsing those two.
        st.markdown(rtl(svc.get("fees") or "— not published —"), unsafe_allow_html=True)
    with c2:
        st.markdown("**Where to apply**")
        st.markdown(rtl(svc.get("where_to_apply") or "— not published —"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown("**Processing time**")
        headline, sub = format_time_estimate(out.get("time_estimate") or {})
        st.markdown(rtl(headline), unsafe_allow_html=True)
        if sub:
            st.caption(sub)
    with c4:
        st.markdown("**Source freshness**")
        f = (svc.get("freshness") or {}).get("status", "unverified")
        st.markdown({"unchanged": "✅ unchanged since our snapshot",
                     "changed": "⚠️ the source changed — flagged for review",
                     "unverified": "❔ could not verify"}.get(f, f))


def render_terminal(action: str, out: dict) -> None:
    if action == "invalid_request":
        st.error(f"**Request declined** — {esc(out.get('message',''))}")
        st.caption(f"reason: `{esc(out.get('reason_code','')) }`")
    elif action == "service_not_found":
        st.warning(rtl(out.get("message", "")), unsafe_allow_html=True)
        if out.get("suggestions"):
            st.caption("Closest services we do have:")
            for s in out["suggestions"]:
                st.markdown(rtl(f"• {s.get('name_ar','')}"), unsafe_allow_html=True)
    elif action == "clarification_needed":
        st.info(rtl(out.get("question", "")), unsafe_allow_html=True)
        for c in out.get("candidates") or []:
            st.markdown(rtl(f"• {c.get('name_ar','')}"), unsafe_allow_html=True)
    elif action == "error":
        st.error(f"Something went wrong at `{esc(out.get('stage',''))}`. "
                 "The failure was handled rather than hidden.")


def render_trace(state: dict, elapsed: float) -> None:
    events = state.get("trace_events") or []
    externals = [c for t in events if t["node"] == "research"
                 for c in t.get("calls", []) if c["tool"] != "resolve_document"]
    label = f"🔍 Agent trace — {len(events)} steps, {len(externals)} external call(s), {elapsed:.1f}s"
    with st.expander(label):
        for t in events:
            bits = {k: v for k, v in t.items() if k not in {"node", "at", "calls"}}
            st.markdown(f"**{esc(t['node'])}** — `{esc(json.dumps(bits, ensure_ascii=False))[:160]}`")
            for c in t.get("calls", []):
                icon = "🌐" if c["tool"] != "resolve_document" else "🔗"
                st.caption(f"　{icon} `{esc(c['tool'])}`({esc(str(c.get('arg'))[:44])}) "
                           f"→ {esc(c.get('result'))}")


# ---------------------------------------------------------------- chat loop
if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(rtl(turn["content"]), unsafe_allow_html=True)
        else:
            env = turn["envelope"]
            out = env.get("output") or {}
            if env.get("action") == "answer":
                render_answer(out)
            else:
                render_terminal(env.get("action", ""), out)
            cc1, cc2 = st.columns([1, 3])
            with cc1:
                st.metric("Confidence", f"{env.get('confidence', 0):.2f}")
            with cc2:
                if env.get("needs_human_review"):
                    st.caption("🚩 flagged for human review: "
                               + ", ".join(env.get("review_reasons") or []))
            render_trace(turn["state"], turn["elapsed"])
            with st.expander("📄 Raw JSON (the structured output the brief requires)"):
                st.json(env)

if prompt := st.chat_input("شو المستندات المطلوبة لتسجيل ولادة؟  /  What do I need to…"):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(rtl(prompt), unsafe_allow_html=True)

    with st.chat_message("assistant"):
        _warm()
        from agents.runtime import answer as run_agent
        with st.spinner("Consulting Dawlati…"):
            t0 = time.time()
            try:
                state = run_agent(prompt, offline=OFFLINE)
                env = state["final_response"]
            except Exception as exc:  # noqa: BLE001 — a crash must render as a handled error
                state = {"trace_events": []}
                env = {"action": "error", "reasoning": "unhandled", "confidence": 0.0,
                       "language": "ar", "output": {"stage": "ui", "detail": str(exc)[:200]}}
            elapsed = time.time() - t0

        out = env.get("output") or {}
        if env.get("action") == "answer":
            render_answer(out)
        else:
            render_terminal(env.get("action", ""), out)
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric("Confidence", f"{env.get('confidence', 0):.2f}")
        with c2:
            if env.get("needs_human_review"):
                st.caption("🚩 flagged for human review: "
                           + ", ".join(env.get("review_reasons") or []))
        render_trace(state, elapsed)
        with st.expander("📄 Raw JSON (the structured output the brief requires)"):
            st.json(env)

    st.session_state.history.append({"role": "assistant", "envelope": env,
                                     "state": state, "elapsed": elapsed})
