from typing import Dict, Any

import pandas as pd


def eda_summary(df: pd.DataFrame) -> Dict[str, Any]:
    numeric = df.select_dtypes(include="number")
    summary = {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "missing_ratio": (df.isna().mean().to_dict()),
        "describe": numeric.describe().to_dict() if not numeric.empty else {},
        "correlation": numeric.corr().to_dict() if numeric.shape[1] >= 2 else {},
    }
    return summary

