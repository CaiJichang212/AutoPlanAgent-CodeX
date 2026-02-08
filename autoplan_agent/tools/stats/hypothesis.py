from typing import Dict, Any

import pandas as pd
from scipy import stats


def t_test(df: pd.DataFrame, col_a: str, col_b: str) -> Dict[str, Any]:
    a = df[col_a].dropna()
    b = df[col_b].dropna()
    stat, pvalue = stats.ttest_ind(a, b, equal_var=False)
    return {"t_stat": float(stat), "p_value": float(pvalue)}


def chi_square(df: pd.DataFrame, col_a: str, col_b: str) -> Dict[str, Any]:
    table = pd.crosstab(df[col_a], df[col_b])
    stat, pvalue, dof, expected = stats.chi2_contingency(table)
    return {
        "chi2": float(stat),
        "p_value": float(pvalue),
        "dof": int(dof),
        "expected": expected.tolist(),
    }

