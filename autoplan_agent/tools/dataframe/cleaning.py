"""数据清洗工具模块。

该模块提供 DataFrame 的数值转换和通用清洗功能。
"""

from typing import Dict, Any

import pandas as pd


def coerce_numeric_columns(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """尝试将列转换为数值类型。

    支持处理包含中文单位（如“万”、“亿”）和逗号、百分号的字符串。

    Args:
        df: 待处理的数据框。
        columns: 目标列名列表，如果为 None 则处理所有列。

    Returns:
        pd.DataFrame: 转换后的数据框。
    """
    df = df.copy()
    targets = columns or df.columns.tolist()
    for col in targets:
        if col not in df.columns:
            continue
        if df[col].dtype == "object":
            try:
                series = df[col]
                text = series.astype(str).str.strip()
                cleaned = text.str.replace(",", "", regex=False)
                multiplier = pd.Series(1.0, index=series.index)
                mask_wanyi = cleaned.str.endswith("万亿")
                multiplier[mask_wanyi] = 1e12
                cleaned = cleaned.str.replace("万亿", "", regex=False)
                cleaned = cleaned.str.replace("亿元", "", regex=False)
                cleaned = cleaned.str.replace("万元", "", regex=False)
                mask_yi = cleaned.str.endswith("亿")
                multiplier[mask_yi] = 1e8
                cleaned = cleaned.str.replace("亿", "", regex=False)
                mask_wan = cleaned.str.endswith("万")
                multiplier[mask_wan] = 1e4
                cleaned = cleaned.str.replace("万", "", regex=False)
                mask_qian = cleaned.str.endswith("千")
                multiplier[mask_qian] = 1e3
                cleaned = cleaned.str.replace("千", "", regex=False)
                mask_bai = cleaned.str.endswith("百")
                multiplier[mask_bai] = 1e2
                cleaned = cleaned.str.replace("百", "", regex=False)
                cleaned = cleaned.str.replace("%", "", regex=False)
                if cleaned.str.contains(r"[A-Za-z]", regex=True, na=False).any():
                    continue
                if cleaned.str.contains(r"[\u4e00-\u9fff]", regex=True, na=False).any():
                    continue
                numeric = pd.to_numeric(cleaned, errors="coerce") * multiplier
                non_null = series.notna()
                numeric_count = numeric.notna().sum()
                # If dataframe is empty, still attempt conversion for requested columns
                if df.empty:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif numeric_count > 0 and numeric_count >= max(1, int(0.6 * non_null.sum())):
                    df[col] = numeric
            except Exception:
                pass
    return df


def clean_dataframe(df: pd.DataFrame, rules: Dict[str, Any] | None = None) -> pd.DataFrame:
    """根据规则清洗 DataFrame。

    Args:
        df: 待清洗的数据框。
        rules: 清洗规则字典，支持 drop_duplicates, fillna, dropna 等。

    Returns:
        pd.DataFrame: 清洗后的数据框。
    """
    rules = rules or {}
    if df.empty:
        return df
    
    df = df.copy()

    # 1. Drop duplicates
    if rules.get("drop_duplicates", True):
        subset = rules.get("duplicate_subset")
        df = df.drop_duplicates(subset=subset)

    # 2. Coerce numeric
    df = coerce_numeric_columns(df)

    # 3. Fill missing values
    fillna = rules.get("fillna")
    if isinstance(fillna, dict):
        df = df.fillna(fillna)
    elif fillna is not None:
        # If it's a single value, fill all
        df = df.fillna(fillna)

    # 4. Drop missing values
    dropna = rules.get("dropna")
    if dropna:
        df = df.dropna()

    return df
