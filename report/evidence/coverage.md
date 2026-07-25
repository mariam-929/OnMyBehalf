# coverage.md - denominator register (A19)

Four denominators, never conflated: **catalog / fetched / extracted_ok / verified-40**.
Populated as each gate closes. VPN must be OFF for any Dawlati request (see PROGRESS Findings).

| Denominator | Count | Gate | Date | Source |
|---|---|---|---|---|
| catalog (posts enumerated from REST) | **249** | G1 | 2026-07-25 | data/catalog.json |
| - ministry_service_ser | 195 | G1 | 2026-07-25 | matches frozen SCOPE 6 |
| - services | 24 | G1 | 2026-07-25 | matches frozen SCOPE 6 |
| - useful-numbers-post | 30 | G1 | 2026-07-25 | matches frozen SCOPE 6 |
| service pages (subset used for answers) | 219 | G1 | 2026-07-25 | SCOPE 6 definition |
| fetched | _pending_ | G2 | - | - |
| extracted_ok | _pending_ | G2 | - | - |
| verified-40 (core) | _pending_ | G3 | - | - |
| authorities with >=1 contact | _pending_ | G1b | - | contacts_coverage.md |

## G1 auto-check result (2026-07-25, owner Ali)

Run: python tools/crawler/enumerate.py -> data/catalog.json

| Criterion (VERIFICATION G1) | Result |
|---|---|
| exactly 3 post types | PASS |
| counts vs 195/24/30 (>5% miss fails) | PASS - 0.0% off on all three |
| no duplicate post_ids | PASS |
| every row carries modified_gmt | PASS |
| every row has a non-empty Arabic title | PASS |
| every row has an https URL | PASS |

ministry_term present on 195/249 rows (only ministry_service_ser carries it) - informational,
not a gate criterion.

**G1 AUTO: PASS.** Human sign-off pending: **Mariam** opens the 5 sampled URLs below
(reviewer reassigned from Gaby 2026-07-25; reviewer != producer still holds).

## Human-check sample (5 random rows, seed 7)

| post_id | type | title_ar | url |
|---|---|---|---|
| 11621 | ministry_service_ser | إصدار شهادات صحية لتصدير الحيوانات أو المشتقات الحيوانية | https://dawlati.gov.lb/ministry_service_ser/%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%b4%d9%87%d8%a7%d8%af%d8%a7%d8%aa-%d8%b5%d8%ad%d9%8a%d8%a9-%d9%84%d8%aa%d8%b5%d8%af%d9%8a%d8%b1-%d8%a7%d9%84%d8%ad%d9%8a%d9%88%d8%a7%d9%86%d8%a7%d8%aa-%d8%a3%d9%88/ |
| 9719 | useful-numbers-post | Ogero | https://dawlati.gov.lb/en/useful-numbers-post/ogero/ |
| 11665 | ministry_service_ser | رخصة رعي في الغابات | https://dawlati.gov.lb/ministry_service_ser/%d8%b1%d8%ae%d8%b5%d8%a9-%d8%b1%d8%b9%d9%8a-%d9%81%d9%8a-%d8%a7%d9%84%d8%ba%d8%a7%d8%a8%d8%a7%d8%aa/ |
| 11602 | ministry_service_ser | إعطاء رخصة صيد الأسماك البحرية (بواسطة مركب) | https://dawlati.gov.lb/ministry_service_ser/%d8%a5%d8%b9%d8%b7%d8%a7%d8%a1-%d8%b1%d8%ae%d8%b5%d8%a9-%d8%b5%d9%8a%d8%af-%d8%a7%d9%84%d8%a3%d8%b3%d9%85%d8%a7%d9%83-%d8%a7%d9%84%d8%a8%d8%ad%d8%b1%d9%8a%d8%a9-%d8%a8%d9%88%d8%a7%d8%b3%d8%b7%d8%a9/ |
| 11466 | ministry_service_ser | تصحيح أو إضافة اسم على لوائح الشطب | https://dawlati.gov.lb/ministry_service_ser/%d8%aa%d8%b5%d8%ad%d9%8a%d8%ad-%d8%a3%d9%88-%d8%a5%d8%b6%d8%a7%d9%81%d8%a9-%d8%a7%d8%b3%d9%85-%d8%b9%d9%84%d9%89-%d9%84%d9%88%d8%a7%d8%a6%d8%ad-%d8%a7%d9%84%d8%b4%d8%b7%d8%a8/ |
