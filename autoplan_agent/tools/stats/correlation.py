"""相关性分析工具模块。

该模块提供计算 DataFrame 数值列相关性矩阵的功能。
"""

from typing import Dict, Any

import pandas as pd


def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> Dict[str, Any]:
    """计算数值列的相关性矩阵。

    Args:
        df: 待处理的数据框。
        method: 相关性计算方法，支持 'pearson', 'kendall', 'spearman'。

    Returns:
        Dict[str, Any]: 相关性矩阵字典。
    """
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return {}
    return numeric.corr(method=method).to_dict()

