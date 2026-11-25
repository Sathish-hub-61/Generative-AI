import pandas as pd
from pathlib import Path

# Load sample CSV
csv_path = Path(__file__).parent / "data" / "dataset.csv"
if not csv_path.exists():
    csv_path = Path(__file__).parent / "data" / "bank.csv"

df = pd.read_csv(csv_path)

# Load sample docs
doc_path = Path(__file__).parent / "data" / "sample_docs.txt"
with open(doc_path, "r", encoding="utf-8") as f:
    doc_text = f.read()

# Import project modules
import sys
sys.path.append(str(Path(__file__).parent))
from profiler import profile
from doc_parser import parse_docs
from matcher import match

# Process
stats = profile(df)
docs, unparsed = parse_docs(doc_text)
documented, undocumented = match(list(df.columns), docs)

print(f"Total columns: {len(df.columns)}")
print(f"Documented: {len(documented)}")
print(f"Undocumented: {len(undocumented)}")
print("Undocumented columns:", ", ".join(undocumented))
print("Unparsed doc lines:", len(unparsed))
