"""异常检测工具模块。

该模块提供基于 IQR 和孤立森林 (Isolation Forest) 的异常检测算法。
"""

from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def iqr_anomaly(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """使用 IQR (四分位距) 方法检测单列异常值。

    Args:
        df: 待处理的数据框。
        column: 目标列名。

    Returns:
        Dict[str, Any]: 包含上下界和异常值数量的字典。
    """
    series = df[column].dropna()
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    return {"lower": float(lower), "upper": float(upper), "anomaly_count": int(mask.sum())}


def isolation_forest(df: pd.DataFrame, columns: list[str]) -> Dict[str, Any]:
    """使用孤立森林算法进行多维异常检测。

    Args:
        df: 待处理的数据框。
        columns: 参与分析的列名列表。

    Returns:
        Dict[str, Any]: 包含异常值数量和样本大小的字典。
    """
    data = df[columns].dropna()
    if data.empty:
        return {"anomaly_count": 0}
    model = IsolationForest(random_state=42, contamination="auto")
    preds = model.fit_predict(data.values)
    anomaly_count = int((preds == -1).sum())
    return {"anomaly_count": anomaly_count, "sample_size": int(data.shape[0])}

