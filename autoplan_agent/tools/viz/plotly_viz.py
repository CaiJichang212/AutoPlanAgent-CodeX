"""Plotly 可视化工具模块。

该模块提供基于 Plotly 的交互式图表绘制和保存功能。
"""

from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd


def plot_chart(df: pd.DataFrame, spec: Dict[str, Any], run_dir: Path) -> Tuple[Path, Path]:
    """使用 Plotly 绘制交互式图表。

    生成 HTML 交互文件和静态图片（如果支持）。

    Args:
        df: 包含绘图数据的数据框。
        spec: 图表配置，包含 type, x, y, title 等。
        run_dir: 运行任务目录。

    Returns:
        Tuple[Path, Path]: 生成的 HTML 文件路径和图片文件路径。

    Raises:
        RuntimeError: 如果未安装 plotly 库。
    """
    try:
        import plotly.express as px
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("plotly is required for plotly_viz") from exc
    chart_type = spec.get("type", "line")
    x = spec.get("x")
    y = spec.get("y")
    title = spec.get("title", "Chart")
    if chart_type == "bar":
        fig = px.bar(df, x=x, y=y, title=title)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, title=title)
    else:
        fig = px.line(df, x=x, y=y, title=title)

    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    
    # Sanitize title for filename
    safe_title = title.replace(" ", "_")
    for char in "/\\?%*:|\"<>":
        safe_title = safe_title.replace(char, "_")
        
    html_path = artifacts / f"plotly_{safe_title}.html"
    png_path = artifacts / f"plotly_{safe_title}.png"
    fig.write_html(str(html_path))
    try:
        fig.write_image(str(png_path))
    except Exception:
        png_path = html_path
    return html_path, png_path
