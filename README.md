# OnMyBehalf — an agentic AI for Lebanese government procedures

MSBA 316 (Text Analytics & NLP, AUB, Summer 2025/26) course project. **Team:** Gaby, Mariam, Ali,
Ghina, Maria.

Given a citizen's question (Arabic or English) about a Lebanese government transaction, the agent
returns a **verified checklist of required documents — with where to obtain each one** — plus fees,
authority, where to apply, best-effort contacts, and a source-cited time estimate, flagging every
claim it cannot verify for human review. Data source: [Dawlati](https://dawlati.gov.lb), Lebanon's
national public-services portal (OMSAR).

> Demo video: _(added at G10)_

## Teammates: start here
- **`CONTRIBUTING.md`** — your part, how the work splits, whether it parallelizes (it does), workflow.
- **`SETUP.md`** — environment setup end to end.
- **`docs/`** — the full plan: `SCOPE`, `SCHEMA_AND_CONTRACTS`, `TECH_PLAN`, `VERIFICATION`,
  `PROGRESS` (live status + owners), `RESOLUTIONS` (+ `reviews/` decision trail).

## Architecture (one line)
`detect_language → validate_input → classify_intent → retrieve (RRF: BM25+BGE-M3) → bounded research
loop (resolve_document · check_freshness · live_service_lookup) → compose → validate_schema → respond`,
on **LangGraph**, with **Groq** (model chosen by the G0 bakeoff), **Chroma** vector store, and a
**Streamlit** chat UI. Structured JSON out; human-in-the-loop review queue. Full design in `../Final
Project/` planning docs (SCOPE, SCHEMA_AND_CONTRACTS, TECH_PLAN, VERIFICATION).

## Setup
```bash
python -m venv .venv && .venv/Scripts/activate      # Windows: keep .venv OUT of OneDrive sync if possible
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # then paste your Groq key into .env  (never commit .env)
```

## Gates (must pass in order — see ../Final Project/VERIFICATION.md)
```bash
python tests/gates/check_g0.py     # env + per-model bakeoff (run FIRST)
```

## Repo layout
```
agents/     models.py (schema), adapters.py (per-model Groq), state.py, graph.py
prompts/    intent_classifier_v1.md, research_agent_v1.md, composer_v1.md, ITERATION_LOG.md
tools/      search_services, resolve_document, check_freshness, live_service_lookup,
            enrich_contacts, indexer, crawler/
tests/      gold_claims.seed.json, gates/, unit/
data/       document_sources / curated_core seeds  (corpus & chroma are gitignored)
app/        streamlit_app.py
report/     AI_LOG.md, evidence/
```

## Notes
- No API keys in the repo (`.env` gitignored; `tests/gates/check_g10` secret-scans history).
- Corpus is public Dawlati content used for retrieval-with-attribution (site `ai-train=no` respected).
