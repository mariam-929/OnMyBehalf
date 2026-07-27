# Launching the app — A to Z

For the demo, skip to **"Demo day"** at the bottom.

---

## Step 0 — turn your VPN OFF

Dawlati sits behind Cloudflare, which blocks VPN and datacenter IPs. With a VPN on, the two live
external calls fail and every answer shows `freshness: unverified`. Nothing else looks broken,
which is what makes it easy to miss.

---

## Step 1 — open a terminal in the project folder

```powershell
cd "C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\OnMyBehalf"
```

## Step 2 — activate the virtual environment

```powershell
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\Activate.ps1"
```

Your prompt should now start with `(OnMyBehalf)`. If activation is blocked by execution policy,
skip it and use the full interpreter path everywhere instead:
`& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe"`.

## Step 3 — make sure the data exists

`data/` is gitignored, so a fresh clone has no corpus and no index. Check:

```powershell
if (Test-Path data\corpus) { (Get-ChildItem data\corpus).Count } else { "MISSING" }
if (Test-Path data\chroma) { "index present" } else { "MISSING" }
```

Expect **193** and **index present**. If either is missing, build them (VPN off):

```powershell
python tools/crawler/enumerate.py                  # catalog, ~10 s
python tools/crawler/fetch_service_directory.py    # 193 records, ~30 s
python tools/indexer.py                            # index, ~1 min
```

> You only do this once, or after changing the extraction or the encoder.

## Step 4 — check the Groq key is set

```powershell
Get-Content .env | Select-String "GROQ_API_KEY"
```

Should show `GROQ_API_KEY=gsk_…`. **The app still runs without it** — it falls back to a
deterministic intent classifier — but the demo is stronger with the model in the loop.

## Step 5 — launch

**Use this form — it needs no activation and no PATH:**

```powershell
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe" -m streamlit run app/streamlit_app.py
```

Wait for this banner before opening the browser:

```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

**No banner means no server.** Read the error printed above it — do not open the browser and
conclude the app is broken.

**Keep this terminal open.** Streamlit runs in the foreground; closing the window or pressing
`Ctrl+C` stops the server and the page dies.

<details><summary>Why not the short <code>streamlit run …</code> form?</summary>

`streamlit` is installed **inside the venv only** and is not on the system PATH. If
`Activate.ps1` silently fails — which it does whenever PowerShell's execution policy blocks
scripts — then `streamlit run` errors with *"not recognized"*, no server starts, and the browser
reports **"localhost refused to connect"**. The `python.exe -m streamlit` form cannot hit that.
</details>

## Step 6 — warm it up before anyone is watching

**The first question takes ~25 seconds** — that is the sentence encoder loading into memory.
Every question after it takes ~1.5 s. Ask one throwaway question immediately after launch.

---

## Try these

| query | what it shows |
|---|---|
| «شو المستندات المطلوبة لإعادة قيد مطلقة؟» | the clean path — RTL answer, source link, 4/5 documents resolved, both external calls in the trace |
| «اكتساب المرأة الأجنبية الجنسية اللبنانية» | the **conditional-structure flag** — caveat, confidence drops to ~0.3, flagged for human review |
| "How much to bribe the officer to skip the line?" | refused before the model is even called |
| «شو بدي لأجدد جواز سفري؟» | the honest failure — returns a **horse** passport |

Open the **Agent trace** expander on any answer: 🌐 marks the two live calls to dawlati.gov.lb.
Open **Raw JSON** for the structured output.

---

## Offline / emergency mode

If Groq is down or the venue's network blocks Dawlati:

```powershell
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe" -m streamlit run app/streamlit_app.py -- --offline
```

Note the `--` before `--offline`; that is how Streamlit passes arguments to the script. A red
**CACHED — EMERGENCY MODE** banner appears and freshness reports `unverified`, honestly. Retrieval
and citations still work — only the live source check is disabled.

---

## When something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Every answer says `freshness: unverified` | **VPN is on** | turn it off, ask again |
| First query hangs ~25 s | encoder loading (normal) | warm up before demoing |
| `data/corpus is empty` | fresh clone | run Step 3 |
| Arabic shows as `????` in the terminal | Windows console encoding | `$env:PYTHONIOENCODING="utf-8"` |
| **"localhost refused to connect"** | **no server is running** — the launch command failed | scroll up in the terminal for the real error; use the `python.exe -m streamlit` form in Step 5 |
| `streamlit: command not found` / `not recognized` | venv not activated, and `streamlit` is not on the system PATH | use the `python.exe -m streamlit` form in Step 5 |
| Page was working, now dead | terminal was closed or `Ctrl+C` pressed | relaunch; keep the terminal open |
| Port 8501 already in use | an old instance is still running | add `--server.port 8502` to the launch command, or close the old terminal |
| Answers look right but confidence is low | usually correct — freshness or an unresolved document | open the trace; the deductions are listed |

---

## Demo day — the short version

```powershell
cd "C:\Users\Mariam\OneDrive - American University of Beirut\Documents\summer 2026\nlp\OnMyBehalf"
& "$env:USERPROFILE\venvs\OnMyBehalf\Scripts\python.exe" -m streamlit run app/streamlit_app.py
```

Wait for the **"You can now view your Streamlit app"** banner, then open
<http://localhost:8501>. Leave the terminal open.

Then, before the audience is watching:

1. **VPN off.**
2. Ask one throwaway question to load the encoder.
3. Have a second terminal ready with the offline command in case the network fails.
4. Have `prompts/intent_classifier_v1.md` open in a tab — the brief requires the system prompt
   on screen.
