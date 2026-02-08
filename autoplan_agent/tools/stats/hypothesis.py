"""假设检验工具模块。

该模块提供常用的统计假设检验功能，包括 T 检验和卡方检验。
"""

from typing import Dict, Any

import pandas as pd
from scipy import stats


def t_test(df: pd.DataFrame, col_a: str, col_b: str) -> Dict[str, Any]:
    """执行两独立样本 T 检验。

    Args:
        df: 待处理的数据框。
        col_a: 样本 A 的列名。
        col_b: 样本 B 的列名。

    Returns:
        Dict[str, Any]: 包含 t 统计量和 p 值的字典。
    """
    a = df[col_a].dropna()
    b = df[col_b].dropna()
    stat, pvalue = stats.ttest_ind(a, b, equal_var=False)
    return {"t_stat": float(stat), "p_value": float(pvalue)}


def chi_square(df: pd.DataFrame, col_a: str, col_b: str) -> Dict[str, Any]:
    """执行卡方独立性检验。

    Args:
        df: 待处理的数据框。
        col_a: 第一个分类变量的列名。
        col_b: 第二个分类变量的列名。

    Returns:
        Dict[str, Any]: 包含卡方统计量、p 值、自由度和期望频数的字典。
    """
    table = pd.crosstab(df[col_a], df[col_b])
    stat, pvalue, dof, expected = stats.chi2_contingency(table)
    return {
        "chi2": float(stat),
        "p_value": float(pvalue),
        "dof": int(dof),
        "expected": expected.tolist(),
    }

