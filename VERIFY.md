# How to check this work

Written so you can **catch mistakes**, not just confirm the happy path. Every number I reported is
reproducible from this repo; where a claim is weaker than it sounds, this file says where to look.

Run everything with the venv Python and the encoder set:

```powershell
$env:EMBED_MODEL="sentence-transformers/LaBSE"
$P="C:\Users\Mariam\venvs\OnMyBehalf\Scripts\python.exe"
```

---

## Level 1 — five minutes, does it actually work

```powershell
& $P tools/crawler/fetch_service_directory.py   # rebuilds 193 records (~30 s, VPN OFF)
& $P tools/indexer.py                           # rebuilds the index (~1 min)
streamlit run app/streamlit_app.py
```

Ask it: **«شو المستندات المطلوبة لإعادة قيد مطلقة؟»**

You should see an Arabic answer rendering **right-to-left**, a source link to dawlati.gov.lb,
5 documents with "where to obtain" under 4 of them, a confidence number, and an **Agent trace**
expander containing two 🌐 external calls. Open the Raw JSON expander — that is the structured
output the brief requires.

**If the first query takes ~25 s, that is the encoder loading.** Ask a second question; it should
take ~1.5 s. **Warm it up before the demo.**

---

## Level 2 — run the gates yourself

```powershell
& $P -m pytest tests/unit -q            # expect: 64 passed
& $P tests/gates/check_g5.py            # expect: AUTO GATE: PASS
& $P tests/gates/check_g9.py            # expect: AUTO GATE: PASS
& $P tests/gates/check_g2.py            # expect: PASS, recall 90%, precision 81%
& $P tests/gates/check_g6.py            # expect: PASS 8/8, both external calls listed
& $P tests/gates/check_g4.py            # expect: FAIL 2/4 — this is honest, see below
& $P tests/run_eval.py                  # expect: 36.4% failure, 0 hallucinations
```

**`check_g4.py` failing is not a mistake.** It reports top-1 88% and abstention 1/3 and fails its
own bar. Leaving a gate failing rather than lowering the bar is deliberate.

---

## Level 3 — spot-check the claims that matter

### The claim I'd challenge first: "0 hallucinations"

This is the weakest-sounding-strong number. Check that the detector actually detects:

```powershell
& $P -c "import sys; sys.path.insert(0,'.'); sys.argv=['x']
import json
from tests.run_eval import count_hallucinated_documents
rec=json.load(open('data/corpus/11532.json',encoding='utf-8'))
env={'output':{'service':{'source_url':rec['url']},'required_documents':[
  {'name_ar':'شهادة حسن سلوك من مخفر الشرطة'}]}}
print(count_hallucinated_documents(env))"
```

Expect `(1, ['شهادة حسن سلوك…'])` — it catches an injected fabrication.

**But read REPORT §6.1 before quoting the zero.** Documents are *passed through* from the retrieved
record, not generated, so fabrication is structurally impossible in that list. Zero is a real
measurement of an architectural property, **not evidence that the model resists hallucination.**
If a grader asks "so your LLM never hallucinates?", the honest answer is "our document list can't,
by construction — here's why."

### The failure that is our best demo moment

```powershell
& $P -c "import sys; sys.path.insert(0,'.')
from tools.search_services import search_services
for c in search_services('شو بدي لأجدد جواز سفري؟',k=2): print(c.dense_cos, c.post_id, c.title_ar)"
```

Expect **`إصدار جواز سفر للخيل`** — a horse passport — as the top hit. Passports for people don't
exist on Dawlati. This is failure mode 2 in the report.

### Verify the experts' work was used faithfully

Open `report/evidence/g2_worksheet_maria_FULL.md` and `..._ghina (Final).md`, pick any document
they marked `NOT A DOCUMENT`, and confirm it is **absent** from `data/spike_gold.json`
`gold_documents`. Their verdicts drove the 90% recall figure; if a rejected item survived into
gold, the number is wrong.

Same for Job C: every `KEEP` in `jobc_worksheet_*.md` should appear in `data/curated_core.json`
(44 entries), every `SKIP` in the `skipped` list with its reason.

---

## Level 4 — things I would check if I were auditing me

| Check | Command / where | What would be wrong |
|---|---|---|
| No secrets committed | `git grep -nE "gsk_[A-Za-z0-9]{20}" $(git rev-list --all)` | any hit = a real key in history |
| `.env` untracked | `git ls-files .env` | any output = leaked |
| Gate ≠ runtime drift | `agents/nodes/retrieve.py::classify_outcome` is imported by `check_g4.py` | if they diverge again, the gate stops testing the system |
| Numbers match artefacts | `tests/eval_report.json` vs REPORT §6.1 | any mismatch = report drifted from evidence |
| Retracted claim is retracted | `report/evidence/retrieval.md` top | it must still say 100% was **wrong**, not quietly say 88% |
| No faked sign-offs | `docs/PROGRESS.md` gate record | any human sign-off filled in by me rather than a person |

---

## What is genuinely NOT done

Don't let the passing gates give a false impression:

- **G7** — freshness and queue code exists and is unit-tested, but `diff_recrawl.py` is still a stub.
- **G10** — repo hygiene, secret scan, README refresh not done.
- **G11** — demo rehearsals and the backup video. Human-only, and yours.
- **G3** — core-44 and gold exist; the **≥20-row source-checked lookup table does not**.
- **G0** — still needs Maria's Arabic sign-off, which needs `report/evidence/bakeoff.md`
  regenerated (the original outputs were printed to console and never saved).
- **`data/` is gitignored.** A fresh clone has no corpus and no index until the first two commands
  in Level 1 are run. If someone clones and the app is empty, that is why.

---

## Fastest way to find me out

Ask the system a question **neither I nor the experts wrote**, about a civil-registry service you
know exists, and see whether the answer is right and the source link goes where it claims.

That is the test that has embarrassed this project twice already — first when the experts' own
questions dropped retrieval to 3/8, and again when a representative gold set dropped top-1 from
"100%" to 88%. **Independent input has consistently made the numbers worse.** A third round would
most likely do the same, and that is worth knowing before you present rather than during Q&A.
