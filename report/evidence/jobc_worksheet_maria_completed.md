# Job C worksheet — **Maria** (Completed)

**Task:** decide which civil-registry services the agent officially supports (target ~40 of 53).
**Rule applied:** KEEP if an ordinary citizen needs it, it's a distinct procedure, and it has documents. SKIP if internal/admin, a duplicate, or 0 docs. When in doubt, KEEP.
**My tally:** 23 KEEP · 3 SKIP (all removals carry a note for Mariam to verify).

---

# PART 1 — KEEP / SKIP

## 🪪 Identity
| id | docs | service | Call |
|---|---|---|---|
| 11464 | 9 | بطاقة هوية | **KEEP** |

## 👶 Birth — all KEEP
| id | docs | service | Call |
|---|---|---|---|
| 11528 | 11 | وثيقة ولادة واردة من الخارج | **KEEP** |
| 11518 | 5 | محضر اعتراف بولادة غير شرعية | **KEEP** *(flagged — niche; possible overlap with 11534)* |
| 11554 | 5 | تسجيل ولادة | **KEEP** (core) |
| 11490 | 4 | ولادة مولود من أب أجنبي | **KEEP** |
| 11540 | 4 | تنفيذ قرار قضائي بقيد مولود | **KEEP** |
| 11534 | 3 | قيد مولود غير شرعي | **KEEP** |
| 11536 | 3 | قيد مولود حديث الولادة | **KEEP** |
| 11500 | 2 | قرارات قنصلية (تصحيح تاريخ/اسم/شهرة/جنس/وضع عائلي) واردة من الخارج | **KEEP** *(note: catch-all bundling several corrections)* |

## ⚰️ Death — all KEEP
| id | docs | service | Call |
|---|---|---|---|
| 11496 | 4 | وفاة أجنبي ضمن نطاق محافظة بيروت | **KEEP** *(flagged — oddly Beirut-governorate-only scope)* |
| 11526 | 4 | وثيقة وفاة واردة من الخارج | **KEEP** |
| 11550 | 1 | تسجيل وفاة | **KEEP** (core) *(flagged — only 1 doc captured; likely under-extracted)* |

## 🌍 Nationality
| id | docs | service | Call |
|---|---|---|---|
| 11476 | 7 | اكتساب المرأة الأجنبية الجنسية اللبنانية بمفعول الزواج من لبناني | **KEEP** |
| 11478 | 6 | إعادة الجنسية للمرأة التي خسرتها لزواجها قبل 11/1/1960 | **KEEP** *(niche — specific historical cohort)* |
| 11522 | 4 | طلب المرأة الأجنبية اكتساب الجنسية لزواجها من لبناني | **SKIP** — see note below |
| 11520 | 3 | طلب الشخص اللبناني التخلي عن الجنسية اللبنانية | **KEEP** *(flagged — uncommon procedure)* |
| 11482 | 2 | طلب الترخيص لاكتساب جنسية أجنبية | **KEEP** |
| 11488 | 2 | طلب تنفيذ مرسوم التجنس | **KEEP** *(borderline — leans official)* |

## 📄 Other
| id | docs | service | Call |
|---|---|---|---|
| 11516 | 4 | إبدال دين أو مذهب وارد من الخارج | **KEEP** |
| 11558 | 3 | إبدال دين او مذهب | **KEEP** *(local version of 11516 — a pair, NOT a duplicate; keep both)* |
| 11544 | 2 | وثيقة تبديل مكان | **KEEP** *(flagged — title vague, worth a site check)* |
| 11498 | 1 | طلب نسخة عن وثائق منفذة | **SKIP** — see note below |
| 11560 | 1 | نسخ طبق الأصل عن وثائق الوقوعات المنفذة | **KEEP** (kept as the surviving copy of the 11498/11560 pair) |
| 11466 | 3 | تصحيح أو إضافة اسم على لوائح الشطب | **KEEP** *(no fee listed — data gap, not a reason to drop)* |
| 11468 | 2 | الحصول على لوائح الشطب | **KEEP** *(borderline — electoral admin)* |
| 11472 | 2 | شكاوى | **SKIP** *(vague catch-all — not a distinct procedure with a real citizen document checklist)* |

