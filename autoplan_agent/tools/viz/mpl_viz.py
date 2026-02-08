"""Matplotlib 可视化工具模块。

该模块提供基于 Matplotlib 的基础图表绘制和保存功能。
"""

from pathlib import Path
from typing import Dict, Any

import matplotlib.pyplot as plt
import pandas as pd


def plot_chart(df: pd.DataFrame, spec: Dict[str, Any], run_dir: Path) -> Path:
    """使用 Matplotlib 绘制图表并保存为图片。

    Args:
        df: 包含绘图数据的数据框。
        spec: 图表配置，包含 type, x, y, title 等。
        run_dir: 运行任务目录。

    Returns:
        Path: 生成的图表图片文件路径。
    """
    chart_type = spec.get("type", "line")
    x = spec.get("x")
    y = spec.get("y")
    title = spec.get("title", "Chart")

    plt.figure()
    if chart_type == "bar":
        plt.bar(df[x], df[y])
    elif chart_type == "scatter":
        plt.scatter(df[x], df[y])
    else:
        plt.plot(df[x], df[y])
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)

    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    
    # Sanitize title for filename
    safe_title = title.replace(" ", "_")
    for char in "/\\?%*:|\"<>":
        safe_title = safe_title.replace(char, "_")
        
    path = artifacts / f"mpl_{safe_title}.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

