"""Flask backend for Bank Marketing Data Documentation Assistant (PS 179).

Serves the Verity-style HTML/CSS/JS frontend and handles:
  POST /api/process  –  CSV + docs -> dictionary, limitations, guardrails
  GET  /api/download/dict  –  last generated dictionary as CSV
  GET  /api/download/report  –  last generated limitations as Markdown
"""

import io
import os
import json
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session

from profiler import profile
from doc_parser import parse_docs
from matcher import match
from llm import describe_field, narrate, reset_api_call_count, get_api_call_count
from limitations import find_limitations
from validator import validate

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory store for last results (simple prototype, no DB)
_last_results = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/process", methods=["POST"])
def api_process():
    global _last_results

    # ---- Read CSV ----
    csv_file = request.files.get("csv_file")
    if not csv_file:
        return jsonify({"error": "CSV dataset is required"}), 400

    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    # ---- Read documentation ----
    doc_file = request.files.get("doc_file")
    doc_text = ""
    if doc_file and doc_file.filename:
        if doc_file.filename.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(doc_file)
                doc_text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception:
                doc_text = ""
        else:
            doc_text = doc_file.read().decode("utf-8", errors="ignore")
    if not doc_text:
        doc_text = request.form.get("doc_text", "")

    if not doc_text.strip():
        return jsonify({"error": "Upload documentation or paste text"}), 400

    target_column = request.form.get("target_column", "").strip() or None

    # ---- Pipeline ----
    reset_api_call_count()

    stats = profile(df)
    docs, unparsed = parse_docs(doc_text)
    documented, undocumented = match(list(df.columns), docs)

    # Build dictionary rows
    dict_rows = []
    for col in df.columns:
        st = stats[col]
        entry = documented.get(col)

        if entry:
            # CODE GATE: only documented fields go to LLM
            llm_resp = describe_field(col, entry, st)
            meaning = llm_resp.get("plain_description", entry.description)
            source = entry.source_line
            status = "Documented"
        else:
            # NON-NEGOTIABLE: undocumented fields never touch the LLM
            meaning = "Undocumented \u2013 meaning not inferred"
            source = ""
            status = "Undocumented"

        dict_rows.append({
            "Field": col,
            "Observed type": st.dtype,
            "Missing %": f"{st.missing_pct:.2f}%",
            "Distinct": st.n_unique,
            "Example values": ", ".join(st.sample_values),
            "Documented meaning": meaning,
            "Source line": source,
            "Status": status,
            "min": st.min_val,
            "max": st.max_val,
            "mean": st.mean_val,
            "top_values": st.top_values,
        })

    # Limitations
    findings = find_limitations(df, stats, documented, undocumented, target_column)
    limitations_md = narrate(findings)

    # Validation / guardrails
    violations = validate(dict_rows, findings)

    # Summary numbers
    summary = {
        "total_fields": len(df.columns),
        "total_rows": len(df),
        "documented": len(documented),
        "undocumented": len(undocumented),
        "issues": len(findings),
        "api_calls": get_api_call_count(),
    }

    # Cache for downloads
    _last_results = {
        "dict_rows": dict_rows,
        "limitations_md": limitations_md,
        "summary": summary,
    }

    return jsonify({
        "summary": summary,
        "dictionary": dict_rows,
        "unparsed_lines": unparsed,
        "findings": findings,
        "limitations_md": limitations_md,
        "violations": violations,
    })


@app.route("/api/download/dict")
def download_dict():
    rows = _last_results.get("dict_rows", [])
    if not rows:
        return "No data generated yet", 404
    csv_buf = io.StringIO()
    pd.DataFrame(rows).to_csv(csv_buf, index=False)
    return send_file(
        io.BytesIO(csv_buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="data_dictionary.csv",
    )


@app.route("/api/download/report")
def download_report():
    md = _last_results.get("limitations_md", "")
    if not md:
        return "No report generated yet", 404
    return send_file(
        io.BytesIO(md.encode("utf-8")),
        mimetype="text/markdown",
        as_attachment=True,
        download_name="limitations_report.md",
    )


if __name__ == "__main__":
    print("Starting Bank Doc Assistant on http://localhost:8501")
    app.run(host="0.0.0.0", port=8501, debug=True)
