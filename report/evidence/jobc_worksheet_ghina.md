# Job C worksheet — **Ghina**

**This file is yours.** 27 services to judge. Budget **~45 minutes**.
Maria has the rest in her own file.

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

## 💍 زواج — Marriage

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11552 | 4 | ✓ | تسجيل زواج | `KEEP` |
| 2 | 11508 | 4 | ✓ | وثيقة زواج لزوجين لبنانيين | `KEEP` |
| 3 | 11502 | 4 | ✓ | وثيقة زواج واردة من الخارج لزوج لبناني وزوجة فلسطينية | `KEEP` |
| 4 | 11504 | 4 | ✓ | وثيقة زواج واردة من الخارج لزوج لبناني وزوجة سورية | `KEEP` |
| 5 | 11506 | 4 | ✓ | وثيقة زواج واردة من الخارج لزوج لبناني وزوجة قيد الدرس | `KEEP` |
| 6 | 11512 | 4 | ✓ | وثيقة زواج لزوجة لبنانية وزوج فلسطيني مسجل في | `KEEP` |
| 7 | 11530 | 4 | ✓ | وثيقة زواج لزوج لبناني وزوجة اجنبية | `KEEP` |
| 8 | 11510 | 4 | ✓ | وثيقة زواج لزوجة لبنانية وزوج أجنبي من غير الجنسية السورية | `KEEP` |
| 9 | 11514 | 4 | ✓ | وثيقة زواج لزوجة لبنانية وزوج من الجنسية السورية | `KEEP` |
| 10 | 11494 | 5 | ✓ | زواج حاصل في بيروت بين رجل أجنبي اومن الجنسية السورية | `KEEP` |
| 11 | 11546 | 4 | ✓ | تنفيذ وثيقة زواج بعد إبدال دين أو مذهب | `KEEP` |
| 12 | 11566 | 4 | ✓ | توحيد قيد الزوجين | `KEEP` |

**Notes on this group** (anything odd, duplicated, or miscategorised):
item 6 is missing part of the procedure name: المديرية العامة للأحوال الشخصية (دائرة النفوس) في لبنان
- 

## 💔 طلاق — Divorce

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11568 | 4 | ✓ | تسجيل طلاق | `KEEP` |
| 2 | 11532 | 5 | ✓ | إعادة قيد مطلقة *(Ghina checked this in Job B)* | `KEEP` |
| 3 | 11542 | 4 | ✓ | تنفيذ وثيقة طلاق بعد إبدال دين أو مذهب | `KEEP` |
| 4 | 11524 | 3 | ✓ | وثيقة طلاق واردة من الخارج (لبنانيان – لبناني وأجنبية او لبنانيه واجنبي) | `KEEP` |
| 5 | 11556 | 1 | ✓ | إعادة قيد مطلقة إلى قيد والديها | `KEEP` |
| 6 | 11492 | 6 | ✓ | طلاق حاصل في بيروت بين زوج أجنبي اومن الجنسية السورية أو من الجنسية قيد الدرس و بين زوجة لبنانية أو أجنبية مهما كانت جنسيتها | `KEEP` |
| 7 | 11474 | 0 ⚠️ | ✓ | مصادقة وثائق أحوال شخصية ( ولادة – وفاة – زواج- طلاق – إخراج قيد عائلي – إخراج قيد فردي- افادة قيد( | `SKIP` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

-No Notes 

## 📋 بيان قيد وسجلات — Civil extracts & registers

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11548 | 2 | ✓ | بيان قيد عائلي وإفرادي | `KEEP` |
| 2 | 11538 | 3 | ✓ | تنفيذ قرار قضائي بتصحيح قيود (في السجلات) | `KEEP` |
| 3 | 11470 | 1 | ✓ | طلب بيان قيد عن سجلات إحصاء ما قبل 1932 | `KEEP` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- 

## 📄 أخرى — Other (quick pass, most will be SKIP)

| # | id | docs | fees | service | KEEP / SKIP |
|---|---|---|---|---|---|
| 1 | 11484 | 4 | ✓ | إلغاء مراسيم الترخيص | `SKIP` |
| 2 | 11562 | 4 | ✓ | تنفيذ المراسيم | `SKIP` |
| 3 | 11480 | 2 | — | الاعتراض مع وقف التنفيذ على القرارات الرجائية | `SKIP` |
| 4 | 11486 | 2 | — | استحضارات الدعاوى | `SKIP` |
| 5 | 11564 | 2 | ✓ | تنفيذ الأحكام بعد صدورها | `SKIP` |

**Notes on this group** (anything odd, duplicated, or miscategorised):

- This group is SKIP because these are used by specilized professionals, mostly lawyers, not regular citizens.

---

# PART 2 — your 4 demo questions

Write **4 questions a real citizen would actually ask**, about services you marked KEEP.
Each one in **Arabic and English**. These become the questions we demo live in the
presentation and the test cases we score the system on — so they matter more than they look.

**Make one of them deliberately badly-phrased** — misspelled, too short, vague, or mixing
Arabic and English. Real people don't type neatly, and we get marked specifically on whether
the system copes. A question like «هوية» or "birth cert what papers" is *more* useful to us
than a perfectly formed sentence.

Suggested topics from your clusters (change freely): تسجيل زواج · تسجيل طلاق · بيان قيد عائلي وإفرادي · وثيقة زواج واردة من الخارج

### Question 1

- **Arabic:** كيف يمكنني تسجيل زواجي في لبنان؟
- **English:** How do i register my marriage in Lebanon?
- **Which service should answer it (id or name):** 11552

### Question 2

- **Arabic:** أين يمكنني الحصول على بيان قيد عائلي؟
- **English:** Where can i go to obtain a family civil registry? 
- **Which service should answer it (id or name):** 11548

### Question 3

- **Arabic:** كيف فيي أعمل وثيقة زاوج بعد ما غيرت ديني؟
- **English:** How can i register my marriage after changing my religion?
- **Which service should answer it (id or name):** 11546

### Question 4  ← make this one the messy/badly-phrased one

- **Arabic:** زواج من الخارج الأوراق؟
- **English:** marriage from abroad docs?
- **Which service should answer it (id or name):** 11530

---

# PART 3 — anything that looks wrong

While going through the list, flag anything suspicious:

- **Services that look like duplicates of each other:** NO
  - 
- **Titles that are garbled, cut off, or don't make sense:** item 6 within MArriage is missing part of the procedure name: المديرية العامة للأحوال الشخصية (دائرة النفوس) في لبنان

- **Procedures you know exist but are missing from the list entirely:** None
  - 
- **Anything else:** None
  - 

---

## When you're done

1. Send this back to Mariam (file, photo, or voice note — whatever's fastest).
2. **Swap with Maria** and glance at her KEEP/SKIP calls — same rule as last time, neither
   of us approves our own work. You don't need to re-judge everything; just flag anything you'd
   have decided differently.
None noted, all exceptions, justifications and observations detailed in the file.
**Why this one is urgent:** the system's testing and scoring are both blocked until this list
exists. It's the last thing standing between the data work and the finished project.
