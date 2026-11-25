# Bank Marketing Documentation Assistant — Enterprise Architecture (10/10 Target)

## 1. Gap Analysis
Critical: no PII detection/redaction; no audit persistence; no versioning; no edge-case handlers (empty/mixed/corrupt/unnamed); no confidence scoring; no evidence matrix; no metadata governance scores; test suite broken.
Major: placeholder false positives; no null-pattern analysis; no format validation; no leakage beyond duration; no high-cardinality rule originally (added); no corrupted-row detection originally (added).
Minor: sample selection bias; no dashboard metrics API; no access control.

## 2. Target Architecture
Input Layer (CSV/PDF/Text) -> Schema Analyzer (profiler) -> Metadata Matcher (doc_parser+matcher) -> Evidence Validator (validator) -> No-Inference Guardrail (code gate) -> Data Quality Engine (limitations) -> Governance Engine (scores) -> PII Detection Engine -> Risk Assessment Engine -> Documentation Generator (llm) -> Audit Report Generator (narrate) -> PDF Export Engine -> Versioning Layer -> Audit Log Layer.

Workflow: Upload -> Profile -> Parse docs -> Match -> Gate (undocumented never to LLM) -> Quality rules -> PII scan -> Governance scores -> Evidence matrix -> Confidence scores -> Narrate -> Validate -> Export -> Persist audit log + version.

## 3. Data Quality Engine
Rules: missing>5% (R002), placeholders (R003), class imbalance>70% (R004), constant/near-constant>95% (R005), IQR outliers (R006), exact duplicates (R007), doc-vs-csv mismatch (R008), warning sentences (R009), PII (R010), high-cardinality>50 (R011), mixed types (R012), unnamed (R013), encoded-no-legend (R014), leakage (R015), corrupted rows>=50% null (R016). Add: null pattern (all-null columns), format validation (regex for email/phone/date), invalid values (negative ages), near-duplicate fuzzy, empty dataset guard.

## 4. PII Detection
Regex + column-name heuristics for email, phone, mobile, PAN, Aadhaar, SSN, passport, address, customer IDs, account numbers. Output: risk level (low/med/high/critical), evidence (column, sample row), recommended action (mask/redact/block export).

## 5. Metadata Governance Engine
Metadata Coverage = documented/total. Documentation Completeness = fields with source_line/total. Governance = 0.4*coverage + 0.3*completeness + 0.3*(1 - undocumented_ratio). Transparency = fields explicitly marked unknown / undocumented. Risk = weighted sum of finding severities. All 0-100.

## 6. Evidence Matrix
Per field: Field Name, Observed Data (dtype, stats, samples), Matched Documentation (text or NONE), Source Line, Confidence Score, Evidence Reference (rule IDs). Undocumented fields: documentation=NONE, confidence=0.

## 7. Confidence Scoring
100 if documented with source line; 75 if partial/ambiguous doc; 50 if matched by fuzzy only; 0 if undocumented. Decay by missing% and placeholder presence.

## 8. Limitation Detection
Auto-detect missing metadata, unknown fields, missing legends, encoded values, high missingness, leakage, imbalance, sampling risk (small n), audit risk (no source lines). Each with evidence + row refs.

## 9. Hallucination Defense
L1 Metadata Verification (matcher exact match only). L2 Evidence Validation (validator numbers/caps/overlap). L3 Output Validation (JSON schema, no invented numbers). L4 Post-gen Audit (re-run validator on output). L5 Governance Review (human approval gate for low-confidence). Target probability ~0 via code gates + deterministic fallbacks.

## 10. Edge Cases
Empty dataset -> reject with 400. Single row -> skip IQR/outliers. Unnamed -> flag. Unknown abbreviations -> undocumented. Mixed types -> R012. High cardinality -> R011. Corrupted CSV -> parse error handling. Missing headers -> pandas auto names + flag. Encoded no legend -> R014. Unicode -> utf-8 decode errors=ignore + flag. Large datasets -> chunked profiling + sampling.

## 11. Audit Report
Sections: Executive Summary, Dataset Health Score, Governance Score, Risk Assessment, Data Dictionary, Evidence Matrix, Data Quality Findings, Limitations, Recommendations, Compliance Assessment. Export Markdown + PDF.

## 12. Dashboard Metrics
Dataset Health, Metadata Coverage, Governance Compliance, Transparency, Hallucination Risk, Documentation Confidence, Data Quality Score, PII Risk Score. Add API /api/metrics.

## 13. Security & Compliance
Audit logs (append-only JSONL), version control (git tags per run), report history (storage dir), access control (API key + roles), PII redaction (mask in exports), data masking (hash IDs), traceability (source_line + rule_id).

## 14. Production Readiness Checklist
Scalability: async workers, chunked CSV, caching. Reliability: retries, fallbacks, health endpoint. Monitoring: metrics endpoint, error tracking. Logging: structured logs. Testing: 100 cases (below). Compliance: GDPR/CCPA PII handling. Deployment: Docker + gunicorn + env config.

## 15. Test Suite (100 cases)
Accuracy (20): field types, missing%, distinct counts, min/max/mean, sample values, documented meanings, undocumented marking, source lines, no inference, numbers only from source.
Governance (20): coverage score, completeness, transparency, risk score, audit log presence, versioning, PII redaction, access control, evidence refs, confidence scores.
Transparency (10): unknown marking, no guessed meanings, limitations list, ambiguity flags, source citations.
PII (15): email/phone/PAN/Aadhaar/SSN/passport/address/ID/account detection + redaction + risk levels.
Evidence (10): matrix completeness, source line, confidence, rule IDs, row refs.
Hallucination (10): code gate, prompt constraints, validator checks, fallback, no invented numbers.
Edge cases (15): empty, single row, unnamed, mixed, high cardinality, corrupted, missing headers, unicode, large, encoded, all-null column, constant, duplicate, placeholder, null pattern.

## 16. Implementation Plan
Phase 1 (Critical, 2 weeks, +20 score): PII engine, audit logs, versioning, edge-case guards, fix tests.
Phase 2 (Major, 3 weeks, +10): confidence scoring, evidence matrix, governance scores, dashboard metrics API, PDF export.
Phase 3 (Advanced, 4 weeks, +6): async scalability, access control, full 100-test suite, monitoring.

## 17. Final Deliverables
Folders: app/, engines/ (pii, quality, governance, risk), validators/, exporters/, audit/, tests/, dashboard/. DB: SQLite (runs, findings, audit_log, versions). APIs: /api/process, /api/metrics, /api/audit-log, /api/version, /api/export/pdf, /api/health. Validation rules: R001-R016 + edge guards. Audit framework: evidence matrix + confidence + governance scores. Governance framework: no-inference gate + multi-layer defense. Dashboard: 8 metrics. Roadmap: 3 phases above.
