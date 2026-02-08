"""描述性统计工具模块。

该模块提供计算 DataFrame 数值列统计描述的功能。
"""

from typing import Dict, Any

import pandas as pd


def descriptive_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """计算数值列的描述性统计信息。

    Args:
        df: 待处理的数据框。

    Returns:
        Dict[str, Any]: 包含统计描述（均值、标准差、分位数等）的字典。
    """
    numeric = df.select_dtypes(include="number")
    return numeric.describe().to_dict() if not numeric.empty else {}

