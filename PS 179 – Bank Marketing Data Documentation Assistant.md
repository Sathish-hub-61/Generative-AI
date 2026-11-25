# PS 179 – Bank Marketing Data Documentation Assistant

**Planning pack for Review 1** · PRD · TRD · System Flow · UI · 6-Hour Execution Plan · Pitch

> Note: the problem-statement PDF (Venue\_209\_Final.pdf) was not visible to me, so this plan is built from the problem text you pasted. Check it against the PDF for any extra constraints (dataset name, required output format, demo rules).

## 1. Problem Understanding

**What is asked:** Build a GenAI app that reads a bank marketing campaign dataset (field names plus records) and produces (a) a readable **data dictionary** and (b) a **limitations report**.

**The one hard rule:** the prototype must **not infer undocumented field meanings**. If a column (for example `pdays`, `poutcome`, `duration`) has no supplied documentation, the system must say "Not documented" and must not guess from the column name or the values.

**Why this is hard for an LLM:** LLMs naturally guess that `duration` means call length or that `pdays=999` means "never contacted". The core of the project is **controlling that behaviour**, not generating text.

**Who uses it:** a data analyst or auditor handed an unfamiliar campaign file who needs trustworthy documentation fast.

### Requirements

| ID | Requirement | Type |
| --- | --- | --- |
| R1 | Upload a dataset (CSV) | Must |
| R2 | Upload or paste the official field documentation (txt/md/csv/pdf text) | Must |
| R3 | Data dictionary: one row per field with name, observed type, example values, observed stats, and documented meaning | Must |
| R4 | Every documented meaning is traceable to a source line in the supplied documentation | Must |
| R5 | Fields with no documentation are marked "Undocumented – meaning not inferred" | Must |
| R6 | Limitations report: data-quality, coverage and documentation gaps, each backed by a measured fact | Must |
| R7 | Report exportable (Markdown/PDF/CSV) | Must |
| R8 | Faithfulness check that flags LLM output not supported by the documentation | Should |
| R9 | Evaluation panel: counts of documented vs undocumented fields, guardrail pass rate | Should (Review 3) |
| R10 | Chat Q&A over the dictionary | Won't (cut) |

### Problem decomposition

1. **Ingest:** parse CSV and parse documentation into `{field: description}` entries.
2. **Profile (no AI):** pandas computes types, missing values, distinct counts, min/max/mean, top categories, class balance.
3. **Match:** map each CSV column to a documentation entry by exact (case-insensitive) name match. No fuzzy guessing.
4. **Describe (AI, constrained):** the LLM rewrites only the documented text into plain English for documented fields. Undocumented fields never reach the LLM.
5. **Detect limitations (rules first):** deterministic checks produce a findings list with evidence.
6. **Narrate (AI, constrained):** the LLM turns the findings list into a readable report and may not add new findings.
7. **Verify:** a validator checks the AI output against the documentation and findings, then flags or rejects violations.
8. **Export:** dictionary and report are downloadable.

## 2. GenAI Concept Selection and Innovation

**Selected concept:** **Grounded, schema-constrained generation (RAG-lite) with a guardrail layer.** There is no vector database, because the documentation is small enough to pass directly as context. That saves time and avoids retrieval errors.

| Choice | Decision | Reason |
| --- | --- | --- |
| LLM | Claude API (or Gemini free tier if no key) | Strong instruction-following and JSON output |
| Fine-tuning | No | Not needed, and 6 hours is too short |
| Vector DB / embeddings | No | Documentation fits in one prompt |
| Agents | No | Fixed pipeline is easier to demo and defend |
| Prompting | System prompt with an explicit refusal rule plus JSON schema | Enforces "do not infer" |

**Innovation points (what to pitch):**

1. **Hard-gated inference:** undocumented fields are blocked in code, so the LLM never sees them. The "no guessing" rule is enforced by architecture, not only by prompt wording.
2. **Evidence-linked dictionary:** each description shows the exact source documentation line beside the AI paraphrase.
3. **Facts vs meaning separation:** observed statistics (measured) are kept separate from documented meaning (supplied). A value like `pdays = -1` is reported as "appears N times", and its meaning is only stated if the documentation states it.
4. **Faithfulness validator:** flags paraphrases that add facts absent from the source.
5. **Documentation gap report:** the tool reports what is missing from the documentation, which is itself a useful output.

