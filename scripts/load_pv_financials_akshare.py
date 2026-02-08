"""AKShare 财务数据加载脚本。

该脚本用于通过 AKShare 接口抓取 A 股公司的财务报表数据，并将其导入 MySQL 数据库。
"""

import argparse
import datetime as dt
import os
import sys
import time
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import create_engine, text, inspect

from autoplan_agent.config import Settings


def _import_akshare():
    """导入 akshare 库。

    Returns:
        module: akshare 模块。

    Raises:
        RuntimeError: 如果未安装 akshare。
    """
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependency: akshare. Install with pip install -e .[data]") from exc
    return ak


def _build_engine() -> Tuple[object, Settings]:
    """创建数据库引擎和配置对象。

    Returns:
        Tuple[object, Settings]: 数据库引擎和配置对象。

    Raises:
        RuntimeError: 如果缺少数据库连接信息。
    """
    settings = Settings()
    dsn = settings.mysql_dsn()
    if not dsn:
        raise RuntimeError("MySQL connection info missing. Set MYSQL_URL or MYSQL_HOST/USER/PASSWORD/DB.")
    engine = create_engine(dsn, pool_pre_ping=True)
    return engine, settings


def _daterange(start_year: int, end_year: int, annual_only: bool) -> List[str]:
    """生成报告期日期列表。

    Args:
        start_year: 开始年份。
        end_year: 结束年份。
        annual_only: 是否仅包含年报。

    Returns:
        List[str]: YYYYMMDD 格式的日期字符串列表。
    """
    dates = []
    for y in range(start_year, end_year + 1):
        if annual_only:
            dates.append(f"{y}1231")
        else:
            dates.extend([f"{y}0331", f"{y}0630", f"{y}0930", f"{y}1231"])
    return dates


def _safe_call(ak, func_names: List[str], **kwargs):
    """安全调用 akshare 函数，支持多个候选函数名。

    Args:
        ak: akshare 模块。
        func_names: 候选函数名列表。
        **kwargs: 传递给函数的参数。

    Returns:
        Any: 函数返回结果。

    Raises:
        AttributeError: 如果所有函数都不存在。
        Exception: 最后一个执行失败的函数抛出的异常。
    """
    last_exc = None
    for name in func_names:
        if hasattr(ak, name):
            try:
                return getattr(ak, name)(**kwargs)
            except Exception as exc:
                last_exc = exc
                continue
    if last_exc:
        raise last_exc
    raise AttributeError(f"None of the functions exist: {func_names}")


def _get_code_map(ak) -> pd.DataFrame:
    """获取股票代码和名称的映射表。

    Args:
        ak: akshare 模块。

    Returns:
        pd.DataFrame: 包含代码和名称的 DataFrame。

    Raises:
        RuntimeError: 如果无法获取映射表。
    """
    try:
        df = _safe_call(ak, ["stock_info_a_code_name"])
        df = df.rename(columns={"code": "代码", "name": "名称"})
        return df[["代码", "名称"]]
    except Exception:
        pass

    frames = []
    for func, col_code, col_name, kwargs in [
        ("stock_info_sh_name_code", "代码", "简称", {"indicator": "主板A股"}),
        ("stock_info_sh_name_code", "代码", "简称", {"indicator": "科创板"}),
        ("stock_info_sz_name_code", "A股代码", "A股简称", {}),
        ("stock_info_bj_name_code", "证券代码", "证券简称", {}),
    ]:
        if hasattr(ak, func):
            try:
                df = getattr(ak, func)(**kwargs) if kwargs else getattr(ak, func)()
                if col_code in df.columns and col_name in df.columns:
                    frames.append(df[[col_code, col_name]].rename(columns={col_code: "代码", col_name: "名称"}))
            except Exception:
                continue
    if not frames:
        raise RuntimeError("Failed to fetch stock code/name list from akshare.")
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def _match_codes(code_map: pd.DataFrame, company_names: List[str]) -> Dict[str, str]:
    """根据公司名称匹配股票代码。

    Args:
        code_map: 映射表 DataFrame。
        company_names: 公司名称列表。

    Returns:
        Dict[str, str]: 公司名称到股票代码的映射字典。
    """
    mapping: Dict[str, str] = {}
    code_map["名称"] = code_map["名称"].astype(str)
    code_map["代码"] = code_map["代码"].astype(str)
    for name in company_names:
        exact = code_map[code_map["名称"] == name]
        if len(exact) == 1:
            code = exact.iloc[0]["代码"]
            mapping[name] = code.replace(".SZ", "").replace(".SH", "").replace(".BJ", "")
            continue
        fuzzy = code_map[code_map["名称"].str.contains(name)]
        if len(fuzzy) == 1:
            code = fuzzy.iloc[0]["代码"]
            mapping[name] = code.replace(".SZ", "").replace(".SH", "").replace(".BJ", "")
            continue
        if len(fuzzy) > 1:
            print(f"[WARN] Multiple matches for {name}: {fuzzy['代码'].tolist()} / {fuzzy['名称'].tolist()}")
        else:
            print(f"[WARN] No code match for {name}")
    return mapping


