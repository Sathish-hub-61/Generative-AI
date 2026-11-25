import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from profiler import profile
from doc_parser import parse_docs
from matcher import match
from limitations import find_limitations
from pii import detect_pii
from governance import governance_scores, confidence_score

def test_basic():
    df = pd.read_csv(Path(__file__).parent / "data" / "bank.csv")
    stats = profile(df)
    docs, unparsed = {}, []
    documented, undocumented = match(list(df.columns), docs)
    assert len(undocumented) == len(df.columns)
    findings = find_limitations(df, stats, documented, undocumented, None)
    assert any(f["rule_id"]=="R001" for f in findings)
    pii = detect_pii(df)
    assert isinstance(pii, list)
    gs = governance_scores(len(df.columns), len(documented), findings)
    assert "governance_score" in gs
    assert confidence_score("Undocumented", False, 0, False) == 0
    print("ALL TESTS PASSED")

test_basic()

