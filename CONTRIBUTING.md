# CONTRIBUTING — start here (team quickstart)

Team: **Gaby, Mariam, Ali, Ghina, Maria.** Deadline: **Wed Jul 29**. This file tells you where your
part is, how the work splits, and the workflow. Full plan lives in `docs/`.

## 1. First 20 minutes (everyone, once)
1. Read this file + `docs/PROGRESS.md` ("Where we are" + the gate/owner table + the checklist).
2. Do `SETUP.md` (clone → venv → `pip install` → `.env` with your Groq key). Everyone should be able
   to run `python tests/gates/check_g0.py`.
3. Skim `docs/SCOPE.md` (what we're building) and `docs/SCHEMA_AND_CONTRACTS.md` (the data shapes —
   this is the contract everyone codes against).

## 2. Can we work in parallel? YES — here's the dependency map

The plan is built to parallelize. **`agents/models.py` (the typed schema) is the decoupling layer:**
as long as everyone codes to those types, you can build your piece against fixtures/mocks without
waiting for someone else's piece to exist.

What's genuinely serial (the only hard blockers):
- **G0 (bakeoff) comes first** — it picks the model. ~2 hours, one person runs it; everyone else
  does SETUP + reads docs meanwhile. Nothing else starts until G0 passes.
- **Integration join (G6, Jul 27):** the agent end-to-end needs BOTH the real index (DATA track)
  AND the graph (BUILD track) to exist. The two tracks run in parallel Jul 26, then meet here.
- **Eval (G8)** needs a working agent + the gold data from core verification (G3).
- **Report/demo** at the end — but draft your sections continuously, don't batch them.

Everything else runs at the same time:

```
Jul 25:  G0 bakeoff (Gaby) ── everyone else: SETUP + read docs
                │
Jul 26:  ┌──────┴───────── two parallel tracks ─────────────┐
         │ DATA (laptop/network, IO-bound)   BUILD (code, on fixtures) │
         │  Ali: crawl + catalog + contacts   Mariam: graph + state + nodes │
         │  Gaby: index + RRF retrieval       (codes against models.py)      │
         │  Maria+Ghina+all: verify 40 core   prompts iteration (shared)      │
         └──────┬───────────────────────────────────┬───────┘
Jul 27:         └────────── converge at G6 ──────────┘  + UI shell (whoever's free)
Jul 28:  eval G8 (Mariam+Ghina) ∥ UI finish ∥ competitor test ∥ report §§1–4
Jul 29:  report + repo + demo rehearsal (all)
```

## 3. Suggested work-stream ownership (from docs/PROGRESS.md gate table)

| Stream | Lead(s) | Files | Gate |
|---|---|---|---|
| Crawl · catalog · contacts | **Ali** | `tools/crawler/*` | G1, G1b, G2 |
| Index · retrieval (RRF) | **Gaby** | `tools/indexer.py`, `tools/search_services.py` | G4 |
| Core verification + gold data (domain-critical) | **Maria + Ghina** (all split 40 ≈ 8 each) | `data/core_verification.csv`, `tests/gold_claims.json`, `data/document_sources.json` | G3 |
| Agent graph · nodes · research loop | **Mariam** | `agents/graph.py`, `agents/nodes/*`, `tools/resolve_document.py` | G5, G6 |
| Prompts iteration | **shared** (whoever hits a failure logs it) | `prompts/*_v1.md`, `prompts/ITERATION_LOG.md` | G6/G8 |
| Eval harness + failure analysis | **Mariam + Ghina** | `tests/run_eval.py`, `tests/test_cases.json` | G8 |
| Streamlit UI (RTL, trace, offline) | **Gaby** (or first free) | `app/streamlit_app.py` | G9 |
| Report (55%!) + repo hygiene | **Mariam** coord; each writes their section | `report/` | G10 |
| Demo + video | **all** (each justifies their own decisions in Q&A) | — | G11 |

These are starting points — swap freely; just update the owner in `docs/PROGRESS.md`.

## 4. Workflow (keep it light, we have 4 days)
- Branch per work-stream: `git checkout -b data-crawl` / `build-graph` / etc. Small PRs into `main`;
  a quick review by your gate's **Reviewer** (see PROGRESS table), then merge.
- **After finishing a task, tick it in `docs/PROGRESS.md` and add a one-line session-log entry.**
  Push it — that file is how everyone sees live status.
- A gate's **automated** check (`tests/gates/check_gN.py`) must pass before its **human** check;
  the human check is signed by someone who ISN'T the person who built it.
- Never commit `.env` or keys (already gitignored; the G10 gate scans history).

## 5. Where things are
- `docs/` — the plan: SCOPE, SCHEMA_AND_CONTRACTS, TECH_PLAN, VERIFICATION, PROGRESS, RESOLUTIONS
  (+ `reviews/` = the decision/audit trail, useful for the report's "decisions" section).
- `agents/` `tools/` `prompts/` `tests/` `data/` `app/` `report/` — code + artifacts.
- `SETUP.md` — environment. `CLAUDE.md` — context for anyone using Claude Code on the repo.
