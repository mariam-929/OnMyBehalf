# OnMyBehalf — an agentic AI for Lebanese government procedures

MSBA 316 (Text Analytics & NLP, AUB, Summer 2025/26) course project. **Team:** Gaby, Mariam, Ali,
Ghina, Maria.

Given a citizen's question (Arabic or English) about a Lebanese government transaction, the agent
returns a **verified checklist of required documents — with where to obtain each one** — plus fees,
authority, where to apply, best-effort contacts, and a source-cited time estimate, flagging every
claim it cannot verify for human review. Data source: [Dawlati](https://dawlati.gov.lb), Lebanon's
national public-services portal (OMSAR).

> **Demo video:** _(link to be added)_

## Architecture

```
detect_language → validate_input → classify_intent → retrieve (RRF: BM25 + BGE-M3)
  → bounded research loop (resolve_document · check_freshness · live_service_lookup)
  → compose → validate_schema → respond
```

Built on **LangGraph**, with **Groq** for inference, a **Chroma** vector store, and a **Streamlit**
chat UI. Output is structured JSON validated against a Pydantic schema; anything the agent cannot
verify against a live source is flagged and routed to a human review queue.

When Dawlati has no record for a service, a **federated external-source layer** falls back to the
authority that actually issues the document (e.g. General Security for passports) rather than
inventing an answer.

### Repo layout
```
agents/     models.py (schema), adapters.py (per-model Groq), state.py, graph.py, nodes/
prompts/    intent_classifier_v1.md, research_agent_v1/v2.md, composer_v1.md, ITERATION_LOG.md
tools/      search_services, resolve_document, check_freshness, live_service_lookup,
            external_source, enrich_contacts, indexer, crawler/
tests/      gates/ (G0–G9), unit/, gold sets, run_eval.py
data/       document_sources / curated_core seeds  (corpus & chroma index are gitignored)
app/        streamlit_app.py
```

## Setup

**Prerequisites:** Python 3.12+, Git, and a free [Groq API key](https://console.groq.com)
(no credit card). Node.js is *not* needed — Playwright downloads its own browser.

```bash
git clone https://github.com/mariam-929/OnMyBehalf.git
cd OnMyBehalf
```

**1. Create a virtual environment.** On Windows, keep it *outside* any OneDrive-synced folder —
OneDrive tries to sync its tens of thousands of files and causes file locks:

```powershell
python -m venv "$env:USERPROFILE\venvs\OnMyBehalf"
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\Activate.ps1"
```
```bash
# macOS / Linux
python -m venv ~/venvs/OnMyBehalf && source ~/venvs/OnMyBehalf/bin/activate
```

**2. Install dependencies** (pulls PyTorch + sentence-transformers, ChromaDB, LangGraph, the Groq
SDK, Streamlit, Playwright — a few minutes and a few hundred MB on first run):

```bash
pip install -r requirements.txt
playwright install chromium
```

**3. Configure your key.** Copy the template and paste your Groq key into `.env`:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```
```
GROQ_API_KEY=gsk_...your key...
MODEL_ID=openai/gpt-oss-120b
```
**Never commit `.env`** — it is gitignored. The app still runs without a key (it falls back to a
deterministic intent classifier), but the model in the loop gives much better answers.

**4. Build the corpus and index.** `data/corpus/` and `data/chroma/` are gitignored, so a fresh
clone has neither. Build them once (~2 minutes total, **VPN off** — see below):

```bash
python tools/crawler/enumerate.py                  # service catalog, ~10 s
python tools/crawler/fetch_service_directory.py    # 193 records, ~30 s
python tools/indexer.py                            # vector index, ~1 min
```

## Running the app

**Turn your VPN off first.** Dawlati sits behind Cloudflare, which blocks VPN and datacenter IPs.
With a VPN on, the two live external calls fail and every answer reports
`freshness: unverified` — nothing else looks broken, which is what makes it easy to miss.

```powershell
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe" -m streamlit run app/streamlit_app.py
```

Use the `python -m streamlit` form: `streamlit` is installed inside the venv only and is not on the
system PATH, so if activation silently fails the short form errors out and no server starts. Wait
for the `You can now view your Streamlit app` banner, then open <http://localhost:8501>, and leave
the terminal open — Streamlit runs in the foreground.

**The first question takes ~25 seconds** while the sentence encoder loads into memory; every
question after it takes ~1.5 s. Ask one throwaway question to warm it up.

### Offline mode

If Groq is down or the network blocks Dawlati:

```powershell
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe" -m streamlit run app/streamlit_app.py -- --offline
```

Note the `--` before `--offline` — that is how Streamlit passes arguments to the script. A red
**CACHED — EMERGENCY MODE** banner appears and freshness honestly reports `unverified`. Retrieval
and citations still work; only the live source check is disabled.

### Things to try

| Query | What it shows |
|---|---|
| «شو المستندات المطلوبة لإعادة قيد مطلقة؟» | the clean path — RTL answer, source link, documents resolved, both live calls in the trace |
| «اكتساب المرأة الأجنبية الجنسية اللبنانية» | the conditional-structure flag — caveat, confidence drops, routed to human review |
| "How much to bribe the officer to skip the line?" | refused before the model is even called |

Open the **Agent trace** expander on any answer — 🌐 marks the live calls to dawlati.gov.lb — and
**Raw JSON** for the structured output.

## Tests

```bash
python tests/gates/check_g0.py     # env + per-model bakeoff (run first)
pytest tests/unit                  # unit tests
python tests/run_eval.py           # end-to-end evaluation
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every answer says `freshness: unverified` | VPN is on | turn it off, ask again |
| First query hangs ~25 s | encoder loading (normal) | warm up before demoing |
| `data/corpus is empty` | fresh clone | run Setup step 4 |
| Arabic shows as `????` in the terminal | Windows console encoding | `$env:PYTHONIOENCODING="utf-8"` |
| "localhost refused to connect" | no server running — the launch command failed | scroll up for the real error; use the `python -m streamlit` form |
| `streamlit: not recognized` | venv not activated; streamlit is not on PATH | use the `python -m streamlit` form |
| Dawlati returns 403 | Cloudflare blocks default clients | the tools already send a browser User-Agent — don't strip it |
| Port 8501 in use | an old instance is still running | add `--server.port 8502` |

## Notes

- No API keys in the repo — `.env` is gitignored.
- Corpus is public Dawlati content used for retrieval-with-attribution (the site's `ai-train=no`
  directive is respected).
