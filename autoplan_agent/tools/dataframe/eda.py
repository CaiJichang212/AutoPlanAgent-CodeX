"""EDA 工具模块。

该模块提供 DataFrame 的探索性数据分析 (EDA) 摘要功能。
"""

from typing import Dict, Any

import pandas as pd


def eda_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """生成数据框的 EDA 摘要。

    包含行数、列数、缺失值比例、数值列的统计描述及相关性矩阵。

    Args:
        df: 待分析的数据框。

    Returns:
        Dict[str, Any]: 包含分析摘要的字典。
    """
    numeric = df.select_dtypes(include="number")
    summary = {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "missing_ratio": (df.isna().mean().to_dict()),
        "describe": numeric.describe().to_dict() if not numeric.empty else {},
        "correlation": numeric.corr().to_dict() if numeric.shape[1] >= 2 else {},
    }
    return summary