## 3. PRD (Product Requirements Document)

**Product:** Bank Marketing Data Documentation Assistant **Goal:** turn a raw campaign dataset plus its partial documentation into a trustworthy data dictionary and limitations report in under 2 minutes.

### User story

As a data analyst, I upload a campaign CSV and its field documentation. I get a data dictionary where every meaning is traceable to my documentation, undocumented fields are clearly flagged, and I get a limitations report I can hand to my team.

### Scope (6-hour MVP)

**In scope**

- Single-page app with two uploads, a Generate button, and three tabs (Dictionary, Limitations, Guardrail Check).
- Download as Markdown and CSV (PDF optional).
- Works on the bank marketing dataset (for example the UCI Bank Marketing data) and any similar CSV.

**Out of scope (deliberately cut)**

- Login, database, user accounts, deployment pipelines, multi-file projects.
- Chatbot, fine-tuning, vector search, charts beyond one small distribution per field.
- Inferring field meaning from names, values or outside knowledge.

### Functional requirements

| # | Requirement | Acceptance criterion |
| --- | --- | --- |
| F1 | Dataset upload | CSV with up to \~50k rows loads; shows row/column count |
| F2 | Documentation input | Accepts file upload or pasted text; parsed into field entries; unparsed lines are listed |
| F3 | Field matching | Exact name match only; unmatched columns listed as undocumented |
| F4 | Dictionary | Table shows Field, Type, Missing %, Distinct, Example values, Documented meaning, Source line, Status |
| F5 | Status badge | `Documented` or `Undocumented – not inferred` |
| F6 | Limitations report | Each item has a title, a measured evidence line, and a severity |
| F7 | Guardrail tab | Shows validator results per field and per report item |
| F8 | Export | Dictionary CSV and report Markdown download |

### Non-functional requirements

- Generation finishes in under 60 seconds for 17 to 21 columns.
- Deterministic output for the same inputs (temperature 0).
- No invented content: zero undocumented fields may carry a meaning.
- The dataset is not sent to the LLM in full. Only per-field statistics and a few sample values are sent.

### Success metrics (used in Review 3)

| Metric | Target |
| --- | --- |
| Undocumented fields given an invented meaning | 0 |
| Documented fields whose paraphrase passes the faithfulness check | at least 95% |
| Limitations items with evidence attached | 100% |
| End-to-end time | under 60 s |

## 4. TRD (Technical Requirements Document)

### Stack

| Layer | Choice | Why |
| --- | --- | --- |
| UI | Streamlit | Full UI in about 100 lines; fastest for a hackathon |
| Data | pandas | Profiling without extra dependencies |
| LLM | Anthropic SDK (Claude) with JSON output | Reliable structured output |
| Validation | pydantic plus custom checks | Enforces schema and guardrails |
| PDF text (optional) | pypdf | Only if the documentation is a PDF |
| Export | Markdown and CSV from pandas | No extra libraries needed |
| Hosting | Local plus Streamlit Community Cloud (if time permits) | Demo-ready |

### Project structure

```
bank-doc-assistant/
  app.py              # Streamlit UI
  profiler.py         # pandas stats per column
  doc_parser.py       # documentation text -> {field: description}
  matcher.py          # exact name matching, undocumented list
  llm.py              # prompts + Claude calls (2 functions)
  limitations.py      # rule-based findings
  validator.py        # guardrail checks
  data/               # sample CSV + sample documentation
  requirements.txt
  README.md
```

### Module contracts

- `profile(df) -> dict[field, Stats]` where Stats has dtype, missing\_pct, n\_unique, min/max/mean (numeric), top\_values (categorical), samples.
- `parse_docs(text) -> dict[field, DocEntry]` where DocEntry has description and source\_line. Accepted formats: `field: text`, `field - text`, and `field | text`.
- `match(columns, docs) -> (documented, undocumented)` using case-insensitive exact match only.
- `describe_field(field, doc_text, stats) -> {plain_description, uses_only_source: bool}` is called for documented fields only.
- `find_limitations(df, stats, documented, undocumented) -> list[Finding]` where Finding has title, evidence, severity, rule\_id.
- `narrate(findings) -> markdown` where the LLM may only reword the supplied findings.
- `validate(...) -> list[Violation]` runs the guardrail checks.

