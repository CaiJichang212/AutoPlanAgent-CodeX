from pathlib import Path
from typing import Dict, Any

import matplotlib.pyplot as plt
import pandas as pd


def plot_chart(df: pd.DataFrame, spec: Dict[str, Any], run_dir: Path) -> Path:
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

