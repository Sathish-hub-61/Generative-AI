"""Rule-based limitations finder. No AI – every finding has evidence."""

from typing import Any, Dict, List
import pandas as pd


PLACEHOLDER_STRINGS = {"unknown", "na", "n/a", "none", "unidentified", "other", "nan"}
PLACEHOLDER_NUMBERS = {-1, 999, 9999, 0}
WARNING_KEYWORDS = {"note", "warning", "caution", "not"}


def find_limitations(
    df: pd.DataFrame,
    stats: dict,
    documented: dict,
    undocumented: list,
    target_column: str = None,
) -> List[Dict[str, Any]]:
    """Apply rule-based checks. Return list of Finding dicts."""
    findings: List[Dict[str, Any]] = []
    total = len(df.columns)

    # R001 – undocumented columns
    if undocumented:
        findings.append({
            "title": f"{len(undocumented)} of {total} columns have no documentation",
            "evidence": f"Undocumented columns: {', '.join(undocumented)}",
            "severity": "high",
            "rule_id": "R001",
        })

    # R002 – missing values above 5 %
    for col, st in stats.items():
        if st.missing_pct > 5:
            findings.append({
                "title": f"High missing rate in '{col}'",
                "evidence": f"{st.missing_pct}% missing values",
                "severity": "medium",
                "rule_id": "R002",
            })

    # R003 – placeholder-like values
    for col in df.columns:
        series = df[col]
        if series.dtype == object:
            count = series.apply(lambda v: str(v).strip().lower() in PLACEHOLDER_STRINGS).sum()
        elif pd.api.types.is_numeric_dtype(series):
            count = series.isin(PLACEHOLDER_NUMBERS).sum()
        else:
            count = 0
        if count > 0:
            findings.append({
                "title": f"Placeholder-like values in '{col}'",
                "evidence": f"{int(count)} occurrences observed",
                "severity": "low",
                "rule_id": "R003",
            })

    # R004 – class imbalance on target column
    if target_column and target_column in df.columns:
        vc = df[target_column].value_counts(normalize=True)
        if not vc.empty and vc.iloc[0] > 0.7:
            findings.append({
                "title": f"Class imbalance in target '{target_column}'",
                "evidence": f"Majority class '{vc.index[0]}' = {vc.iloc[0]:.1%}",
                "severity": "high",
                "rule_id": "R004",
            })

    # R005 – constant or near-constant columns (one value > 95 %)
    for col in df.columns:
        vc = df[col].value_counts(normalize=True)
        if not vc.empty:
            top_pct = vc.iloc[0]
            if top_pct >= 0.95:
                label = "Constant" if stats[col].n_unique == 1 else "Near-constant"
                findings.append({
                    "title": f"{label} column '{col}'",
                    "evidence": f"Top value '{vc.index[0]}' covers {top_pct:.1%} of rows",
                    "severity": "low",
                    "rule_id": "R005",
                })

    # R006 – IQR outlier count for numeric columns
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = s[(s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)]
        if len(outliers) > 0:
            findings.append({
                "title": f"IQR outliers in '{col}'",
                "evidence": f"{len(outliers)} outlier values detected (IQR method)",
                "severity": "medium",
                "rule_id": "R006",
            })

    # R007 – duplicate rows
    dup = int(df.duplicated().sum())
    if dup > 0:
        findings.append({
            "title": "Duplicate rows detected",
            "evidence": f"{dup} exact duplicate rows found",
            "severity": "medium",
            "rule_id": "R007",
        })

    # R008 – documented fields missing from CSV / CSV columns missing from docs
    doc_keys = set(documented.keys())
    csv_keys_lower = {c.lower() for c in df.columns}
    missing_from_csv = {k for k in doc_keys if k.lower() not in csv_keys_lower}
    if missing_from_csv:
        findings.append({
            "title": "Documentation mentions fields not in CSV",
            "evidence": f"Fields: {', '.join(missing_from_csv)}",
            "severity": "low",
            "rule_id": "R008",
        })

    # R009 – warning sentences in documentation
    for field_name, entry in documented.items():
        words = set(entry.description.lower().split())
        matched_kw = WARNING_KEYWORDS & words
        if matched_kw:
            findings.append({
                "title": f"Warning in docs for '{field_name}'",
                "evidence": f'"{entry.description}"',
                "severity": "low",
                "rule_id": "R009",
            })

    return findings