### Guardrails (the core of the project)

1. **Code gate:** undocumented fields are never sent to the LLM. Their meaning is hard-coded to `Undocumented – meaning not inferred`.
2. **Prompt rule:** "Use only SOURCE\_TEXT. If it is insufficient, return `INSUFFICIENT`. Do not use outside knowledge about banking or this dataset."
3. **Structured output:** JSON schema with a required `source_line_id` field.
4. **Validator:** (a) the paraphrase must not contain numbers or named entities absent from the source text and stats; (b) a keyword-overlap check against the source; (c) optional second LLM call as a judge ("does the paraphrase add any claim not in the source?"). A failure falls back to showing the raw source text.
5. **Narration guard:** the report may only contain findings from the rule engine. The validator checks every number in the report against the findings.

### Rule-based limitations checks (no AI needed)

| Rule | Evidence produced |
| --- | --- |
| Undocumented fields | "N of M columns have no documentation: ..." |
| Missing values | Per-field missing % above a threshold |
| Placeholder-like values | Categories such as `unknown`, or sentinel-looking values, reported **as observed counts**. Their meaning is not stated unless documented |
| Class imbalance | Target column distribution (the target is identified only if documented, or chosen by the user from a dropdown) |
| Constant or near-constant fields | Distinct count of 1 or a dominant value above 95% |
| Outliers | IQR-based count for numeric fields |
| Duplicate rows | Count |
| Doc/data mismatch | Documented fields missing from the CSV, and the reverse |
| Documented caveats | Any warning sentence in the documentation, quoted verbatim |

### Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| LLM guesses meanings | Code gate plus validator plus INSUFFICIENT fallback |
| Documentation format varies | Parser tolerates three separators; shows unparsed lines for manual fix |
| API key or rate limit failure | Cache responses to a JSON file; a "no-AI mode" shows raw documentation text |
| Time overrun | Strict cut list in section 7 |

## 5. System Flow

```
  [CSV upload]            [Documentation upload / paste]
       |                              |
       v                              v
  profiler.py                    doc_parser.py
  (pandas stats)                 ({field: text + source line})
       \                              /
        \                            /
         v                          v
               matcher.py  (exact name match)
                  |                |
        documented fields     undocumented fields
                  |                |
                  v                v
          llm.describe_field   hard-coded:
          (JSON, source-only)  "Undocumented - not inferred"
                  \                /
                   v              v
                 DATA DICTIONARY table
                          |
  limitations.py (rules) -+-> findings list (with evidence)
                          |
                          v
                 llm.narrate (reword findings only)
                          |
                          v
                    validator.py  (guardrail checks)
                          |
               pass ------+------ fail -> fallback to raw source / drop sentence
                          v
          UI tabs: Dictionary | Limitations | Guardrail Check
                          |
                          v
                Download (CSV / Markdown)
```

## 6. UI Design (single Streamlit page)

```
+--------------------------------------------------------------+
| Bank Marketing Data Documentation Assistant                  |
| "Documents only what is documented. Never guesses."          |
+-----------------------------+--------------------------------+
| 1. Upload dataset (CSV)     | 2. Field documentation         |
| [ Browse files ]            | [ Upload .txt/.md ] or paste   |
| bank.csv  45,211 x 17       | [ text box ................... ] |
+-----------------------------+--------------------------------+
| Target column (optional): [ y  v ]   [ Generate Documentation ]|
+--------------------------------------------------------------+
| Summary:  17 fields | 14 documented | 3 undocumented | 5 issues|
+--------------------------------------------------------------+
| [ Dictionary ] [ Limitations ] [ Guardrail Check ]           |
|                                                              |
| Field   | Type | Missing | Examples | Meaning | Source | Status|
| age     | int  | 0%      | 58, 44   | (doc..) | line 3 | Documented |
| pdays   | int  | 0%      | -1, 91   |  --     |  --    | Undocumented|
|         |      |         |          | meaning not inferred          |
+--------------------------------------------------------------+
| [Download dictionary CSV]   [Download report .md]            |
+--------------------------------------------------------------+
```

