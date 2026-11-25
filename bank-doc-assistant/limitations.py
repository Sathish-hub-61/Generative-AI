"""Rule-based limitations finder. No AI – every finding has evidence with exact locations."""

from typing import Any, Dict, List
import pandas as pd


PLACEHOLDER_STRINGS = {"unknown", "na", "n/a", "none", "unidentified", "other", "nan"}
PLACEHOLDER_NUMBERS = {-1, 999, 9999, 0}
WARNING_KEYWORDS = {"note", "warning", "caution", "not"}


def _format_rows(indices: pd.Index, limit: int = 12) -> str:
    """Format 0-based DataFrame indices as 1-based data row numbers."""
    row_nums = [int(i) + 1 for i in indices[:limit]]
    suffix = f" ... (+{len(indices) - limit} more)" if len(indices) > limit else ""
    return f"[{', '.join(map(str, row_nums))}{suffix}]"


def find_limitations(
    df: pd.DataFrame,
    stats: dict,
    documented: dict,
    undocumented: list,
    target_column: str = None,
) -> List[Dict[str, Any]]:
    """Apply rule-based checks. Return list of Finding dicts with exact locations."""
    findings: List[Dict[str, Any]] = []
    total = len(df.columns)

    # R001 – undocumented columns
    if undocumented:
        col_positions = [f"{c} (col #{df.columns.get_loc(c) + 1})" for c in undocumented]
        findings.append({
            "title": f"{len(undocumented)} of {total} columns have no documentation",
            "evidence": f"Undocumented columns: {', '.join(col_positions)}",
            "severity": "high",
            "rule_id": "R001",
        })

    # R002 – missing values above 5 %
    for col, st in stats.items():
        if st.missing_pct > 5:
            miss_mask = df[col].isna()
            miss_idx = df.index[miss_mask]
            findings.append({
                "title": f"High missing rate in '{col}'",
                "evidence": (
                    f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): "
                    f"{int(miss_mask.sum())} missing values ({st.missing_pct}%) at rows {_format_rows(miss_idx)}"
                ),
                "severity": "medium",
                "rule_id": "R002",
            })

    # R003 – placeholder-like values
    for col in df.columns:
        series = df[col]
        if series.dtype == object:
            mask = series.apply(lambda v: str(v).strip().lower() in PLACEHOLDER_STRINGS)
        elif pd.api.types.is_numeric_dtype(series):
            mask = series.isin(PLACEHOLDER_NUMBERS)
        else:
            mask = pd.Series(False, index=df.index)

        count = int(mask.sum())
        if count > 0:
            matched_vals = series[mask].value_counts().head(5).to_dict()
            val_summary = ", ".join(f"'{k}': {int(v)}" for k, v in matched_vals.items())
            match_idx = df.index[mask]
            findings.append({
                "title": f"Placeholder-like values in '{col}'",
                "evidence": (
                    f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): "
                    f"{count} occurrences observed ({val_summary}) at rows {_format_rows(match_idx)}"
                ),
                "severity": "low",
                "rule_id": "R003",
            })

    # R004 – class imbalance on target column
    if target_column and target_column in df.columns:
        vc_norm = df[target_column].value_counts(normalize=True)
        vc_cnt = df[target_column].value_counts()
        if not vc_norm.empty and vc_norm.iloc[0] > 0.7:
            findings.append({
                "title": f"Class imbalance in target '{target_column}'",
                "evidence": (
                    f"Column '{target_column}' (col #{df.columns.get_loc(target_column) + 1}): "
                    f"majority class '{vc_norm.index[0]}' = {vc_norm.iloc[0]:.1%} "
                    f"({int(vc_cnt.iloc[0])} of {len(df)} rows)"
                ),
                "severity": "high",
                "rule_id": "R004",
            })

    # R005 – constant or near-constant columns (one value > 95 %)
    for col in df.columns:
        vc_norm = df[col].value_counts(normalize=True)
        vc_cnt = df[col].value_counts()
        if not vc_norm.empty:
            top_pct = vc_norm.iloc[0]
            if top_pct >= 0.95:
                label = "Constant" if stats[col].n_unique == 1 else "Near-constant"
                findings.append({
                    "title": f"{label} column '{col}'",
                    "evidence": (
                        f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): "
                        f"top value '{vc_norm.index[0]}' covers {top_pct:.1%} ({int(vc_cnt.iloc[0])} of {len(df)} rows)"
                    ),
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
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = s[(s < lower) | (s > upper)]
        if len(outliers) > 0:
            sample_vals = [str(v) for v in outliers.head(5).tolist()]
            findings.append({
                "title": f"IQR outliers in '{col}'",
                "evidence": (
                    f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): "
                    f"{len(outliers)} outlier values outside [{lower:.2f}, {upper:.2f}] "
                    f"at rows {_format_rows(outliers.index)} (sample values: {', '.join(sample_vals)})"
                ),
                "severity": "medium",
                "rule_id": "R006",
            })

    # R007 – duplicate rows
    dup_mask = df.duplicated()
    dup = int(dup_mask.sum())
    if dup > 0:
        dup_idx = df.index[dup_mask]
        findings.append({
            "title": "Duplicate rows detected",
            "evidence": (
                f"{dup} exact duplicate rows found across all {total} columns "
                f"at rows {_format_rows(dup_idx)}"
            ),
            "severity": "medium",
            "rule_id": "R007",
        })

    # R008 – documented fields missing from CSV
    doc_keys = set(documented.keys())
    csv_keys_lower = {c.lower() for c in df.columns}
    missing_from_csv = {k for k in doc_keys if k.lower() not in csv_keys_lower}
    if missing_from_csv:
        findings.append({
            "title": "Documentation mentions fields not in CSV",
            "evidence": f"Fields missing from CSV: {', '.join(sorted(missing_from_csv))}",
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
                "evidence": f'Column \'{field_name}\' (doc line {entry.source_line}): "{entry.description}"',
                "severity": "low",
                "rule_id": "R009",
            })

    return findings
