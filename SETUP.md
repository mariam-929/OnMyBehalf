# SETUP.md — OnMyBehalf environment setup (end to end)

Follow top to bottom. Tested on Windows 11 (the team's setup); notes for the Microsoft-Store
Python and OneDrive gotchas are included. **Keep this file current: whenever anyone adds or removes
a dependency, update `requirements.txt` AND the Dependencies table below in the same commit.**

---

## 0. Prerequisites — check these first (download anything missing)

| Tool | Min version | Check | Get it |
|---|---|---|---|
| Python | 3.12+ | `python --version` | https://www.python.org/downloads/ (prefer the python.org installer over the Microsoft Store build — see note ⚠) |
| Git | 2.4+ | `git --version` | https://git-scm.com/download/win |
| GitHub CLI (optional) | 2.x | `gh --version` | https://cli.github.com (only needed to create/manage the repo) |
| Groq API key | — | — | https://console.groq.com → sign in (no credit card) → API Keys → Create |

Nothing else is required up front. **Node.js is NOT needed.** Playwright downloads its own browser
in step 4 (~150 MB).

⚠ **Microsoft-Store Python gotcha:** the Store build of Python redirects `AppData\Local`, which
breaks venvs created there. If `python` is the Store build, either install python.org Python, or
just follow step 2 which puts the venv outside `AppData\Local`.

---

## 1. Get the code

```powershell
git clone https://github.com/mariam-929/OnMyBehalf.git
cd OnMyBehalf
```
(If you already have the folder, just `cd` into it.)

---

## 2. Create & activate the virtual environment

⚠ **Do NOT put the venv inside a OneDrive-synced folder** — OneDrive tries to sync its tens of
thousands of files, which is slow and causes file locks. Put it outside OneDrive:

```powershell
# recommended: venv outside OneDrive and outside AppData\Local
python -m venv "$env:USERPROFILE\venvs\OnMyBehalf"
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\Activate.ps1"
```
Your prompt should now show `(OnMyBehalf)`. To reactivate later, re-run the `Activate.ps1` line.

<details><summary>Git Bash / macOS / Linux equivalent</summary>

```bash
python -m venv ~/venvs/OnMyBehalf
source ~/venvs/OnMyBehalf/Scripts/activate   # macOS/Linux: .../bin/activate
```
</details>

If your clone is NOT under OneDrive, an in-repo `.venv` is fine (`python -m venv .venv`); it's
already gitignored.

---

## 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```
This pulls PyTorch + sentence-transformers (for BGE-M3 embeddings), ChromaDB, LangGraph, the Groq
SDK, Streamlit, Playwright, etc. First run is a few minutes and a few hundred MB.

---

## 4. Install the Playwright browser (needed for crawling, from Jul 26)

```powershell
playwright install chromium
```
Not needed to run the G0 bakeoff; required before the corpus crawl (G2) and directory/contacts
crawl (G1b).

---

## 5. Configure your Groq key

```powershell
copy .env.example .env
```
Open `.env` and paste your key:
```
GROQ_API_KEY=gsk_...your key...
MODEL_ID=openai/gpt-oss-120b   # updated after the G0 bakeoff picks the winner
```
**Never commit `.env`** — it's gitignored, and the G10 gate scans history for keys. Keep any loose
key `.txt` OUTSIDE the repo folder.

---

## 6. Verify the install

```powershell
python -c "import langgraph, groq, chromadb, sentence_transformers, streamlit, playwright; print('imports OK')"
python tests/gates/check_g0.py     # the G0 bakeoff (needs GROQ_API_KEY set)
```
`check_g0.py` runs both candidate models on 10 Arabic/English fixtures, prints schema-validity +
latency, and writes live rate limits to `data/model_limits.json`. A human (Maria) then reads the 5
Arabic outputs to bless the winner.

---

## 7. Launch the app

The Streamlit chat UI (functional from G9, Jul 27–28):
```powershell
streamlit run app/streamlit_app.py
```
It opens at http://localhost:8501. Emergency offline demo mode (after caches exist):
```powershell
streamlit run app/streamlit_app.py -- --offline
```

Other entry points as the build progresses:
```powershell
python tools/crawler/enumerate.py     # G1: build data/catalog.json (works now)
python tests/gates/check_g0.py        # G0 gate
pytest tests/unit                     # unit tests (from G5)
```

---

## 8. Dependency-update protocol (keep this file + requirements.txt in lockstep)

When you add or remove a package:
1. `pip install <pkg>` into the activated venv.
2. Add it (with a version) to `requirements.txt`.
3. Add a row to the **Dependencies** table below with what it's for.
4. Commit `requirements.txt` + `SETUP.md` together.
5. At/after G0 we freeze everything to exact `==` versions via `pip freeze`.

### Dependencies (why each is here)
| Package | Purpose |
|---|---|
| langgraph, langgraph-prebuilt | agent runtime / state graph |
| langchain-groq, groq | Groq LLM client (per-model adapters) |
| pydantic | schema / guardrail (single source of truth) |
| chromadb | local vector store (RAG) |
| sentence-transformers | BGE-M3 embeddings (Arabic + cross-lingual) |
| rank-bm25 | BM25 keyword channel for hybrid retrieval |
| playwright | render JS pages for the crawl + contacts |
| requests | REST calls (catalog, freshness, live lookup) |
| portalocker | append-safe review-queue writes |
| streamlit | chat UI |
| python-dotenv | load `.env` |
| pytest | unit + gate tests |

---

## 9. Troubleshooting

- **Arabic shows as `????` in the console:** set `PYTHONIOENCODING=utf-8` (it's in `.env.example`);
  in PowerShell you can also run `$env:PYTHONIOENCODING="utf-8"`.
- **Dawlati requests return 403:** the crawler/tools already send a browser User-Agent (Cloudflare
  blocks default clients). Don't strip it.
- **Torch install is slow/large:** normal on first run; it's CPU-only and cached afterward.
- **OneDrive locking files / “resource busy”:** keep the venv out of OneDrive (step 2); pause
  OneDrive sync during heavy installs if needed.
- **`playwright` command not found:** ensure the venv is activated; it's installed by step 3.
