"""Guardrail validator – checks LLM descriptions against source text."""

import re
from typing import Any, Dict, List


def validate(dict_rows: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a list of violation dicts with keys: field, check, detail, status."""

    violations: List[Dict[str, Any]] = []

    # Collect all numbers that appear in finding evidence
    evidence_numbers = set()
    for f in findings:
        evidence_numbers.update(re.findall(r"\b\d+(?:\.\d+)?\b", f.get("evidence", "")))

    for row in dict_rows:
        field = row["Field"]
        desc = row.get("Documented meaning", "")
        source = row.get("Source line", "")
        status = row.get("Status", "")

        # Skip undocumented fields – nothing to validate
        if status == "Undocumented":
            violations.append({
                "field": field,
                "check": "Skip",
                "detail": "Undocumented – no LLM output to validate",
                "status": "SKIP",
            })
            continue

        # Check 1: numbers in description that aren't in source or evidence
        desc_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", desc))
        source_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", source))
        allowed_nums = source_nums | evidence_numbers
        bad_nums = desc_nums - allowed_nums
        if bad_nums:
            violations.append({
                "field": field,
                "check": "Unsourced numbers",
                "detail": f"Numbers {bad_nums} not found in source text or evidence",
                "status": "FAIL",
            })

        # Check 2: capitalised names not in source
        desc_caps = set(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", desc))
        source_caps = set(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", source))
        # Exclude common English words
        common = {"The", "This", "Type", "Age", "Level", "Whether", "Number", "Duration",
                   "Contact", "Month", "Day", "Outcome", "Last", "Personal"}
        bad_caps = (desc_caps - source_caps) - common
        if bad_caps:
            violations.append({
                "field": field,
                "check": "Unsourced names",
                "detail": f"Capitalised terms {bad_caps} not in source",
                "status": "FAIL",
            })

        # Check 3: keyword overlap >= 30 %
        desc_words = set(w.lower() for w in re.findall(r"\b\w+\b", desc))
        source_words = set(w.lower() for w in re.findall(r"\b\w+\b", source))
        if desc_words and source_words:
            overlap = len(desc_words & source_words) / len(desc_words)
            if overlap < 0.3:
                violations.append({
                    "field": field,
                    "check": "Low keyword overlap",
                    "detail": f"Only {overlap:.0%} overlap with source text (threshold 30%)",
                    "status": "FAIL",
                })

        # If no violations so far for this field, mark PASS
        field_violations = [v for v in violations if v["field"] == field and v["status"] == "FAIL"]
        if not field_violations:
            violations.append({
                "field": field,
                "check": "All checks",
                "detail": "Description aligns with source text",
                "status": "PASS",
            })

    return violations
