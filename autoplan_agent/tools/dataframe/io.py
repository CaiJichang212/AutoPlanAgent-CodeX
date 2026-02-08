"""数据输入输出工具模块。

该模块提供 DataFrame 的预览和保存功能，支持 CSV 和 Parquet 格式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Dict, Any

import pandas as pd


def preview_dataframe(df: pd.DataFrame, max_rows: int = 5) -> Dict[str, Any]:
    """获取数据框的预览信息。

    Args:
        df: 待预览的数据框。
        max_rows: 最大返回行数。

    Returns:
        Dict[str, Any]: 包含列名、行数据和总行数的字典。
    """
    return {
        "columns": df.columns.tolist(),
        "rows": df.head(max_rows).to_dict(orient="records"),
        "row_count": int(df.shape[0]),
    }


def save_dataframe(
    df: pd.DataFrame,
    run_dir: Path,
    name_prefix: str,
    prefer_parquet: bool = True,
) -> Tuple[Path, str]:
    """保存数据框到运行目录。

    优先尝试保存为 Parquet 格式，如果失败则保存为 CSV。

    Args:
        df: 待保存的数据框。
        run_dir: 运行任务目录。
        name_prefix: 文件名前缀。
        prefer_parquet: 是否优先使用 Parquet 格式。

    Returns:
        Tuple[Path, str]: 包含文件路径和 MIME 类型的元组。
    """
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if prefer_parquet:
        try:
            import pyarrow  # noqa: F401

            path = artifacts_dir / f"{name_prefix}.parquet"
            df.to_parquet(path, index=False)
            return path, "application/parquet"
        except Exception:
            pass

    path = artifacts_dir / f"{name_prefix}.csv"
    df.to_csv(path, index=False)
    return path, "text/csv"