### Notes on the SKIPs (Mariam — please verify these before final)
- **11472 (شكاوى)** — removed. "Complaints" is a catch-all, not a distinct procedure a citizen brings documents for.
- **11522** — removed as **probable duplicate of 11476** (both = a foreign woman acquiring Lebanese nationality by marriage to a Lebanese man). Wording differs (بمفعول الزواج vs لزواجها + طلب) but the procedure looks identical; doc counts differ (7 vs 4), suggesting the same service captured twice. Kept the richer 11476. **If they turn out to be genuinely distinct, put 11522 back.**
- **11498** — removed as **duplicate of 11560** (both = obtaining a certified copy of executed documents). Kept 11560. **Please confirm they're truly identical.**

---

# PART 2 — 4 demo questions

*(Draft phrasings — Arabic reviewed to sound like real citizen input.)*

### Question 1 — clean
- **Arabic:** شو الأوراق المطلوبة لتجديد بطاقة الهوية؟
- **English:** What documents do I need to renew my ID card?
- **Should answer:** 11464 (بطاقة هوية)

### Question 2 — clean
- **Arabic:** كيف بسجّل ولادة طفلي وشو بيلزمني؟
- **English:** How do I register my child's birth and what do I need?
- **Should answer:** 11554 (تسجيل ولادة)

### Question 3 — clean
- **Arabic:** أنا أجنبية ومتزوجة من لبناني، كيف بقدر أحصل على الجنسية اللبنانية؟
- **English:** I'm a foreign woman married to a Lebanese man — how can I get Lebanese nationality?
- **Should answer:** 11476 (اكتساب الجنسية بالزواج)

### Question 4 — THE MESSY ONE (misspelled + too short + broken grammar)
- **Arabic:** تسجيل وفاه شو بدي
- **English:** death registration what paper need
- **Should answer:** 11550 (تسجيل وفاة)
- *(Deliberately messy: typo وفاه→وفاة, no punctuation, telegraphic, broken English — tests whether the system copes with real sloppy input.)*

---

# PART 3 — anything that looks wrong

**Possible duplicates:**
- 11522 ↔ 11476 (foreign woman, nationality by marriage) — removed 11522 pending verification.
- 11498 ↔ 11560 (certified copies of executed documents) — removed 11498 pending verification.

**Vague / garbled / catch-all titles:**
- 11544 (وثيقة تبديل مكان) — unclear what the service actually is; worth opening on the site.
- 11500 (consular corrections) — a catch-all bundling several different corrections (date, name, surname, gender, family status) into one service.

**Oddly scoped:**
- 11496 (death of a foreigner) — limited to Beirut governorate only. Why just Beirut? Possible other governorate versions elsewhere, or miscategorised.

**Low / suspicious data:**
- 11550 (تسجيل وفاة) — only 1 document captured for a core service; likely under-extracted.

**Missing procedures I know exist but aren't on my list:**
- Couldn't confirm from my half alone — e.g. **marriage registration (تسجيل زواج)** doesn't appear on my 26, but it may be on Ghina's list. Worth checking against the combined 53 before concluding anything is genuinely missing.

**Related-but-not-duplicate pairs (keep both — don't let anyone merge):**
- 11516 / 11558 (religion/sect change: from-abroad vs local) — same topic, two real procedures, like the birth/death from-abroad twins.

---

## Next steps
1. Send to Mariam (file / photo / voice note).
2. Swap with Ghina and glance at her KEEP/SKIP calls (neither approves their own work). The combined 53 is also the point to check for genuinely missing procedures like marriage registration.

*Rule I applied consistently: **same procedure captured twice → duplicate → remove one; same topic but two real procedures (local vs from-abroad) → keep both.***
