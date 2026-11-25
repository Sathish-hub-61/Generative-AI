"""Flask backend for Bank Marketing Data Documentation Assistant (PS 179)."""
import io, os, json
from pathlib import Path
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file

from profiler import profile
from doc_parser import parse_docs
from matcher import match
from llm import describe_field, narrate, reset_api_call_count, get_api_call_count, answer_dataset_query
from limitations import find_limitations
from validator import validate
from pii import detect_pii
from governance import governance_scores, confidence_score
from audit import log_event

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

_last_results = {}

def _auth_ok():
    tok = os.getenv("API_TOKEN")
    if tok and request.headers.get("X-API-Token") != tok:
        return False
    return True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/process", methods=["POST"])
def api_process():
    global _last_results
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401
    csv_file = request.files.get("csv_file")
    if not csv_file:
        return jsonify({"error": "Dataset is required"}), 400
    try:
        if csv_file.filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(csv_file)
        else:
            df = pd.read_csv(csv_file)
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400
    if df.empty or len(df.columns) == 0:
        return jsonify({"error": "Empty dataset"}), 400

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

    target_column = request.form.get("target_column", "").strip() or None
    reset_api_call_count()
    stats = profile(df)
    docs, unparsed = parse_docs(doc_text)
    documented, undocumented = match(list(df.columns), docs)

    dict_rows = []
    for col in df.columns:
        st = stats[col]
        entry = documented.get(col)
        if entry:
            llm_resp = describe_field(col, entry, st)
            meaning = llm_resp.get("plain_description", entry.description)
            source = entry.source_line
            status = "Documented"
        else:
            meaning = "Undocumented \u2013 meaning not inferred"
            source = ""
            status = "Undocumented"
        placeholders = False
        dict_rows.append({
            "Field": col, "Observed type": st.dtype, "Missing %": f"{st.missing_pct:.2f}%",
            "Distinct": st.n_unique, "Example values": ", ".join(st.sample_values),
            "Documented meaning": meaning, "Source line": source, "Status": status,
            "min": st.min_val, "max": st.max_val, "mean": st.mean_val,
            "top_values": st.top_values,
            "Confidence": confidence_score(status, bool(source), st.missing_pct, placeholders),
            "Evidence ref": source or "N/A",
        })

    findings = find_limitations(df, stats, documented, undocumented, target_column)
    for pf in detect_pii(df):
        findings.append({"title": f"PII detected: {pf['type']} in '{pf['column']}'",
                         "evidence": pf["evidence"], "severity": pf["risk_level"], "rule_id": "PII"})
    limitations_md = narrate(findings)
    violations = validate(dict_rows, findings)
    gs = governance_scores(len(df.columns), len(documented), findings)
    summary = {
        "total_fields": len(df.columns), "total_rows": len(df),
        "documented": len(documented), "undocumented": len(undocumented),
        "issues": len(findings), "api_calls": get_api_call_count(), **gs,
    }
    _last_results = {"summary": summary, "dictionary": dict_rows, "findings": findings,
                     "limitations_md": limitations_md, "dict_rows": dict_rows}
    try:
        ctx_path = Path(__file__).parent / ".last_context.json"
        ctx_path.write_text(json.dumps({"summary": summary, "dictionary": dict_rows,
                                       "findings": findings}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    log_event("process", {"summary": summary})
    return jsonify({"summary": summary, "dictionary": dict_rows, "unparsed_lines": unparsed,
                    "findings": findings, "limitations_md": limitations_md, "violations": violations})

@app.route("/api/download/dict")
def download_dict():
    rows = _last_results.get("dict_rows", [])
    if not rows:
        return "No data generated yet", 404
    csv_buf = io.StringIO()
    pd.DataFrame(rows).to_csv(csv_buf, index=False)
    return send_file(io.BytesIO(csv_buf.getvalue().encode("utf-8")), mimetype="text/csv",
                     as_attachment=True, download_name="data_dictionary.csv")

@app.route("/api/download/report")
def download_report():
    md = _last_results.get("limitations_md", "")
    if not md:
        return "No report generated yet", 404
    return send_file(io.BytesIO(md.encode("utf-8")), mimetype="text/markdown",
                     as_attachment=True, download_name="limitations_report.md")

@app.route("/api/download/pdf")
def download_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "Bank Marketing Documentation Report")
    md = _last_results.get("limitations_md", "")
    y = 730
    for line in md.splitlines():
        c.drawString(100, y, line[:95]); y -= 14
        if y < 50:
            c.showPage(); y = 750
    c.save(); buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="report.pdf")

@app.route("/api/ask", methods=["POST"])
def api_ask():
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    inj = ["ignore previous", "system prompt", "reveal", "bypass"]
    if any(k in question.lower() for k in inj):
        return jsonify({"error": "Blocked"}), 400
    context = data.get("context")
    if not context:
        if _last_results.get("dictionary"):
            context = {"summary": _last_results.get("summary", {}),
                       "dictionary": _last_results.get("dictionary", []),
                       "findings": _last_results.get("findings", [])}
        else:
            ctx_path = Path(__file__).parent / ".last_context.json"
            if ctx_path.exists():
                context = json.loads(ctx_path.read_text(encoding="utf-8"))
    if not context:
        return jsonify({"error": "No dataset analyzed yet."}), 400
    res = answer_dataset_query(question, context)
    return jsonify(res)

@app.route("/api/metrics")
def api_metrics():
    return jsonify(_last_results.get("summary", {}))

@app.route("/api/audit-log")
def api_audit_log():
    from audit import LOG_PATH
    lines = []
    if LOG_PATH.exists():
        lines = [l for l in LOG_PATH.read_text(encoding="utf-8").splitlines()]
    return jsonify({"entries": lines[-50:]})

if __name__ == "__main__":
    print("Starting Bank Doc Assistant on http://localhost:8501")
    app.run(host="0.0.0.0", port=8501, debug=True)
