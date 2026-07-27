# G2 worksheet — **Maria** (Part 1 + Part 2 Completed)

**Owner:** Maria · **Reviewer:** Ghina
**Method:** every service opened live on Dawlati (VPN off), compared line-by-line against our extracted list.
**Marks used:** `OK` · `WRONG` · `NOT A DOCUMENT` · `SPLIT`

---

# PART 1 — my 4 services

## 1.1  بطاقة هوية  — #11464 · FIELD-BY-FIELD · Ministry: وزارة الداخلية والبلديات

### Documents we extracted

1. صورة شمسية عدد 1(حديثه) ذات خلفية فاتحة مصدقتان من مختار محلة القيد…
   - `OK`

2. بيان قيد افرادي مخصص لبطاقة الهويه… 3. تقرير طبي او فحص مخبري يثبت فئة الدم…
   - `SPLIT` — two documents glued into one line; the blood-type report is separate (written under MISSING).

3. في حال تقديم الطلب في مركز محطة البصم…
   - `NOT A DOCUMENT` — instruction / describes a situation.

4. يترك الأمر لولي أمر من لم يتجاوز 15من عمره…
   - `NOT A DOCUMENT` — instruction.

5. لمن عمره أقل من 15 عاماً عليه الحضور مع ولي أمره للتوقيع…
   - `NOT A DOCUMENT` — instruction.

6. بطاقة الهويه الأصليه اذا تعلق الطلب ب
   - `OK` but truncated mid-sentence — real document (original ID card), line cut off. **Should merge with #7.**

7. تجديد بطاقة هويه
   - `NOT A DOCUMENT` — tail of #6's sentence ("the original ID card, if the request concerns renewing an ID"). #6 and #7 are one item, wrongly split.

8. محضر فقدان بطاقة الهويه الأصلي مصدق من النيابة العامة…
   - `OK` but **conditional** — only for lost/replacement requests (بدل عن ضائع), tied to the condition of providing a copy of the lost ID.

9. تنجز المعاملة لدى مختار محل القيد…
   - `NOT A DOCUMENT` — location / where the process happens.

