from __future__ import annotations

from pathlib import Path
from typing import Tuple, Dict, Any

import pandas as pd


def preview_dataframe(df: pd.DataFrame, max_rows: int = 5) -> Dict[str, Any]:
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

