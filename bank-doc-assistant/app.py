"""Flask backend for Bank Marketing Data Documentation Assistant (PS 179)."""
import io, os, json, uuid, zipfile, xml.etree.ElementTree as ET
from datetime import timedelta
from functools import wraps
from pathlib import Path
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename

from profiler import profile
from doc_parser import parse_docs
from matcher import match
from llm import describe_field, narrate, reset_api_call_count, get_api_call_count, answer_dataset_query
from limitations import find_limitations
from validator import validate
from pii import detect_pii
from governance import governance_scores, confidence_score
from audit import log_event
from visualizer import compute_visualizations
from auth import init_db, create_user, authenticate_user, get_user_by_id, get_or_create_secret_key

app = Flask(__name__)
app.secret_key = get_or_create_secret_key()
app.permanent_session_lifetime = timedelta(days=14)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

init_db()
_last_results = {}
UPLOAD_DOC_DIR = Path(__file__).parent / "uploaded_docs"
LAST_DOC_META_PATH = Path(__file__).parent / ".last_document.json"


def _extract_docx_text(raw_bytes: bytes) -> str:
    """Extract plain text lines from a .docx archive without modifying the original bytes."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            xml_bytes = zf.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        lines = []
        for para in root.findall(".//w:p", ns):
            texts = [t.text for t in para.findall(".//w:t", ns) if t.text]
            if texts:
                lines.append("".join(texts))
        return "\n".join(lines)
    except Exception:
        return ""


def _save_original_document(doc_file) -> dict:
    """Persist the exact unmodified uploaded document and clean up the previous one."""
    _clear_stored_document()
    UPLOAD_DOC_DIR.mkdir(parents=True, exist_ok=True)
    orig_name = Path(doc_file.filename).name or "document"
    safe_name = secure_filename(orig_name) or "document"
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    stored_path = UPLOAD_DOC_DIR / stored_name

    raw_bytes = doc_file.read()
    stored_path.write_bytes(raw_bytes)
    ext = Path(orig_name).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
        ".markdown": "text/plain; charset=utf-8",
    }
    meta = {
        "has_document": True,
        "filename": orig_name,
        "ext": ext,
        "size_bytes": len(raw_bytes),
        "mime": mime_map.get(ext, doc_file.mimetype or "application/octet-stream"),
        "stored_path": str(stored_path),
    }
    try:
        LAST_DOC_META_PATH.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return meta


def _clear_stored_document() -> None:
    """Remove any previously stored uploaded document metadata and file."""
    prev = _get_stored_document_meta()
    if prev and prev.get("stored_path"):
        try:
            p = Path(prev["stored_path"])
            if p.exists():
                p.unlink()
        except Exception:
            pass
    if LAST_DOC_META_PATH.exists():
        try:
            LAST_DOC_META_PATH.unlink()
        except Exception:
            pass


def _get_stored_document_meta() -> dict:
    """Retrieve stored document metadata if the original file still exists on disk."""
    meta = _last_results.get("document")
    if not meta and LAST_DOC_META_PATH.exists():
        try:
            meta = json.loads(LAST_DOC_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            meta = None
    if meta and meta.get("stored_path") and Path(meta["stored_path"]).exists():
        return meta
    return {}


@app.context_processor
def inject_user():
    return {"current_user": get_user_by_id(session.get("user_id"))}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_user_by_id(session.get("user_id"))
        if not user:
            session.pop("user_id", None)
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for("login_page"))
        return fn(*args, **kwargs)
    return wrapper


def _auth_ok():
    tok = os.getenv("API_TOKEN")
    if tok and request.headers.get("X-API-Token") != tok:
        return False
    return True


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if get_user_by_id(session.get("user_id")):
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember")) and str(data.get("remember")).lower() not in ("false", "0", "off")

    user = authenticate_user(email, password)
    if not user:
        if request.is_json:
            return jsonify({"error": "Invalid email address or password."}), 401
        return render_template("login.html"), 401

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = remember
    log_event("login", {"user_id": user["id"], "email": user["email"]})

    if request.is_json:
        return jsonify({"ok": True, "redirect": url_for("dashboard"), "user": user})
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "GET":
        if get_user_by_id(session.get("user_id")):
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if password != confirm_password:
        if request.is_json:
            return jsonify({"error": "Passwords do not match."}), 400
        return render_template("register.html"), 400

    ok, msg, user = create_user(full_name, email, password)
    if not ok:
        status_code = 409 if "already exists" in msg else 400
        if request.is_json:
            return jsonify({"error": msg}), status_code
        return render_template("register.html"), status_code

    log_event("register", {"user_id": user["id"], "email": user["email"]})
    if request.is_json:
        return jsonify({"ok": True, "message": msg, "redirect": url_for("login_page", registered=1)})
    return redirect(url_for("login_page", registered=1))


@app.route("/logout", methods=["GET", "POST"])
def logout():
    uid = session.get("user_id")
    session.clear()
    if uid:
        log_event("logout", {"user_id": uid})
    if request.is_json:
        return jsonify({"ok": True, "redirect": url_for("login_page", logged_out=1)})
    return redirect(url_for("login_page", logged_out=1))


@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400
    log_event("forgot_password_request", {"email": email})
    return jsonify({
        "ok": True,
        "message": "If an account is registered with that email, recovery instructions have been noted. In this local prototype, contact your administrator or create a new account.",
    })


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/process", methods=["POST"])
@login_required
def api_process():
    global _last_results
    if not _auth_ok():
        return jsonify({"error": "Unauthorized"}), 401
    csv_file = request.files.get("csv_file")
    if not csv_file or not csv_file.filename:
        return jsonify({"error": "Dataset is required"}), 400
    raw_csv_bytes = csv_file.read()
    try:
        if csv_file.filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(raw_csv_bytes))
        else:
            df = pd.read_csv(io.BytesIO(raw_csv_bytes))
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400
    if df.empty or len(df.columns) == 0:
        return jsonify({"error": "Empty dataset"}), 400

    doc_file = request.files.get("doc_file")
    doc_text = ""
    doc_meta = None
    if doc_file and doc_file.filename:
        doc_meta = _save_original_document(doc_file)
        raw_doc_bytes = Path(doc_meta["stored_path"]).read_bytes()
        lower_name = doc_meta["filename"].lower()
        if lower_name.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_doc_bytes))
                doc_text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception:
                doc_text = ""
        elif lower_name.endswith(".docx"):
            doc_text = _extract_docx_text(raw_doc_bytes)
        else:
            doc_text = raw_doc_bytes.decode("utf-8", errors="ignore")
    else:
        csv_file.stream = io.BytesIO(raw_csv_bytes)
        doc_meta = _save_original_document(csv_file)
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
    visualizations = compute_visualizations(df, stats, documented, undocumented, findings)
    summary = {
        "total_fields": len(df.columns), "total_rows": len(df),
        "documented": len(documented), "undocumented": len(undocumented),
        "issues": len(findings), "api_calls": get_api_call_count(), **gs,
    }
    public_doc_meta = (
        {
            "has_document": True,
            "filename": doc_meta["filename"],
            "ext": doc_meta["ext"],
            "size_bytes": doc_meta["size_bytes"],
            "mime": doc_meta["mime"],
        }
        if doc_meta
        else {"has_document": False}
    )
    _last_results = {"summary": summary, "dictionary": dict_rows, "findings": findings,
                     "limitations_md": limitations_md, "dict_rows": dict_rows,
                     "visualizations": visualizations, "document": doc_meta}
    try:
        ctx_path = Path(__file__).parent / ".last_context.json"
        ctx_path.write_text(json.dumps({"summary": summary, "dictionary": dict_rows,
                                       "findings": findings}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    log_event("process", {"summary": summary})
    return jsonify({"summary": summary, "dictionary": dict_rows, "unparsed_lines": unparsed,
                    "findings": findings, "limitations_md": limitations_md, "violations": violations,
                    "visualizations": visualizations, "document": public_doc_meta})

@app.route("/api/download/dict")
@login_required
def download_dict():
    rows = _last_results.get("dict_rows", [])
    if not rows:
        return "No data generated yet", 404
    csv_buf = io.StringIO()
    pd.DataFrame(rows).to_csv(csv_buf, index=False)
    return send_file(io.BytesIO(csv_buf.getvalue().encode("utf-8")), mimetype="text/csv",
                     as_attachment=True, download_name="data_dictionary.csv")

@app.route("/api/download/report")
@login_required
def download_report():
    md = _last_results.get("limitations_md", "")
    if not md:
        return "No report generated yet", 404
    return send_file(io.BytesIO(md.encode("utf-8")), mimetype="text/markdown",
                     as_attachment=True, download_name="limitations_report.md")

@app.route("/api/download/pdf")
@login_required
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
@login_required
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
@login_required
def api_metrics():
    return jsonify(_last_results.get("summary", {}))


@app.route("/api/visualizations")
@login_required
def api_visualizations():
    viz = _last_results.get("visualizations")
    if not viz:
        return jsonify({"error": "No visualization data available. Please upload and analyze a dataset first."}), 404
    return jsonify(viz)


@app.route("/api/document/meta")
@login_required
def api_document_meta():
    meta = _get_stored_document_meta()
    if not meta:
        return jsonify({"has_document": False})
    return jsonify({
        "has_document": True,
        "filename": meta["filename"],
        "ext": meta["ext"],
        "size_bytes": meta["size_bytes"],
        "mime": meta["mime"],
    })


@app.route("/api/document/upload", methods=["POST"])
@login_required
def api_document_upload():
    up = request.files.get("file") or request.files.get("doc_file")
    if not up or not up.filename:
        return jsonify({"error": "Please select a file to preview."}), 400
    allowed = {".pdf", ".docx", ".txt", ".md", ".markdown", ".csv", ".xlsx", ".xls"}
    ext = Path(up.filename).suffix.lower()
    if ext not in allowed:
        return jsonify({"error": f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, CSV, XLSX, XLS, TXT, MD."}), 400
    doc_meta = _save_original_document(up)
    _last_results["document"] = doc_meta
    return jsonify({
        "has_document": True,
        "filename": doc_meta["filename"],
        "ext": doc_meta["ext"],
        "size_bytes": doc_meta["size_bytes"],
        "mime": doc_meta["mime"],
    })


@app.route("/api/document/file")
@login_required
def api_document_file():
    meta = _get_stored_document_meta()
    if not meta:
        return jsonify({"error": "No document uploaded."}), 404
    return send_file(
        meta["stored_path"],
        mimetype=meta.get("mime", "application/octet-stream"),
        as_attachment=False,
        download_name=meta["filename"],
    )


@app.route("/api/document/download")
@login_required
def api_document_download():
    meta = _get_stored_document_meta()
    if not meta:
        return "No document uploaded.", 404
    return send_file(
        meta["stored_path"],
        mimetype=meta.get("mime", "application/octet-stream"),
        as_attachment=True,
        download_name=meta["filename"],
    )

@app.route("/api/audit-log")
@login_required
def api_audit_log():
    from audit import LOG_PATH
    lines = []
    if LOG_PATH.exists():
        lines = [l for l in LOG_PATH.read_text(encoding="utf-8").splitlines()]
    return jsonify({"entries": lines[-50:]})

if __name__ == "__main__":
    print("Starting Bank Doc Assistant on http://localhost:8501")
    app.run(host="0.0.0.0", port=8501, debug=True)
