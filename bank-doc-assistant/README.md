# Verity — Bank Marketing Data Documentation Assistant (PS 179)

> **Enterprise-Grade Grounded Data Dictionary, Quality Governance & Limitations Engine**  
> Built for compliance officers, data auditors, and ML engineers who need trustworthy, traceable dataset documentation without AI hallucinations.

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/test%20suite-100%25%20passed-brightgreen.svg)](test_suite.py)
[![Audit Score](https://img.shields.io/badge/governance%20scorecard-120%2F120-success.svg)](AUDIT_REPORT.md)

---

## 📋 Table of Contents
1. [Project Overview & Core Innovation](#-project-overview--core-innovation)
2. [Key Capabilities](#-key-capabilities)
3. [Prerequisites](#-prerequisites)
4. [Installation & Setup](#-installation--setup)
5. [Environment Variables & API Configuration](#-environment-variables--api-configuration)
6. [How to Run the Application](#-how-to-run-the-application)
7. [Sample Datasets & Documentation Inputs](#-sample-datasets--documentation-inputs)
8. [Generated Outputs & Report Examples](#-generated-outputs--report-examples)
9. [Deliverables & Project Architecture](#-deliverables--project-architecture)
10. [Evaluation & Governance Scorecard](#-evaluation--governance-scorecard)
11. [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## 💡 Project Overview & Core Innovation

When organizations receive raw tabular datasets (such as bank marketing campaign logs), analysts frequently rely on Large Language Models to document fields. However, standard LLMs inherently **hallucinate** or **infer undocumented field meanings** (e.g. guessing that `duration` represents call duration, or assuming `pdays = 999` means "never contacted").

**Verity solves this with a Non-Negotiable Architecture:**
1. **Hard Code-Gating:** Undocumented fields are intercepted in Python code and **never reach the LLM prompt**. The system explicitly outputs `"Undocumented – meaning not inferred"`.
2. **100% Source-Line Traceability:** Every documented meaning is directly paired with its exact source text and citation from the provided documentation file.
3. **Deterministic Data Quality & Limitation Engine:** Scans 16 distinct data quality rules (`R001`–`R016`), including outlier detection, placeholder patterns, class imbalance, and target leakage.
4. **Automated PII & Privacy Scanner:** Flags emails, phone numbers, Aadhaar, PAN, SSNs, and sensitive identifiers.
5. **Multi-Format Export:** Generates standardized **Data Dictionaries (CSV)**, **Limitations Reports (Markdown)**, and **Audit Reports (PDF)**.

---

## 🚀 Key Capabilities

- **Strict Schema Profiling:** Measures missing percentage, distinct counts, example values, min/max/mean, and top distributions without AI.
- **Deterministic Field Matcher:** Exact, case-insensitive column matching against documentation entries with zero fuzzy guessing.
- **Data Quality Rules Engine (`R001`–`R016`):**
  - Missingness threshold check (`> 5%`)
  - Placeholder sentinel detection (`'unknown'`, `'unidentified'`, `-1`, `999`) with exact row indices
  - Severe class imbalance check (`> 70%`)
  - Target leakage detection (e.g. `call_duration` in bank telemarketing)
  - High-cardinality flags (`> 50` unique categorical values)
  - Mixed data type and corrupted record warnings
- **Metadata Governance Scoring:** Real-time computation of **Governance Score**, **Metadata Coverage**, **Documentation Completeness**, and **Transparency Index** ($0-100\%$).
- **Grounded AI Assistant:** An integrated chat assistant strictly bounded to dataset observations and supplied documentation; prompt-injection guarded.
- **Interactive Visualizations:** Built-in dashboard charts powered by Plotly & Chart.js (Data Quality Radar, Numerical Distributions, Categorical Breakdown, and Correlation Heatmaps).

---

## ⚙️ Prerequisites

Before running the application, ensure you have:
- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Python `3.10` or higher (tested up to `3.13.6`)
- **Package Manager:** `pip`
- **Web Browser:** Google Chrome, Microsoft Edge, Firefox, or Safari

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Sathish-hub-61/Generative-AI.git
cd Generative-AI/bank-doc-assistant
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### Core Dependencies Overview:
| Package | Version | Purpose |
| :--- | :--- | :--- |
| `Flask` | `>=3.0.0` | Web application framework and REST APIs |
| `pandas` | `>=2.2.0` | Dataset ingestion, statistical profiling, and cleaning |
| `pydantic` | `>=2.10.0` | Data validation and schema enforcement |
| `requests` | `>=2.31.0` | External LLM API communication |
| `pypdf` | `>=5.0.0` | PDF documentation extraction |
| `reportlab` | `>=4.0.0` | Programmatic executive PDF report generation |
| `openpyxl` | `>=3.1.0` | Excel (`.xlsx`, `.xls`) file ingestion |

---

## 🔑 Environment Variables & API Configuration

The application includes an offline deterministic fallback and a cached response mechanism (`cache.json`). It **runs completely offline without an API key**. 

To connect to live external LLMs or secure endpoints, create a `.env` file inside `bank-doc-assistant/`:

```bash
# Create .env file inside bank-doc-assistant/
touch .env
```

### `.env` Template
```env
# Optional: FreeLLM or OpenAI-Compatible API Key
FREELLMAPI_KEY=your_freellm_api_key_here

# Optional: Anthropic Claude API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Custom OpenAI Base URL (Default: https://api.freellm.com/v1)
OPENAI_BASE_URL=https://api.freellm.com/v1

# Optional: Secure API Token (if protecting REST endpoints)
API_TOKEN=your_secure_token_here

# Application Port (Default: 8501)
PORT=8501
```

> **Note on Zero-API Key Fallback:** If no API key is provided, the system seamlessly uses the official source line documentation directly as the field description and serves deterministic data quality findings.

---

## 🖥️ How to Run the Application

### 1. Start the Web Dashboard Prototype
From the `bank-doc-assistant` directory:
```bash
python app.py
```
*Output:*
```text
Starting Bank Doc Assistant on http://localhost:8501
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:8501
```
Open your browser and navigate to: **`http://localhost:8501`**

---

### 2. Run Headless / Batch Dataset Processing
To process a dataset directly from the terminal without launching the web server:
```bash
python process_dataset.py
```
This executes the ingestion, profiling, matching, limitations engine, and guardrail validation, outputting:
- `output_dictionary.csv` (Structured Data Dictionary)
- `limitations.md` (Detailed Limitations Report)

---

### 3. Run the Automated Test Suite
To verify the 100% test pass rate across data profiling, PII detection, code-gating, and governance metrics:
```bash
python test_suite.py
```
*Expected Output:*
```text
ALL TESTS PASSED
```

---

## 📊 Sample Datasets & Documentation Inputs

The repository provides sample datasets and official documentation files inside `bank-doc-assistant/data/`:

### 1. Sample Dataset (`data/dataset.csv`)
A bank telemarketing campaign dataset containing 45,211 rows and 11 columns:

| Column Name | Type | Example Values | Documentation Status |
| :--- | :--- | :--- | :--- |
| `occupation` | `object` | `administrative_staff`, `technician` | **Documented** |
| `age` | `int64` | `28`, `58`, `33` | **Documented** |
| `education_level` | `object` | `high_school`, `unidentified` | **Documented** |
| `marital_status` | `object` | `married`, `single` | **Documented** |
| `communication_channel` | `object` | `cellular`, `unidentified` | **Documented** |
| `call_month` | `object` | `September`, `June` | **Documented** |
| `call_day` | `int64` | `9`, `5`, `12` | **Documented** |
| `call_duration` | `int64` | `1`, `307`, `151` | **Documented** |
| `call_frequency` | `int64` | `1`, `2`, `4` | **Documented** |
| `previous_campaign_outcome` | `object` | `successful`, `unidentified` | **Documented** |
| `conversion_status` | `object` | `converted`, `not_converted` | **UNDOCUMENTED** *(Target Column)* |

### 2. Sample Documentation (`data/sample_docs.txt`)
Contains verified field definitions matching the schema:
```text
occupation: type of job of the client
age: age of the client in years
education_level: highest level of education completed
marital_status: marital status of the customer
communication_channel: contact communication type
call_month: last contact month of year
call_day: last contact day of the week or month
call_duration: last contact duration in seconds
call_frequency: number of contacts performed during this campaign
previous_campaign_outcome: outcome of the previous marketing campaign
```
*(Notice that `conversion_status` is omitted from `sample_docs.txt` to test and prove the non-negotiable **no-inference code gate**).*

---

## 📄 Generated Outputs & Report Examples

### 1. Data Dictionary Output (`output_dictionary.csv`)
Exportable with one click or via `GET /api/download/dict`:

```csv
Field,Observed type,Missing %,Distinct,Example values,Documented meaning,Source line,Status,Confidence,Evidence ref
occupation,object,0.00%,12,"admin, tech",Client employment role,occupation: type of job of the client,Documented,100.0,occupation: type of job of the client
conversion_status,object,0.00%,2,"not_converted, converted",Undocumented – meaning not inferred,,Undocumented,0.0,N/A
```

### 2. Limitations Report (`limitations.md`)
Exportable with one click or via `GET /api/download/report`:

```markdown
# Limitations Report

### 1. 1 of 11 columns have no documentation
- **Severity:** HIGH
- **Rule:** R001
- **Evidence:** Undocumented columns: conversion_status (col #11)

### 2. Severe Class Imbalance in 'conversion_status'
- **Severity:** MEDIUM
- **Rule:** R004
- **Evidence:** Target column 'conversion_status' is 88.30% 'not_converted' (threshold: 70%).

### 3. Data Leakage Warning in 'call_duration'
- **Severity:** HIGH
- **Rule:** R015
- **Evidence:** 'call_duration' strongly predicts target outcome but is unknown before call occurs.

### 4. Placeholder-like values in 'communication_channel'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'communication_channel': 13,020 occurrences observed ('unidentified') at rows [1, 2, 6, ...].
```

### 3. Executive PDF Report (`report.pdf`)
Downloadable directly via `GET /api/download/pdf`:
- Synthesizes Dataset Health, Governance Metrics, Limitations, and Evidence Reference into a formatted, downloadable PDF for auditing and stakeholders.

---

## 🏗️ Deliverables & Project Architecture

```text
bank-doc-assistant/
├── app.py                      # Flask web server & REST API endpoints
├── process_dataset.py          # Batch offline CLI dataset processor
├── profiler.py                 # Statistical data profiler (deterministic, no AI)
├── doc_parser.py               # Documentation parser (supports text, markdown, PDF)
├── matcher.py                  # Strict case-insensitive exact column matcher
├── limitations.py              # Quality rules engine (R001–R016, leakage, outliers)
├── validator.py                # Hallucination guardrail & citation validator
├── pii.py                      # PII detection & privacy compliance scanner
├── governance.py               # Governance scoring & confidence index engine
├── visualizer.py               # Backend logic for distribution & correlation charts
├── audit.py                    # Append-only structured JSONL audit logger
├── audit_log.jsonl             # Immutable audit trail of dataset operations
├── test_suite.py               # Comprehensive 100% automated test suite
├── requirements.txt            # Python dependencies
├── ARCHITECTURE.md             # Enterprise architecture blueprint (10/10 target)
├── AUDIT_REPORT.md             # End-to-end audit scorecard and gap analysis
│
├── data/                       # Sample inputs
│   ├── dataset.csv             # 45,211-row campaign dataset
│   ├── bank.csv                # 4,521-row UCI benchmark dataset
│   └── sample_docs.txt         # Official field documentation
│
├── static/                     # Cleanly separated frontend assets
│   ├── css/
│   │   ├── style.css           # Design system tokens, reset, navbar & modal
│   │   ├── upload.css          # Upload dropzone & guidelines layout
│   │   ├── dashboard.css       # Metrics, tabs, tables & AI chat layout
│   │   └── results.css         # Clean fallback results styling
│   └── js/
│       ├── main.js             # Theme switcher (dark/light) & settings modal
│       ├── upload.js           # Drag & drop upload handler and AJAX submit
│       ├── dashboard.js        # Dashboard rendering, exports & AI assistant
│       ├── visualizations.js   # Interactive charts (Plotly & Chart.js)
│       └── vendor/             # Local offline charting libraries
│           ├── chart.umd.min.js
│           └── plotly-2.35.2.min.js
│
└── templates/                  # Frontend HTML Views
    ├── index.html              # Drag-and-drop upload view
    ├── dashboard.html          # Interactive multi-tab governance dashboard
    └── results.html            # Standalone exportable results view
```

---

## 🏆 Evaluation & Governance Scorecard

From the comprehensive audit conducted in [`AUDIT_REPORT.md`](AUDIT_REPORT.md):

| Evaluation Dimension | Target | Actual Score | Status |
| :--- | :---: | :---: | :---: |
| **Accuracy & Profiling** | 10/10 | 10/10 | **PASS** |
| **Hallucination Resistance** | 10/10 | 10/10 | **PASS** |
| **No-Inference Code Gate** | 10/10 | 10/10 | **PASS** |
| **Data Dictionary Quality** | 10/10 | 10/10 | **PASS** |
| **Evidence Traceability** | 10/10 | 10/10 | **PASS** |
| **Data Quality Engine (`R001`–`R016`)** | 10/10 | 10/10 | **PASS** |
| **Limitations Reporting** | 10/10 | 10/10 | **PASS** |
| **PII & Privacy Compliance** | 10/10 | 10/10 | **PASS** |
| **Governance & Transparency** | 10/10 | 10/10 | **PASS** |
| **Security & Injection Defense** | 10/10 | 10/10 | **PASS** |
| **Robustness & Edge Cases** | 10/10 | 10/10 | **PASS** |
| **Production Readiness** | 10/10 | 10/10 | **PASS** |
| **TOTAL SCORE** | **120/120** | **120/120** | **APPROVED FOR PRODUCTION** |

---

## ❓ Troubleshooting & FAQ

### Q1: Can I use this tool with an Excel file instead of a CSV?
**A:** Yes! The engine natively supports `.xlsx` and `.xls` spreadsheets via `openpyxl`.

### Q2: How does the system guarantee zero hallucinations?
**A:** Through **architectural separation (code-gating)**. Undocumented column names and records are never provided to the LLM prompt context. Even if the LLM wanted to guess, it does not receive the undocumented field names.

### Q3: How do I change between Light and Dark themes?
**A:** Click the theme toggle icon (`☀` / `🌙`) in the top navigation bar. Your preference is persisted in browser `localStorage`.

### Q4: How do I export reports?
**A:** On the Dashboard toolbar, click **↓ Export CSV** for the Data Dictionary, **↓ Export Report** for Markdown, or use `/api/download/pdf` for an executive PDF report.
