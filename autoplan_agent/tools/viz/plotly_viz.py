from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd


def plot_chart(df: pd.DataFrame, spec: Dict[str, Any], run_dir: Path) -> Tuple[Path, Path]:
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