**MISSING — site lists these; our list doesn't:**
- تقرير طبي او فحص مخبري يثبت فئة الدم أو صورة طبق الأصل عنه  (split out of #2)
- صورة طبق الأصل عن المحضر
- صورة عن الهوية المفقودة في حال توفرها
- المستندات الأخرى السابق ذكرها

### Other fields
- **Fees:** طوابع مالية بقيمة 5.000 آلاف ليرة لبنانية — `OK`
- **Where to apply:** المديرية العامة للأحوال الشخصية – دائرة بطاقة الهويه — `OK`
- **Authority:** Interior and Municipalities — `OK`

**Overall verdict:** `BAD`

**Anything else:** Of 9 extracted "documents," ~4 are instructions, 1 is a wrongly-split sentence fragment (#7), 1 is a split (#2), and the site lists 3+ real documents that were missed. Many items are conditional (new / renewal / lost-replacement) — the extraction doesn't capture that a document can depend on request type.

---

## 1.2  تسجيل ولادة  — #11554 · FIELD-BY-FIELD · Ministry: وزارة الداخلية والبلديات

### Documents we extracted

1. يتم تنظيم وثيقة الولادة لدى
   - `NOT A DOCUMENT` — start of a sentence; head of #2.

2. مختار المحلة التي حصلت فيها الولادة أو لدى مختار محل القيد بحضور شاهدين
   - `NOT A DOCUMENT` — end of #1's sentence (instruction on where/how); should merge with #1.

3. المستندات المطلوبة
   - `NOT A DOCUMENT` — this is literally the section heading, captured as a document.

4. شهادة الولادة الصادرة عن المستشفى أو الطبيب
   - `OK`

5. بيان قيد عائلي أو إفرادي أو بطاقات الهوية للوالدين
   - `OK`

**MISSING:** None — no required documents beyond #4 and #5.

### Other fields
- **Fees:** 400,000 ل.ل on the document / 400,000 on the newborn's registration statement / 50,000 per certified copy / + registration-location text
   - `OK` on accuracy, **but the field is contaminated** — it mixes base fees, a conditional per-copy fee (50k/copy), and a where/how-to-apply instruction (in-area registration, or transfer by hand / official mail — تحال باليد أو بالبريد الرسمي — to the parents' نفوس office). Per-copy fee and transfer method should be separated out.
- **Where to apply:** المديرية العامة للأحوال الشخصية – دوائر وأقلام النفوس — `OK` (note: the "official mail transfer" method is buried inside the fees field)
- **Authority:** Interior and Municipalities — `OK`

**Overall verdict:** `BAD`

**Anything else:** Only 2 of 5 "documents" are real; the rest are a split sentence (#1+#2) and a captured heading (#3). No documents missing — a different failure type from the ID card: correct data filed in the wrong field.

---

## 1.3  طلب إذن مسبق لاستيراد شتول مثمرة/فريز/موز  — #11704 · SKIM · Ministry: agriculture (مديرية الثروة الزراعية)

### Documents we extracted

1. مرفق ربطاً : – صورة عن الفاتورة او Pro forma Invoice
   - `OK`

**MISSING:** None — only one document under المستندات المطلوبة.

**Overall verdict:** `GOOD` (accuracy — the single required document is captured correctly)

**Anything else:** The service's real requirement isn't just "an invoice." Under ملاحظات the site provides a structured application **form** with mandatory fields (importer name & mobile, company name, commercial-registration number, address, phone, email, seedling type/quantity/country of origin) plus an attached table (الجدول المرفق). Our extraction reduces the whole service to "1 document: invoice." Two specific gaps: (a) a **fiscal stamp (طابع مالي) is required but the site gives NO amount** — unverifiable, the agent should flag rather than guess; (b) the notes also contain the ministry's internal **approval/signature chain** — routing info, not citizen requirements.

---

## 1.4  تسجيل مزارع الدواجن والشروط الفنية والصحية (قيد المراجعة)  — #11674 · SKIM · Ministry: agriculture (مديرية الثروة الحيوانية)

### Documents we extracted

> We extracted ZERO documents for this service.

**MISSING:** `SITE HAS NONE` — the site explicitly states لم يتم إدراج أي مستندات مطلوبة ("no required documents have been listed"). Our zero-document extraction correctly matches the site.

**Overall verdict:** `GOOD`

**Anything else:** The service is marked قيد المراجعة ("under review") and the source lists no documents at all. This is a **gap in the government data, not in our extraction.** The agent should surface this honestly ("the official source lists no required documents for this service; it is under review") rather than imply a complete answer — a case for the human-review/flag path.

---

# PART 2 — review of Ghina's 4 services

*(Each opened on the live site. I'm a second pair of eyes, not redoing her work.)*

## 2.1  إعادة قيد مطلقة — #11532

- Agree with Ghina's verdicts? **AGREE**
- Detail: All five documents confirmed on the live site under المستندات المطلوبة, correctly captured, worded the same, none missing. No phantom/heading/split issues — a genuinely clean, flat-list service. Fees (طوابع أميرية بقيمة 100000 ل.ل) and authority (المديرية العامة للأحوال الشخصية – أقلام النفوس) both match.
- Anything she missed: nothing.

## 2.2  وثيقة ولادة واردة من الخارج — #11528

- Agree with Ghina's verdicts? **AGREE**
- Detail: Her heading calls (I/II/III → NOT A DOCUMENT) and her off-by-one cross-reference note are correct. Adding: the service is really **three conditional document sets** (I = birth of a minor, II = birth of an adult, III = birth outside the legal window), not one flat list — each heading introduces its own case with its own documents. Heading III carries a **condition inside its own title** (the legal period between the parents' marriage and the birth isn't met), and القانون المحلي الذي يعتبر بمقتضاه المولود شرعياً is a **conditional document specific to case III** (and unclearly worded — a citizen wouldn't easily know what to bring). Some items are **either/or** (التعميم 1/84 **أو** قرار قنصلي). The cross-references "items 1,2,3,4 above" only make sense once headings are treated as cases (they point to the four real documents under case I). The **Notes** section is follow-up procedure + a mismatch/error case (embassy issues a reference number; file returned for correction if parent info doesn't match records) — useful process info, but not documents.
- Fees: **لا رسوم (free)** — worth recording.

## 2.3  اكتساب المرأة الأجنبية الجنسية اللبنانية بمفعول الزواج من لبناني — #11476

- Agree with Ghina's verdicts? **AGREE**
- Detail: Her SPLITs on lines 2, 4, 5 are confirmed on the live site, and her MISSING breakdown + by-nationality note are correct. This service is the **strongest example of hidden logic a flat list destroys**, on four levels:
  1. **Branching by applicant type** — general / Syrian wife (بالنسبة للزوجة السورية) / Palestinian wife (بالنسبة للفلسطينية). Same case-based pattern as #11528.
  2. **Either/or within lines** — line 3 (اقامة صالحة **أو** تأشيرة دخول), line 4 (Syrian ID copy **أو** birth statement): one requirement satisfiable two ways, not multiple mandatory documents.
  3. **Eligibility precondition inside a document** — line 1's application requires the marriage registered on the husband's record for **≥ 1 year** (بعد مرور سنة).
  4. **Document recency conditions differing by case** — the Syrian بيان قيد must be **< 6 months** old; the Palestinian بيان قيد must be **< 3 months** old. (Ties directly to our `check_freshness` design — freshness applies to the citizen's documents, not just the source.)
- **Fees missing from Ghina's entry** (important) — the site lists **50,000 ل.ل per certified-copy document** AND a **20,000,000 ل.ل fee collected only if the application is approved** (a large conditional fee). Both should be recorded.
- Notes section = the application **form template** + internal processing chain (which box to tick, registration number, 1932 census reference, court ruling, naturalization decree, both spouses signing, نفوس officer's signature/stamp) — correctly not counted as documents.

## 2.4  محضر اعتراف بولادة غير شرعية — #11518

- Agree with Ghina's verdicts? **AGREE**
- Detail: All five confirmed as genuine documents on the live site, correctly captured, none missing, no phantom/heading/split issues — clean at the document level. Two additions: (1) **line 5 is conditional** — the إفادة is only required *if* the local certificate doesn't already show which parent acknowledged the birth first (إذا لم يتبين ذلك من الشهادة المحلية); should be flagged conditional, not always-required; (2) **fees: لا رسوم (free)** — Ghina's entry left this blank; the site states no fees. Notes = a mismatch/correction procedure, correctly excluded.

---

# For the report — cross-service findings (failure-analysis material)

The strongest material came out of looking across all 8 services. Two big themes:

### A. The extractor's mechanical failure modes (my Part 1)
1. **Phantom documents from split sentences** — one conditional sentence sliced across lines, creating a fake standalone "document" (ID card #6/#7; birth #1/#2).
2. **Captured section headings** — headings like المستندات المطلوبة pulled in as documents (birth #3; the I/II/III case headings in #11528).
3. **Instructions mislabeled as documents** — procedural text counted as required documents (ID card #3, #4, #5, #9).
4. **Missed real documents** — the site lists documents our extraction skipped (ID card: 3+; the SPLIT halves in #11476).
5. **Flattened forms** — a whole application form reduced to "1 document" (seedlings #11704).
6. **Contaminated fields** — fees field blends base fees + conditional per-copy fee + apply-method (birth registration).
7. **Missing / unverifiable source data** — a required fee with no amount (seedlings stamp); a large conditional fee not captured (#11476: 20M-if-approved); a service under review with no documents (poultry). These should be flagged for human review, not guessed.

### B. The deeper structural finding — a flat document list can't represent real services
Across #11528 and #11476 the same pattern repeats: services aren't flat lists, they encode **conditional logic** the extraction destroys. Four distinct constraint types observed:
- **Case/branch by applicant type** (minor vs adult; general vs Syrian vs Palestinian wife) — different documents per case.
- **Either/or within a requirement** (residency **أو** visa; circular 1/84 **أو** consular decision; Syrian ID **أو** birth statement) — one requirement, multiple valid documents.
- **Eligibility preconditions** (marriage registered ≥ 1 year before applying).
- **Document recency windows, differing by case** (Syrian بيان قيد < 6 months; Palestinian < 3 months) — directly relevant to the `check_freshness` tool.

**Pattern for the report:** the extractor does fine on simple, flat services (إعادة قيد مطلقة, seedlings, poultry) and fails on services with long or conditional document sections (ID card, birth abroad, citizenship-by-marriage). Not uniformly bad — it fails in identifiable, describable ways, and the deepest failure isn't extraction noise but a **data-model mismatch**: a flat "list of documents" cannot represent cases, disjunctions, preconditions, or recency. #11476 is the flagship example (all four constraint types in one service).

---

*Both files (mine + Ghina's) go to Mariam → machine file → re-run G2 check → gate closes.*
