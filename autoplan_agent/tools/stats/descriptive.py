from typing import Dict, Any

import pandas as pd


def descriptive_stats(df: pd.DataFrame) -> Dict[str, Any]:
    numeric = df.select_dtypes(include="number")
    return numeric.describe().to_dict() if not numeric.empty else {}

