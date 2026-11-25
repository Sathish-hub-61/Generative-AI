"""PII / sensitive data detection engine."""
import re
from typing import List, Dict

PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"\b\d{10,12}\b",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "passport": r"\b[A-Z]\d{7,8}\b",
}

COL_KEYWORDS = {
    "email": ["email", "mail"],
    "phone": ["phone", "mobile", "tel", "contact_no"],
    "address": ["address", "street", "city", "zip", "postal"],
    "customer_id": ["customer_id", "cust_id", "client_id", "user_id"],
    "account": ["account", "acct", "iban"],
}

RISK = {"email": "high", "phone": "high", "pan": "critical", "aadhaar": "critical",
        "ssn": "critical", "passport": "critical", "address": "medium",
        "customer_id": "medium", "account": "critical"}


def detect_pii(df) -> List[Dict]:
    findings = []
    # column-name based
    for col in df.columns:
        low = str(col).lower()
        for kind, kws in COL_KEYWORDS.items():
            if any(k in low for k in kws):
                findings.append({"column": str(col), "type": kind,
                                 "risk_level": RISK.get(kind, "medium"),
                                 "evidence": f"Column name '{col}' suggests {kind}",
                                 "recommended_action": "mask/redact before export"})
    # value-based
    for col in df.columns:
        series = df[col].astype(str)
        for kind, pat in PATTERNS.items():
            sample = series.dropna().head(200)
            hits = sample.str.contains(pat, regex=True, na=False).sum()
            if hits > 0:
                findings.append({"column": str(col), "type": kind,
                                 "risk_level": RISK.get(kind, "high"),
                                 "evidence": f"{int(hits)} value(s) match {kind} pattern",
                                 "recommended_action": "redact/mask"})
    return findings