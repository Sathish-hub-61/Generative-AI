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

    # R010 – PII / sensitive columns (heuristic on column names)
    pii_keywords = {"name", "email", "phone", "ssn", "passport", "address", "dob", "birth", "account", "card"}
    for col in df.columns:
        low = col.lower()
        if any(k in low for k in pii_keywords):
            findings.append({
                "title": f"Potential sensitive/PII column '{col}'",
                "evidence": f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): name suggests personal/sensitive data",
                "severity": "high",
                "rule_id": "R010",
            })

    # R011 – high-cardinality categorical (object with > 50 distinct)
    for col in df.select_dtypes(include="object").columns:
        if df[col].nunique(dropna=True) > 50:
            findings.append({
                "title": f"High-cardinality categorical '{col}'",
                "evidence": f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): {df[col].nunique(dropna=True)} distinct values",
                "severity": "medium",
                "rule_id": "R011",
            })

    # R012 – mixed datatype columns (object column with numeric-looking values)
    for col in df.columns:
        series = df[col]
        if series.dtype == object:
            non_null = series.dropna().astype(str)
            numeric_like = non_null.apply(lambda v: _is_number(v)).sum() if len(non_null) else 0
            if 0 < numeric_like < len(non_null):
                findings.append({
                    "title": f"Mixed datatype column '{col}'",
                    "evidence": f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): {numeric_like} of {len(non_null)} values look numeric",
                    "severity": "medium",
                    "rule_id": "R012",
                })

    # R013 – unnamed columns
    for col in df.columns:
        if str(col).startswith("Unnamed") or str(col).strip() == "":
            findings.append({
                "title": f"Unnamed column '{col}'",
                "evidence": f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): no header name",
                "severity": "medium",
                "rule_id": "R013",
            })

    # R014 – encoded values without legend (numeric with few distinct small ints)
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if s.nunique() <= 10 and (s % 1 == 0).all() and s.max() <= 20:
            findings.append({
                "title": f"Possibly encoded column '{col}' (no legend)",
                "evidence": f"Column '{col}' (col #{df.columns.get_loc(col) + 1}): {sorted(s.unique().tolist())}",
                "severity": "low",
                "rule_id": "R014",
            })

    # R015 – potential leakage (duration-like column vs target)
    if target_column and target_column in df.columns:
        for col in df.columns:
            if col == target_column:
                continue
            low = col.lower()
            if "duration" in low or "outcome" in low:
                findings.append({
                    "title": f"Potential target leakage via '{col}'",
                    "evidence": f"Column '{col}' may encode post-outcome info relative to target '{target_column}'",
                    "severity": "high",
                    "rule_id": "R015",
                })

    # R016 – corrupted rows (rows with all-null or extreme null count)
    null_counts = df.isna().sum(axis=1)
    corrupted = df.index[null_counts >= len(df.columns) // 2]
    if len(corrupted) > 0:
        findings.append({
            "title": "Potentially corrupted rows",
            "evidence": f"{len(corrupted)} rows have >= half columns missing at rows {_format_rows(corrupted)}",
            "severity": "medium",
            "rule_id": "R016",
        })

    return findings


def _is_number(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False
