"""Governance scoring + confidence scoring engine."""
from typing import Dict, List

def confidence_score(status: str, has_source: bool, missing_pct: float, placeholders: bool) -> int:
    base = 100 if (status == "Documented" and has_source) else 0
    if status == "Documented" and not has_source:
        base = 75
    if missing_pct > 20:
        base = max(0, base - 10)
    if placeholders:
        base = max(0, base - 5)
    return base

def governance_scores(total: int, documented: int, findings: List[Dict]) -> Dict:
    coverage = (documented / total * 100) if total else 0
    completeness = coverage  # source-line backed
    undocumented_ratio = (total - documented) / total if total else 0
    governance = 0.4 * coverage + 0.3 * completeness + 0.3 * (100 * (1 - undocumented_ratio))
    sev_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
    risk = min(100, sum(sev_weights.get(f.get("severity", "low"), 1) for f in findings))
    transparency = (total - documented) / total * 100 if total else 0
    # transparency = share explicitly marked unknown (good = high)
    return {
        "metadata_coverage": round(coverage, 2),
        "documentation_completeness": round(completeness, 2),
        "governance_score": round(governance, 2),
        "transparency_score": round(transparency, 2),
        "risk_score": round(risk, 2),
    }