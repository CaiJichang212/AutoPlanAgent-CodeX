"""趋势分析工具模块。

该模块提供基于线性回归的简单趋势分析功能。
"""

from typing import Dict, Any

import numpy as np
import pandas as pd


def linear_trend(df: pd.DataFrame, time_col: str, value_col: str) -> Dict[str, Any]:
    """计算时间序列的线性趋势。

    Args:
        df: 待处理的数据框。
        time_col: 时间列名。
        value_col: 数值列名。

    Returns:
        Dict[str, Any]: 包含斜率、趋势方向和数据点数量的字典。
    """
    data = df[[time_col, value_col]].dropna()
    if data.empty:
        return {"slope": 0.0, "trend": "flat"}
    x = np.arange(len(data))
    y = data[value_col].astype(float).values
    slope = np.polyfit(x, y, 1)[0]
    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
    return {"slope": float(slope), "trend": trend, "points": int(len(data))}

