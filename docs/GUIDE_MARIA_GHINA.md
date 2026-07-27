# Guide for Maria & Ghina — everything you need, A to Z

Written for you two specifically. **You do not need to install Python, write code, or understand the
repo.** Your job is the one thing nobody else on the team can do: you read Arabic and you understand
Lebanese government procedures, and right now the whole project is waiting on that.

Deadline: **Wednesday 29 July.** Your part is roughly **half a day each**, and it is on the critical
path — the code cannot be trusted until you sign off.

---

## 0. The 60-second version

We built a system that answers questions like *"what do I need to get a بطاقة هوية?"* by reading
Dawlati (dawlati.gov.lb) automatically. The computer already scraped 193 services. **But nobody has
checked whether the computer read them correctly.** That is your job:

1. **Maria** — confirm the AI model handles Arabic correctly (15 min).
2. **Both of you** — check that 8 scraped services match what the website actually says (~1 hour).
3. **Both of you** — pick the ~40 services the project will officially support (~2 hours, split).

Everything you need is a website + a text file. That's it.

### The split, at a glance

| | **Maria** | **Ghina** |
|---|---|---|
| **Job A** — bless the model's Arabic | ✅ yours (15 min) — *on hold, see §3* | — |
| **Job B** — verify extraction | `g2_worksheet_maria.md`<br>4 services · 15 docs · **2 field-by-field** | `g2_worksheet_ghina.md`<br>4 services · 28 docs · **1 field-by-field** |
| **Job C** — pick the core 40 | `jobc_worksheet_maria.md`<br>**هوية · ولادة · وفاة · جنسية** (26 rows) | `jobc_worksheet_ghina.md`<br>**زواج · طلاق · بيان قيد** (27 rows) |
| **Demo questions** | 4 | 4 |
| **You review** | Ghina's worksheet + her KEEP/SKIP calls | Maria's worksheet + her KEEP/SKIP calls |
| **Total** | ~half a day | ~half a day |

Neither of you signs off your own work — that's a hard project rule, explained in §4.

---

## 1. Setup — 15 minutes, no coding

### Step 1a — Get access to the repo

The project lives at **https://github.com/mariam-929/OnMyBehalf** — it's public, so you can *read*
everything right now with no account. To *write* (recommended, see §5), you need:

1. A free GitHub account → https://github.com/signup
2. Send Mariam your GitHub username and ask her to add you as a **collaborator**
   (she does: repo → Settings → Collaborators → Add people).
3. Accept the email invite.

### Step 1b — Decide how you want to read the files

Two options, pick whichever you prefer:

| | **Option A — in your browser (recommended)** | **Option B — files on your laptop** |
|---|---|---|
| How | Just open https://github.com/mariam-929/OnMyBehalf and click on files | Ask Mariam to share the `OnMyBehalf` folder over OneDrive |
| Arabic | Displays correctly | Displays correctly in VS Code / Notepad++ |
| Editing | Click the ✏️ pencil icon → type → "Commit changes" | Edit and save normally, then send back |
| Setup needed | none | none |

**Do not** follow `SETUP.md` — that's the developer setup (Python, virtual environments, a 500 MB
install). It exists for Ali/Gaby/Mariam. Nothing in your three jobs needs it.

### Step 1c — The one technical rule that will bite you

> ## ⚠ TURN YOUR VPN OFF before opening any dawlati.gov.lb page.
>
> Dawlati sits behind Cloudflare, which blocks VPN and datacenter IP addresses. With a VPN on you
> get a blank "Attention Required!" page and you will think the site is down. It isn't. This already
> cost Ali an afternoon of debugging.

---

## 2. The map — which files to look at, and in what order

You do **not** need to read the whole repo. Read these four, in this order:

