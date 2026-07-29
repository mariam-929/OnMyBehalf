# End-to-end walkthrough: «شو بدي لأجدد جواز سفري؟»

One page for the live demo. Every figure below is taken from real runs on 2026-07-29, not a
mock-up. Elapsed 4.8-6.5 s warm across runs. Final confidence 0.05.

---

## 1. The path the question takes

```
detect_language  ->  validate_input  ->  classify_intent  ->  retrieve
      ->  external_lookup  ->  research  ->  plan_research  ->  research
      ->  compose  ->  validate_schema  ->  respond
```

| # | node | what happens | model? |
|---|---|---|---|
| 1 | `detect_language` | counts script characters: 18 Arabic, 0 Latin -> `ar` | no |
| 2 | `validate_input` | regex guardrail for bribery, injection, legal advice, PII, other jurisdictions | no |
| 3 | `classify_intent` | classifies the message: `service_query` | **yes** |
| 4 | `retrieve` | RRF-fused BM25 + dense search over the Dawlati corpus | no |
| 5 | `external_lookup` | curated fallback when Dawlati has no such service | no |
| 6 | `research` | resolves each document; runs the live calls | no |
| 7 | `plan_research` | decides which unresolved documents deserve one retry | **yes** |
| 8 | `research` (2nd) | executes the retry plan, and may veto its own model's suggestion | no |
| 9 | `compose` | writes the summary sentence; assembles every fact from the record | **yes** |
| 10 | `validate_schema` | re-validates the envelope before it leaves the graph | no |

**Three model calls. None of them produces a fact.**

---

## 2. The step worth pausing on: Dawlati answers, and is wrong

`retrieve` reports `outcome: found`, `top_cos: 0.598`, above the `theta_abs` 0.45 threshold.

What it found is **«إصدار جواز سفر للخيل»**, a horse passport. It is the only «جواز سفر» record in
the entire 193-record corpus, because passports for people are not published on Dawlati at all.

An embedding cannot represent *"this does not exist"*. It can only return the nearest thing that
does. This is why the fallback is not wired to "retrieval found nothing": retrieval **succeeds
wrongly** here, and a fallback that only fires on failure would never run.

---

## 3. Where the system prompts are built

Prompts are files in `prompts/`, loaded once when the graph is compiled, then passed to the node
that owns them. They are never concatenated into the user's question: each is sent as the **system
message**, with the citizen's text as the user message, and the reply is validated against a
Pydantic model before anything downstream sees it.

| built at | file | used by | role |
|---|---|---|---|
| `agents/graph.py:103` | `prompts/intent_classifier_v1.md` | `classify_intent` | routes the message. Declares *"Tools available: none"* |
| `agents/graph.py:111` | `prompts/research_agent_v2.md` | `plan_research` | **the agent prompt**: role, situation, tool list, negative constraints, output schema, 3 few-shot examples |
| `agents/graph.py:117` | `prompts/composer_v1.md` | `compose` | may emit only `reasoning` and `summary` |

**Show `research_agent_v2.md` on screen.** Its negative constraints are measurements, not guesses:

> *"Do NOT propose a GENERIC administrative phrase as an alias. Measured: «طلب مقدم» matched the
> Directorate of ANTIQUITIES at 0.79 confidence."*

and it tells the model its output will be checked and can be thrown away:

> *"a passport copy that resolves to the Directorate of Animal Wealth is discarded."*

---

## 4. The tool calls

Six calls in this run, two of them to the outside world.

| tool | kind | what it does here | result |
|---|---|---|---|
| `external_source_lookup` | **external HTTP** | fetches the procedure from the authority that issues passports | `live: 4 documents from general-security.gov.lb` |
| `resolve_document` x4 | local | answers *where do I obtain this paper* for each requirement | 3 resolved, 1 abstained |
| `live_service_lookup` | **external HTTP** | asks Dawlati's REST API whether this service exists | **`exists=False`** |

`check_freshness` is deliberately **not** called. It compares a stored `modified_gmt` against the
live Dawlati page, and this record has no Dawlati post id, so asking would attach one site's
freshness to another site's facts.

`live_service_lookup` returning `exists=False` is the confirmation: Dawlati itself says it has no
such service. The fallback is a checked conclusion, not a guess.

---

## 5. What the citizen gets

| # | paper | where to obtain it |
|---|---|---|
| 1 | طلب جواز سفر لبناني (نموذج A4) | مختار محل الإقامة |
| 2 | هوية و/أو إخراج قيد | دائرة الأحوال الشخصية (النفوس) أو المختار |
| 3 | صورة شمسية | *not stated by the source* |
| 4 | جواز السفر السابق | بحوزتك |

Plus **10 conditions** the source attaches (parental consent for a minor, the three-month validity
of a travel permit). Those are requirements to satisfy, not papers to collect, so they are listed
separately: asking where to obtain a rule has no answer.

**Paper 2 is the cross-source moment.** The passport comes from General Security; the ID it
requires is a Dawlati service. That is the product in one line: not what to bring, but where each
thing comes from.

**Paper 3 has no source on purpose.** Two official General Security pages contradict each other,
one saying the photograph is taken at the centre and two saying to bring one. We do not pick a
side on a citizen's behalf.

---

## 6. Why confidence is 0.05

Assembled by code, and shown in the trace as its own deductions:

```
base = non_core           0.50
freshness = unverified   -0.20     no modification timestamp exists to compare against
unresolved_document      -0.10     the photograph
conditional_structure    -0.40     requirements branch by applicant
                        -------
                          0.05     (floor)
```

The number was not tuned to look good in a demo. A source we cannot re-check, on a service outside
the curated core, with branching requirements, **should** score low.

---

## 7. If asked

**"Isn't this just keyword-matching passport to passport?"**
Type `كيف بطلع جواز سفر للخيل؟`. It returns Dawlati's horse passport, correctly. An explicit animal
term vetoes the external source.

**"Does an LLM choose which website to search?"**
No, and deliberately. The query-to-source mapping is a three-entry table a human opened and read.
A model that picks URLs can invent one, and this is the single decision where a fabrication puts a
citizen physically in front of the wrong ministry. The agent reasons within a source; code decides
which sources exist.

**"Why does `plan_research` say `mode: fallback`?"**
The free-tier model is rate-limited. Every model call in this system has a deterministic fallback,
which is why the answer is still complete: the planner simply retried nothing.
