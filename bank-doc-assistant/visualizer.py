"""Pure Pandas/NumPy visualization metrics computation (no AI, no meaning inference)."""

import math
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

_PURE_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
_DATE_SEP_RE = re.compile(r"[-/:T]")


def _safe_float(val: Any, decimals: int = 4) -> Optional[float]:
    """Convert numeric scalar to finite JSON-safe float, or None."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, decimals)


def _format_edge(val: float) -> str:
    """Format a bin edge compactly for histogram labels."""
    if abs(val) >= 1000 or (val != 0 and abs(val) < 0.01):
        return f"{val:.3g}"
    if float(val).is_integer():
        return str(int(val))
    return f"{val:.2f}".rstrip("0").rstrip(".")


def _classify_column_type(series: pd.Series) -> str:
    """Classify a Series into Numerical, Categorical, Date/Time, or Other."""
    if pd.api.types.is_bool_dtype(series):
        return "Other"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "Date/Time"
    if pd.api.types.is_numeric_dtype(series):
        return "Numerical"
    if (
        pd.api.types.is_string_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
        or series.dtype == object
    ):
        non_null = series.dropna().astype(str).str.strip()
        non_null = non_null[non_null != ""]
        if not non_null.empty:
            sample = non_null.head(100)
            has_sep = sample.str.contains(_DATE_SEP_RE, regex=True).mean() >= 0.85
            not_pure_num = (~sample.str.match(_PURE_NUMBER_RE)).mean() >= 0.85
            if has_sep and not_pure_num:
                parsed = pd.to_datetime(sample, format="mixed", errors="coerce")
                if parsed.notna().mean() >= 0.85:
                    return "Date/Time"
        return "Categorical"
    return "Other"


def _compute_numerical_details(series: pd.Series) -> Dict[str, Any]:
    """Compute summary statistics, histogram bins, and box plot metrics for a numeric column."""
    total_len = int(len(series))
    s_num = pd.to_numeric(series, errors="coerce")
    s_clean = s_num.dropna().to_numpy(dtype=float)
    s_clean = s_clean[np.isfinite(s_clean)]
    valid_count = int(len(s_clean))
    missing_count = total_len - valid_count

    if valid_count == 0:
        return {
            "count": 0,
            "missing": missing_count,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "q1": None,
            "q3": None,
            "lowerfence": None,
            "upperfence": None,
            "outliers": [],
            "outlier_count": 0,
            "histogram": {"labels": [], "counts": [], "edges": []},
        }

    q1_val = float(np.percentile(s_clean, 25))
    med_val = float(np.percentile(s_clean, 50))
    q3_val = float(np.percentile(s_clean, 75))
    iqr = q3_val - q1_val
    lo_bound = q1_val - 1.5 * iqr
    hi_bound = q3_val + 1.5 * iqr

    within = s_clean[(s_clean >= lo_bound) & (s_clean <= hi_bound)]
    lower_fence = float(within.min()) if len(within) else float(s_clean.min())
    upper_fence = float(within.max()) if len(within) else float(s_clean.max())

    outliers_arr = s_clean[(s_clean < lo_bound) | (s_clean > hi_bound)]
    outlier_count = int(len(outliers_arr))
    if outlier_count > 150:
        idx = np.linspace(0, outlier_count - 1, 150, dtype=int)
        sampled_outliers = [
            v for v in (_safe_float(x, 4) for x in outliers_arr[idx]) if v is not None
        ]
    else:
        sampled_outliers = [
            v for v in (_safe_float(x, 4) for x in outliers_arr) if v is not None
        ]

    # Histogram via NumPy
    s_min = float(s_clean.min())
    s_max = float(s_clean.max())
    if s_min == s_max:
        hist_labels = [_format_edge(s_min)]
        hist_counts = [valid_count]
        hist_edges = [_safe_float(s_min, 4)]
    else:
        n_unique = int(len(np.unique(s_clean)))
        if n_unique <= 12:
            n_bins = min(12, max(1, n_unique))
        else:
            n_bins = min(20, max(6, int(math.ceil(math.sqrt(valid_count)))))
        counts, edges = np.histogram(s_clean, bins=n_bins)
        hist_counts = [int(c) for c in counts]
        hist_edges = [_safe_float(e, 4) for e in edges]
        hist_labels = [
            f"{_format_edge(float(edges[i]))} – {_format_edge(float(edges[i + 1]))}"
            for i in range(len(counts))
        ]

    std_val = float(np.std(s_clean, ddof=1)) if valid_count > 1 else 0.0

    return {
        "count": valid_count,
        "missing": missing_count,
        "min": _safe_float(s_min, 4),
        "max": _safe_float(s_max, 4),
        "mean": _safe_float(float(np.mean(s_clean)), 4),
        "median": _safe_float(med_val, 4),
        "std": _safe_float(std_val, 4),
        "q1": _safe_float(q1_val, 4),
        "q3": _safe_float(q3_val, 4),
        "lowerfence": _safe_float(lower_fence, 4),
        "upperfence": _safe_float(upper_fence, 4),
        "outliers": sampled_outliers,
        "outlier_count": outlier_count,
        "histogram": {
            "labels": hist_labels,
            "counts": hist_counts,
            "edges": hist_edges,
        },
    }


def _compute_categorical_details(series: pd.Series, top_n: int = 20) -> Dict[str, Any]:
    """Compute category frequencies and unique counts for a categorical column."""
    total_len = int(len(series))
    non_null = series.dropna()
    total_non_null = int(len(non_null))
    missing_count = total_len - total_non_null

    if total_non_null == 0:
        return {
            "total_non_null": 0,
            "missing": missing_count,
            "unique_count": 0,
            "top_category": None,
            "top_count": 0,
            "truncated": False,
            "labels": [],
            "counts": [],
            "percentages": [],
        }

    str_series = non_null.astype(str)
    vc = str_series.value_counts()
    unique_count = int(len(vc))
    truncated = unique_count > top_n
    top_vc = vc.head(top_n)

    labels = [str(k) for k in top_vc.index]
    counts = [int(v) for v in top_vc.values]
    percentages = [round(c / total_non_null * 100, 2) for c in counts]

    return {
        "total_non_null": total_non_null,
        "missing": missing_count,
        "unique_count": unique_count,
        "top_category": labels[0] if labels else None,
        "top_count": counts[0] if counts else 0,
        "truncated": truncated,
        "labels": labels,
        "counts": counts,
        "percentages": percentages,
    }


def compute_visualizations(
    df: pd.DataFrame,
    stats: dict,
    documented: dict,
    undocumented: list,
    findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute all visualization payloads strictly from the uploaded DataFrame and docs match."""
    total_rows = int(len(df))
    total_cols = int(len(df.columns))
    total_cells = total_rows * total_cols

    # 1. Missing Values Analysis (sorted descending by missing count)
    miss_items = []
    total_missing = 0
    for col in df.columns:
        miss_cnt = int(df[col].isna().sum())
        total_missing += miss_cnt
        miss_pct = round((miss_cnt / total_rows * 100), 2) if total_rows > 0 else 0.0
        miss_items.append((str(col), miss_cnt, miss_pct))
    miss_items.sort(key=lambda item: (-item[1], item[0].lower()))

    missing_values = {
        "columns": [x[0] for x in miss_items],
        "counts": [x[1] for x in miss_items],
        "percentages": [x[2] for x in miss_items],
        "total_missing": total_missing,
        "total_cells": total_cells,
        "overall_missing_pct": round((total_missing / total_cells * 100), 2) if total_cells > 0 else 0.0,
    }

    # 2. Documentation Coverage (strictly from matched docs)
    doc_cols = [str(c) for c in df.columns if c in documented]
    undoc_cols = [str(c) for c in undocumented]
    doc_count = len(doc_cols)
    undoc_count = len(undoc_cols)
    coverage_pct = round((doc_count / total_cols * 100), 2) if total_cols > 0 else 0.0

    documentation_coverage = {
        "documented": doc_count,
        "undocumented": undoc_count,
        "total_fields": total_cols,
        "coverage_pct": coverage_pct,
        "documented_fields": doc_cols,
        "undocumented_fields": undoc_cols,
    }

    # 3. Data Type Distribution
    type_buckets: Dict[str, List[str]] = {
        "Numerical": [],
        "Categorical": [],
        "Date/Time": [],
        "Other": [],
    }
    for col in df.columns:
        bucket = _classify_column_type(df[col])
        type_buckets[bucket].append(str(col))

    data_types = {
        "counts": {k: len(v) for k, v in type_buckets.items()},
        "columns_by_type": type_buckets,
    }

    # 4. Data Quality Overview
    duplicate_records = int(df.duplicated().sum()) if total_rows > 0 else 0
    sev_counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = str(f.get("severity", "low")).lower()
        if sev in sev_counts:
            sev_counts[sev] += 1

    data_quality = {
        "total_records": total_rows,
        "total_columns": total_cols,
        "missing_values": total_missing,
        "missing_pct": missing_values["overall_missing_pct"],
        "duplicate_records": duplicate_records,
        "undocumented_fields": undoc_count,
        "total_issues": len(findings),
        "severity_counts": sev_counts,
        "issues": findings,
    }

    # 5. Numerical Data Analysis
    num_cols = type_buckets["Numerical"]
    num_by_col = {col: _compute_numerical_details(df[col]) for col in num_cols}
    numerical_analysis = {
        "columns": num_cols,
        "by_column": num_by_col,
    }

    # 6. Categorical Data Analysis
    cat_cols = type_buckets["Categorical"]
    cat_by_col = {col: _compute_categorical_details(df[col]) for col in cat_cols}
    categorical_analysis = {
        "columns": cat_cols,
        "by_column": cat_by_col,
    }

    # 7. Correlation Heatmap (numerical columns only)
    corr_matrix: List[List[Optional[float]]] = []
    if len(num_cols) >= 2:
        corr_df = df[num_cols].apply(pd.to_numeric, errors="coerce").corr()
        for r_col in num_cols:
            row_vals = [_safe_float(corr_df.loc[r_col, c_col], 3) for c_col in num_cols]
            corr_matrix.append(row_vals)

    correlation = {
        "columns": num_cols,
        "matrix": corr_matrix,
        "note": "Correlation measures linear association between numerical variables only. Correlation does not imply causation.",
    }

    return {
        "missing_values": missing_values,
        "documentation_coverage": documentation_coverage,
        "data_types": data_types,
        "data_quality": data_quality,
        "numerical_analysis": numerical_analysis,
        "categorical_analysis": categorical_analysis,
        "correlation": correlation,
    }