**UI principles:** green badge for Documented, amber for Undocumented. The source line is always visible beside the AI paraphrase. The Limitations tab lists items by severity, with an "Evidence" expander on each. The Guardrail Check tab shows a pass/fail table and the count of blocked fields.

## 7. 6-Hour Execution Plan

| Time | Task | Output | Done when |
| --- | --- | --- | --- |
| 0:00 – 0:30 | Setup: repo, venv, install streamlit, pandas, anthropic, pydantic. Get the dataset and write `data/sample_docs.txt` from the official documentation. Test the API key | Running skeleton | `streamlit run app.py` shows a page |
| 0:30 – 1:30 | `profiler.py`, `doc_parser.py`, `matcher.py` (no AI) | Dictionary table with stats and Documented/Undocumented status | Table renders for the sample CSV |
| 1:30 – 2:30 | `llm.py` describe\_field with JSON schema, INSUFFICIENT fallback, response cache | Plain-language descriptions for documented fields | Undocumented fields never call the API |
| 2:30 – 3:30 | `limitations.py` rules plus `llm.narrate` | Limitations report with evidence | Every item has an evidence line |
| 3:30 – 4:15 | `validator.py` plus Guardrail tab | Pass/fail table | Injecting a fake claim gets flagged |
| 4:15 – 4:45 | Export buttons, summary bar, UI polish | Downloads work | CSV and Markdown open correctly |
| 4:45 – 5:30 | Test: remove 3 fields from the documentation, check they become Undocumented; test a messy documentation format; record the metrics table | Evaluation numbers | Zero invented meanings |
| 5:30 – 6:00 | README, 2-minute demo script, screenshots, backup demo video | Submission-ready | Demo runs twice in a row |

### Cut list (drop in this order if behind)

1. Second-LLM judge in the validator (keep the rule checks).
2. PDF export (keep Markdown and CSV).
3. Per-field distribution charts.
4. Cloud deployment (run locally).

### Team split (if you have teammates)

- Person A: profiler, parser, matcher, limitations rules.
- Person B: LLM prompts, validator, evaluation.
- Person C: Streamlit UI, README, slides and demo script.

## 8. Review Mapping

| Review | What to submit | What this pack covers |
| --- | --- | --- |
| Review 1 (10 marks) | Slides or PDF: problem, requirements, decomposition, GenAI concept, architecture, plan | Sections 1, 2, 5, 7 |
| Review 2 (15 marks) | Working prototype: parsing, profiling, LLM descriptions, dictionary | Hours 0 to 3.5 of the plan, plus a screenshot deck |
| Review 3 (25 marks) | Final demo, guardrail results, evaluation, risks, impact | Sections 3 (metrics), 4 (guardrails, risks), plus the evaluation table |

## 9. Team Pitch (2 minutes)

1. **Hook:** "Ask an LLM what `pdays` means and it will confidently guess. In a bank, a guess in documentation becomes a wrong decision."
2. **Problem:** campaign datasets arrive with partial documentation, and analysts need a dictionary they can trust.
3. **Solution:** a grounded documentation assistant that writes only what is documented, marks everything else "Undocumented – not inferred", and reports data limitations with evidence.
4. **How it works:** pandas measures facts, the LLM rewrites only supplied documentation, a validator checks every sentence.
5. **Differentiator:** the no-guess rule is enforced in code, not only in the prompt.
6. **Impact:** faster onboarding, safer analysis, and an audit trail from every statement back to its source.
7. **Ask:** show the live demo, including removing a field from the documentation and watching it become Undocumented.

## 10. Slide outline for Review 1 (7 slides)

1. Title and team
2. Problem and the "no inference" rule
3. Requirements and decomposition
4. GenAI concept (grounded, gated generation) and why not fine-tuning or RAG with a vector DB
5. Architecture (system flow diagram)
6. UI mockup
7. 6-hour execution plan and risks