def _filter_targets(df: pd.DataFrame, codes: List[str]) -> pd.DataFrame:
    """过滤出目标公司的财务数据。

    Args:
        df: 原始数据 DataFrame。
        codes: 目标股票代码列表。

    Returns:
        pd.DataFrame: 过滤后的 DataFrame。
    """
    if "股票代码" in df.columns:
        key = "股票代码"
    elif "代码" in df.columns:
        key = "代码"
    else:
        return df.iloc[0:0]
    return df[df[key].astype(str).isin(codes)].copy()


def _ensure_report_date(df: pd.DataFrame, report_date: str) -> pd.DataFrame:
    """为数据增加报告日期列。

    Args:
        df: 数据 DataFrame。
        report_date: 报告日期。

    Returns:
        pd.DataFrame: 包含 report_date 列的 DataFrame。
    """
    df["report_date"] = report_date
    return df


def _upsert_table(engine, table: str, df: pd.DataFrame, report_date: str, codes: List[str]) -> None:
    """更新或插入数据到数据库表中。

    如果表已存在，则先删除相同报告期和相同股票代码的数据，再进行插入。

    Args:
        engine: 数据库引擎。
        table: 数据库表名。
        df: 待插入的数据 DataFrame。
        report_date: 报告日期。
        codes: 股票代码列表。
    """
    if df.empty:
        return
    insp = inspect(engine)
    if insp.has_table(table):
        code_col = "股票代码" if "股票代码" in df.columns else ("代码" if "代码" in df.columns else None)
        if code_col:
            placeholders = ",".join([f":c{i}" for i in range(len(codes))]) or "''"
            params = {f"c{i}": code for i, code in enumerate(codes)}
            params["report_date"] = report_date
            sql = f"DELETE FROM `{table}` WHERE report_date = :report_date AND `{code_col}` IN ({placeholders})"
            with engine.begin() as conn:
                conn.execute(text(sql), params)
    df.to_sql(table, engine, if_exists="append", index=False, method="multi")


def main() -> None:
    """脚本入口函数。"""
    parser = argparse.ArgumentParser(description="Load PV company financials from Eastmoney via AkShare into MySQL")
    parser.add_argument(
        "--companies",
        nargs="+",
        default=["迈为股份", "捷佳伟创", "拉普拉斯", "奥特维", "晶盛机电", "连城数控"],
        help="Company names to load",
    )
    parser.add_argument("--start-year", type=int, default=dt.datetime.now().year - 6)
    parser.add_argument("--end-year", type=int, default=dt.datetime.now().year - 1)
    parser.add_argument("--annual-only", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.6)
    parser.add_argument("--table-prefix", default="test_")
    args = parser.parse_args()

    ak = _import_akshare()
    engine, _settings = _build_engine()

    code_map = _get_code_map(ak)
    mapping = _match_codes(code_map, args.companies)
    if not mapping:
        raise SystemExit("No company codes matched. Please provide correct company names.")

    company_df = pd.DataFrame(
        [{"company_name": k, "stock_code": v} for k, v in mapping.items()]
    )
    company_df.to_sql(f"{args.table_prefix}company", engine, if_exists="replace", index=False)

    dates = _daterange(args.start_year, args.end_year, args.annual_only)
    codes = list(mapping.values())

    tasks = [
        ("yjbb", ["stock_yjbb_em", "stock_em_yjbb"]),
        ("zcfz", ["stock_em_zcfz", "stock_zcfz_em", "stock_em_zcfz_report"]),
        ("lrb", ["stock_em_lrb", "stock_lrb_em", "stock_em_lrb_report"]),
        ("xjll", ["stock_xjll_em", "stock_em_xjll", "stock_em_xjll_report"]),
    ]

    for report_date in dates:
        for short, func_names in tasks:
            try:
                df = _safe_call(ak, func_names, date=report_date)
            except Exception as exc:
                print(f"[WARN] {short} {report_date} fetch failed: {exc}")
                continue
            df = _filter_targets(df, codes)
            df = _ensure_report_date(df, report_date)
            table = f"{args.table_prefix}em_{short}"
            _upsert_table(engine, table, df, report_date, codes)
            print(f"[OK] {table} {report_date} rows={len(df)}")
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
