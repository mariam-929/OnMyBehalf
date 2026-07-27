# Job C worksheet — **Maria**

**This file is yours.** 26 services to judge. Budget **~45 minutes**.
Ghina has the rest in her own file.

Same as last time: **a browser and this file. No software.**

## What this job is (it's different from the last one)

Last time you checked whether we read the website *correctly*. This time you're deciding
**which services the system should officially support.**

We promise in the project that 40 services are "hand-verified core" — the ones the agent
answers with high confidence. The original list of 40 was written before we knew what was
actually on Dawlati, and it was wrong (it had passports and driving licences, which don't
exist there). So it has to be rebuilt by people who know which procedures citizens actually
need. That's you.

**Good news: this is smaller than it sounds.** There are only **53 civil-registry services**
in total, and we want about 40. So you are not picking 40 out of hundreds — you're going
through your list and **cutting the ones that don't belong**. Most will be KEEP.

## How to judge each one

Write `KEEP` or `SKIP` next to each service. Ask yourself:

| Ask | KEEP if… | SKIP if… |
|---|---|---|
| **Would an ordinary citizen need this?** | a normal person walks in asking for it | it's internal admin, or for lawyers/officials |
| **Is it a real, distinct procedure?** | yes | it's a duplicate or a vague catch-all |
| **Do we have enough data to answer?** | it has documents listed | 0 documents — we'd have nothing to say |

**When in doubt, KEEP.** It's easier for us to drop one later than to discover we're missing
something during the demo.

> The number in the `docs` column is how many required documents we extracted. `0 docs` is a
> strong SKIP signal — the agent would have nothing useful to tell anyone.

**You do not need to open the website for this job** unless a title looks wrong or you're
unsure what a service is. This is a judgement call from your own knowledge, not a
verification task. If you do open it, VPN off as before.

---

# PART 1 — your services

## 🪪 بطاقة هوية — Identity

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11464 | 9 | ✓ | بطاقة هوية *(you checked this in Job B)* | `______` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

## 👶 ولادة — Birth

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11528 | 11 | ✓ | وثيقة ولادة واردة من الخارج *(Ghina checked this in Job B)* | `______` |
| 2 | 11518 | 5 | ✓ | محضر اعتراف بولادة غير شرعية *(Ghina checked this in Job B)* | `______` |
| 3 | 11554 | 5 | ✓ | تسجيل ولادة *(you checked this in Job B)* | `______` |
| 4 | 11490 | 4 | ✓ | ولادة مولود من أب أجنبي | `______` |
| 5 | 11540 | 4 | ✓ | تنفيذ قرار قضائي بقيد مولود | `______` |
| 6 | 11534 | 3 | ✓ | قيد مولود غير شرعي | `______` |
| 7 | 11536 | 3 | ✓ | قيد مولود حديث الولادة في سجلات النفوس اللبنانية | `______` |
| 8 | 11500 | 2 | ✓ | قرارات قنصلية (تصحيح تاريخ ولادة، تصحيح اسم، تصحيح شهرة، تصحيح جنس، تصحيح وضع عائلي&#8230;) واردة من الخارج | `______` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

## ⚰️ وفاة — Death

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11496 | 4 | ✓ | وفاة أجنبي ضمن نطاق محافظة بيروت | `______` |
| 2 | 11526 | 4 | ✓ | وثيقة وفاة واردة من الخارج | `______` |
| 3 | 11550 | 1 | ✓ | تسجيل وفاة | `______` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

## 🌍 جنسية — Nationality

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11476 | 7 | ✓ | اكتساب المرأة الأجنبية الجنسية اللبنانية بمفعول الزواج من لبناني *(Ghina checked this in Job B)* | `______` |
| 2 | 11478 | 6 | ✓ | إعادة الجنسية اللبنانية للمرأة اللبنانية التي خسرت جنسيتها اللبنانية لزواجها قبل 11/1/1960 من أجنبي | `______` |
| 3 | 11522 | 4 | ✓ | طلب المرأة الأجنبية اكتساب الجنسية اللبنانية لزواجها من لبناني | `______` |
| 4 | 11520 | 3 | ✓ | طلب الشخص اللبناني التخلي عن الجنسية اللبنانية | `______` |
| 5 | 11482 | 2 | ✓ | طلب الترخيص لاكتساب جنسية أجنبية | `______` |
| 6 | 11488 | 2 | ✓ | طلب تنفيذ مرسوم التجنس | `______` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

## 📄 أخرى — Other (quick pass, most will be SKIP)

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11516 | 4 | ✓ | إبدال دين أو مذهب وارد من الخارج | `______` |
| 2 | 11558 | 3 | ✓ | إبدال دين او مذهب | `______` |
| 3 | 11544 | 2 | ✓ | وثيقة تبديل مكان | `______` |
| 4 | 11498 | 1 | ✓ | طلب نسخة عن وثائق منفذة | `______` |
| 5 | 11560 | 1 | ✓ | نسخ طبق الأصل عن وثائق الوقوعات المنفذة | `______` |
| 6 | 11466 | 3 | — | تصحيح أو إضافة اسم على لوائح الشطب | `______` |
| 7 | 11468 | 2 | ✓ | الحصول على لوائح الشطب | `______` |
| 8 | 11472 | 2 | ✓ | شكاوى | `______` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

---

# PART 2 — your 4 demo questions

Write **4 questions a real citizen would actually ask**, about services you marked KEEP.
Each one in **Arabic and English**. These become the questions we demo live in the
presentation and the test cases we score the system on — so they matter more than they look.

**Make one of them deliberately badly-phrased** — misspelled, too short, vague, or mixing
Arabic and English. Real people don't type neatly, and we get marked specifically on whether
the system copes. A question like «هوية» or "birth cert what papers" is *more* useful to us
than a perfectly formed sentence.

Suggested topics from your clusters (change freely): بطاقة هوية · تسجيل ولادة · تسجيل وفاة · اكتساب الجنسية

### Question 1

- **Arabic:** 
- **English:** 
- **Which service should answer it (id or name):** 

### Question 2

- **Arabic:** 
- **English:** 
- **Which service should answer it (id or name):** 

### Question 3

- **Arabic:** 
- **English:** 
- **Which service should answer it (id or name):** 

### Question 4  ← make this one the messy/badly-phrased one

- **Arabic:** 
- **English:** 
- **Which service should answer it (id or name):** 

---

# PART 3 — anything that looks wrong

While going through the list, flag anything suspicious:

- **Services that look like duplicates of each other:**
  - 
- **Titles that are garbled, cut off, or don't make sense:**
  - 
- **Procedures you know exist but are missing from the list entirely:**
  - 
- **Anything else:**
  - 

---

## When you're done

1. Send this back to Mariam (file, photo, or voice note — whatever's fastest).
2. **Swap with Ghina** and glance at her KEEP/SKIP calls — same rule as last time, neither
   of us approves our own work. You don't need to re-judge everything; just flag anything you'd
   have decided differently.

**Why this one is urgent:** the system's testing and scoring are both blocked until this list
exists. It's the last thing standing between the data work and the finished project.
