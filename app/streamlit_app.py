"""Streamlit chat UI — RTL, trace panel, raw-JSON, --offline emergency mode (SCOPE FR10). Stub — G9.
"""
import streamlit as st

st.set_page_config(page_title="OnMyBehalf", page_icon="🇱🇧")
st.title("OnMyBehalf")
st.info("UI scaffold — built at G9 (Jul 27–28). Will render the checklist answer, an 'Agent trace' "
        "expander (from state.trace_events), a raw-JSON expander, RTL for Arabic, and a "
        "'CACHED — EMERGENCY MODE' banner under --offline.")

# TODO(G9): st.chat_input/message; escape all dynamic text (A29); dir=rtl wrapper for Arabic;
# sidebar: model id, corpus snapshot date, coverage; --offline loads report/evidence/demo_cache.