| # | File | What it is | Time |
|---|---|---|---|
| 1 | `docs/PROGRESS.md` → the **▶ CURRENT STATE** block at the top | Where the project stands today. The single source of truth. Read *only* that block; ignore the long history below it. | 5 min |
| 2 | `report/evidence/g2_worksheet_maria.md` **or** `..._ghina.md` | **Your worksheet for Job B — take only the one with your name on it.** Pre-filled with what the computer extracted; you write the verdicts. | — |
| 3 | `report/evidence/core40_candidates.md` | **Your list for Job C.** Every service that actually exists on Dawlati, sorted by how many documents it has. | — |
| 4 | `docs/SCOPE.md` §§1–6 | What we promised to build (only if you're curious about the bigger picture) | 10 min, optional |

Files you can safely ignore: everything in `agents/`, `tools/`, `tests/`, `app/`,
`docs/TECH_PLAN.md`, `docs/SCHEMA_AND_CONTRACTS.md`, `docs/RESOLUTIONS.md`. That's the engineering.

**Useful background before you start (2 things the team discovered that will surprise you):**

- **Passports and driving licences DO NOT EXIST on Dawlati.** We assumed they would; they don't. The
  only «جواز سفر» result is *إصدار جواز سفر للخيل* — a horse passport. So the project has been
  rebuilt around the **civil-registry cluster** instead: بطاقة هوية، تسجيل ولادة / زواج / وفاة،
  بيان قيد. That's why Job C exists.
- **Only 3 of Lebanon's 22 ministries have published anything** (الزراعة، الداخلية، الثقافة).
  Dawlati says so itself on the guide page. That's the source's limitation, not ours, and we report
  it honestly.

---

## 3. Your three jobs

### 🔵 JOB A — Maria only: bless the AI model's Arabic (15 min)

**Why:** we tested two AI models on Arabic inputs and one won. The rules of this project say the
person who *ran* the test can't be the person who *approves* it — Mariam ran it, so she can't sign
it off. It needs a native Arabic reader who wasn't involved. That's you.

**⚠ Before you can start:** ask **Mariam** to send you the file
`report/evidence/bakeoff.md` — the model's 5 Arabic answers were only printed to her screen and
never saved, so she needs to re-run the test and save the output. **Ping her for this now**, then do
Jobs B and C while you wait; nothing else depends on Job A.

**What you do:** read the 5 Arabic test inputs and the model's classification of each. Four should
be classified `service_query` (a normal citizen question) and one should be `invalid_request` (it's
a deliberate prompt-injection attack we planted). Confirm:

- Did the model understand the Arabic correctly?
- Are the 5 classifications right?

**Done when:** you reply to the team — *"Maria confirms gpt-oss-120b handles Arabic correctly, all 5
classifications right"* — or list what's wrong. Mariam records it in `docs/PROGRESS.md`.

---

### 🟢 JOB B — Both of you: verify the extraction (~1 hour) — **CRITICAL PATH**

**Why:** the computer pulled documents/fees/authority for 193 services out of Dawlati's HTML.
Automatic extraction is often wrong in subtle ways — especially here, because Dawlati mixes numbered
and unnumbered items in one paragraph and contains its own typos. Until a human confirms the
extraction is accurate, every number in our final report is unproven.

**The work is already divided. Take the file with your name on it:**

| | **Maria** → `g2_worksheet_maria.md` | **Ghina** → `g2_worksheet_ghina.md` |
|---|---|---|
| 🔍 Field-by-field | **بطاقة هوية** (#11464, 9 docs)<br>**تسجيل ولادة** (#11554, 5 docs) | **إعادة قيد مطلقة** (#11532, 5 docs) |
| 👀 Skim | استيراد شتول (#11704, 1 doc)<br>تسجيل مزارع الدواجن (#11674, **0 docs**) | وثيقة ولادة واردة من الخارج (#11528, 11 docs)<br>اكتساب المرأة الأجنبية الجنسية (#11476, 7 docs)<br>محضر اعتراف بولادة غير شرعية (#11518, 5 docs) |
| Load | 4 services · 15 docs · 2 deep | 4 services · 28 docs · 1 deep |
| Time | ~40 min | ~40 min |

Ghina has more documents but fewer of the slow field-by-field ones — the two sides come out about
even. Maria takes the two headline services (هوية / تسجيل ولادة) because they're the demo cases and
she's the named G2 owner.

Inside your file, every document the computer extracted is numbered with a blank next to it. You
open the real page and write `OK` / `WRONG` / `NOT A DOCUMENT` / `SPLIT`.

**Then swap.** Part 2 of your file is a 10-minute review of the other person's four services — not a
redo, just a second pair of eyes saying AGREE or DISAGREE. Neither of you approves your own work.

**How to find a service on the live site:**

1. VPN **off**.
2. Open the services guide: https://dawlati.gov.lb/دليل-الخدمات/
3. Choose the ministry (most of these are **وزارة الداخلية والبلديات**).
4. Find the service by its Arabic title and expand it.

> **Don't** click the `dawlati.gov.lb/ministry_service_ser/...` links you'll see in our data files.
> Those individual pages are genuinely blank — all the content lives inside the guide page above.
> (We discovered this the hard way; it's in the report.)

**What we most need you to catch:**

- A document the website lists that we **missed entirely** ← the most damaging error
- Two documents **glued into one line** (mark `SPLIT`) — **Maria: look hard at document 2 of بطاقة
  هوية.** It has a stray `3.` sitting in the middle of it, which almost certainly means two separate
  documents got merged into one. If so, that's exactly the bug this whole check exists to find.
- **Maria: #11674 تسجيل مزارع الدواجن came out with zero documents.** Check whether the site really
  lists none, or whether our extraction dropped them. Either answer is useful.
- **Ghina: #11528 has 11 documents** — the longest in the set, so it's the most likely place for a
  `SPLIT` or a dropped item. Worth slowing down on despite being marked skim.
- Text that isn't a document at all (a note, an instruction, a location) sitting in the documents list
- Wrong fees or wrong "where to apply"

**Done when:** the worksheet is filled in and back with Mariam. She converts your answers into
`data/spike_gold.json`, re-runs the automated check, and the **G2 gate closes**. Target: ≥85% of the
real documents captured.

---

### 🟡 JOB C — Both of you: choose the core 40 services (~2 hours, split) — **CRITICAL PATH**

**Why:** the project promises "40 hand-verified core services" that the agent answers with high
confidence. The original 40 was written before we knew what Dawlati contains — it included passports
and driving licences, which don't exist. It has to be rebuilt from what's actually there, by people
who know which procedures Lebanese citizens actually need.

**Take the file with your name on it:** `report/evidence/jobc_worksheet_maria.md` or
`..._ghina.md`. Every service you need to judge is already in it, in a table, with its ID, document
count and whether it has fees. Nothing to look up.

**The split — by procedure family, so neither of you has to hold the whole domain in your head:**

| | **Maria — "the person"** | **Ghina — "the relationship & the register"** |
|---|---|---|
| Your clusters | 🪪 هوية (1)<br>👶 ولادة (8)<br>⚰️ وفاة (3)<br>🌍 جنسية (6)<br>📄 other (8) | 💍 زواج (12)<br>💔 طلاق (7)<br>📋 بيان قيد وسجلات (3)<br>📄 other (5) |
| Rows to judge | **26** | **27** |
| Demo questions | 4 | 4 |
| Time | ~45 min | ~45 min |

Ghina's marriage cluster has **9 near-identical وثيقة زواج rows** differing only by the spouses'
nationalities — judge the first properly and the rest go fast.

**This is smaller than it sounds.** There are only **53 civil-registry services in total** and we
want ~40 — so you're not picking 40 from hundreds, you're going through your list and cutting the
ones that don't belong. Most will be KEEP.

**You don't need to open the website for this job** unless a title looks wrong. It's a judgement
call from your own knowledge, not a verification task.

**What you do:** go down your rows and mark each **KEEP** or **SKIP**. Judge on:

- **Would a normal Lebanese citizen actually need this?** (بطاقة هوية = yes. *تسجيل مزارع الدواجن* =
  no.) Prioritise citizen-facing procedures over business/agricultural licensing.
- **Is the extracted data complete enough to answer with?** (a service with 0 documents is useless
  to us — SKIP it)
- **Spread:** we want the civil-registry cluster covered end to end (هوية، ولادة، زواج، وفاة، طلاق،
  بيان قيد), plus a handful of others so we're not a one-topic system.

**Also flag anything that looks wrong** — a title that's garbled, a duplicate, a service that clearly
isn't real. Several titles in the list are truncated mid-word; that's a display issue in our file,
not necessarily in the data, but tell us if a *service* looks wrong.

**And: 4 demo questions each** (8 total), from your own clusters — one natural question a citizen
would actually ask, in Arabic and English — e.g. *«شو المستندات المطلوبة لتسجيل ولادة؟»* / *"What do
I need to register a birth?"* These become our demo queries and test cases. **Write realistic
questions, including badly-phrased ones** — real users don't type neatly, and we're graded
specifically on handling that. One of your four should be deliberately messy.

**Done when:** the marked-up list is back with Mariam. She fills `data/curated_core.json`, and the
**G3 gate** opens.

---

## 4. What "done" actually means (and the one rule to remember)

Every stage of this project has a **gate**: an automated check the computer runs, plus a **human
check** a person signs. Claude/the code can run the automated half — it is explicitly forbidden from
faking the human half. That's why the project is currently sitting and waiting for you.

**The rule:** *the person who produced something cannot be the person who approves it.* This is why
Mariam can't sign her own bakeoff, and why you two should check each other's worksheets rather than
your own.

Your sign-offs close: **G0** (Maria), **G2** (both), **G3** (both). Three of the eleven gates.

---

## 5. How to hand your work back

Any of these is fine — pick the one you're comfortable with:

1. **GitHub web editor (best)** — open the file on github.com, click ✏️, type your answers, scroll
   down, "Commit changes". Your work is instantly visible to everyone and tracked.
2. **Download → edit → send** — download the `.md` file, edit it in Notepad/Word/VS Code, WhatsApp or
   email it back to Mariam.
3. **Just message the answers** — if a file feels like too much friction, send Mariam a voice note or
   a message: *"service 11464, document 2 is actually two documents, and they're missing X"*. Getting
   the information out of your head beats perfect formatting. **Do not let file formats block you.**

**However you do it, tell the team in the group chat when you're done** — Mariam needs to update
`docs/PROGRESS.md` and unblock the next step.

---

## 6. Rules that will save you pain

- **VPN off** for anything dawlati.gov.lb. (Say it three times.)
- **Never invent data.** If the website doesn't say the fee, the answer is "the website doesn't say
  it" — not a guess. The entire point of this project is that every answer is traceable to a source.
  A confident wrong answer is worse than an honest gap, both for citizens and for our grade.
- **Don't edit anything in `data/`, `agents/`, `tools/`, or `tests/`.** Those are code and machine
  files; changing them by hand breaks things silently. Stay in your two worksheet files.
- **Don't "fix" the `machine_documents` lists** in the worksheet — those are the computer's output
  and we need them unchanged to measure how wrong it was. Write your corrections in the blanks.
- **Nothing you find is bad news.** Every error you catch is a result we report in the paper
  ("human verification found N extraction errors") and a reason our approach is defensible. Finding
  problems *is* the deliverable.

---

## 7. If you *do* want the full developer setup (optional, not needed)

`SETUP.md` walks through it: install Python 3.12+, create a virtual environment **outside OneDrive**,
`pip install -r requirements.txt` (a few hundred MB — it pulls PyTorch), then get a free Groq API key
from https://console.groq.com. Budget an hour, and ask Ali or Mariam when it breaks. Genuinely
optional — none of Jobs A/B/C need it.

---

## 8. Who to ask

| Question about | Ask |
|---|---|
| The repo, the plan, where a file is, "am I doing this right?" | **Mariam** |
| The crawler, the data, why a page is empty | **Ali** |
| The model / retrieval | **Gaby** |
| Arabic or procedure judgement calls | **each other** — you two are the experts, that's the point |

**Start with Job B.** It's the one blocking everything else.
