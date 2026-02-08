from typing import Dict, Any

import numpy as np
import pandas as pd


def linear_trend(df: pd.DataFrame, time_col: str, value_col: str) -> Dict[str, Any]:
    data = df[[time_col, value_col]].dropna()
    if data.empty:
        return {"slope": 0.0, "trend": "flat"}
    x = np.arange(len(data))
    y = data[value_col].astype(float).values
    slope = np.polyfit(x, y, 1)[0]
    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
    return {"slope": float(slope), "trend": trend, "points": int(len(data))}

