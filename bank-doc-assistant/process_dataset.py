import os
import pandas as pd
from pathlib import Path

# ---------- Adjusted paths ----------
# workspace is the folder where this script lives
workspace = Path(__file__).parent / "data"

# Prefer dataset.csv; fall back to bank.csv if needed
csv_path = workspace / "dataset.csv"
if not csv_path.exists():
    csv_path = workspace / "bank.csv"

# Path to the sample documentation (still under data/)
doc_path = Path(__file__).parent / "data" / "sample_docs.txt"

# ---------- Load data ----------
df = pd.read_csv(csv_path)

# ---------- Load documentation ----------
with open(doc_path, "r", encoding="utf-8") as f:
    doc_text = f.read()

# ---------- Import project modules ----------
import sys
sys.path.append(str(Path(__file__).parent))
from profiler import profile
from doc_parser import parse_docs
from matcher import match
from llm import describe_field, narrate
from limitations import find_limitations
from validator import validate

# ---------- Process ----------
stats = profile(df)
docs, unparsed = parse_docs(doc_text)
documented, undocumented = match(list(df.columns), docs)

# Build dictionary rows
dict_rows = []
for col in df.columns:
    stat = stats[col]
    doc_entry = documented.get(col)
    if doc_entry:
        llm_resp = describe_field(col, doc_entry, stat)
        description = llm_resp.get("plain_description", doc_entry.description)
        source_line = doc_entry.source_line
        status = "Documented"
    else:
        description = "Undocumented – meaning not inferred"
        source_line = ""
        status = "Undocumented"
    dict_rows.append({
        "Field": col,
        "Observed type": stat.dtype,
        "Missing %": f"{stat.missing_pct:.2f}%",
        "Distinct": stat.n_unique,
        "Example values": ", ".join(map(str, stat.sample_values)),
        "Documented meaning": description,
        "Source line": source_line,
        "Status": status,
    })

# Limitations & validation
findings = find_limitations(df, stats, documented, undocumented, target_column=None)
limitations_md = narrate(findings)
violations = validate(dict_rows, findings)

# ---------- Write outputs ----------
out_dir = Path(__file__).parent

# Dictionary CSV
import csv
csv_path_out = out_dir / "output_dictionary.csv"
with open(csv_path_out, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=dict_rows[0].keys())
    writer.writeheader()
    writer.writerows(dict_rows)

# Limitations markdown
(out_dir / "limitations.md").write_text(limitations_md, encoding="utf-8")

# ---------- Summary ----------
print("Processing complete")
print(f"Total fields: {len(df.columns)}")
print(f"Documented: {len(documented)}; Undocumented: {len(undocumented)}")
print(f"Findings: {len(findings)}; Violations: {len(violations)}")
