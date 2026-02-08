from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def iqr_anomaly(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    series = df[column].dropna()
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    return {"lower": float(lower), "upper": float(upper), "anomaly_count": int(mask.sum())}


def isolation_forest(df: pd.DataFrame, columns: list[str]) -> Dict[str, Any]:
    data = df[columns].dropna()
    if data.empty:
        return {"anomaly_count": 0}
    model = IsolationForest(random_state=42, contamination="auto")
    preds = model.fit_predict(data.values)
    anomaly_count = int((preds == -1).sum())
    return {"anomaly_count": anomaly_count, "sample_size": int(data.shape[0])}

