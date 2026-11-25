import pandas as pd
from collections import Counter


class Stats:
    """Column-level statistics computed purely with pandas (no AI)."""

    def __init__(self, series: pd.Series):
        self.dtype = str(series.dtype)
        self.missing_pct = round(series.isna().mean() * 100, 2)
        self.n_unique = int(series.nunique(dropna=True))

        # Up to 5 non-null distinct sample values
        uniq = series.dropna().unique()
        self.sample_values = [str(v) for v in uniq[:5]]

        # Numeric stats
        if pd.api.types.is_numeric_dtype(series):
            self.min_val = float(series.min()) if not series.dropna().empty else None
            self.max_val = float(series.max()) if not series.dropna().empty else None
            self.mean_val = round(float(series.mean()), 2) if not series.dropna().empty else None
        else:
            self.min_val = None
            self.max_val = None
            self.mean_val = None

        # Top values for categorical columns
        if series.dtype == object:
            vc = series.value_counts(dropna=True).head(5)
            self.top_values = {str(k): int(v) for k, v in vc.items()}
        else:
            self.top_values = {}

    def to_dict(self):
        return {
            "dtype": self.dtype,
            "missing_pct": self.missing_pct,
            "n_unique": self.n_unique,
            "sample_values": self.sample_values,
            "min": self.min_val,
            "max": self.max_val,
            "mean": self.mean_val,
            "top_values": self.top_values,
        }


def profile(df: pd.DataFrame) -> dict:
    """Return a dict mapping column_name -> Stats object."""
    return {col: Stats(df[col]) for col in df.columns}
