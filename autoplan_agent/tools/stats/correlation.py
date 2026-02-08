from typing import Dict, Any

import pandas as pd


def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> Dict[str, Any]:
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return {}
    return numeric.corr(method=method).to_dict()

