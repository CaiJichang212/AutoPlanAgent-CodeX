"""MySQL 客户端工具模块。

该模块提供 MySQL 引擎创建和 Schema 提示信息加载功能。
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from typing import List, Dict, Any, Optional

from autoplan_agent.config import Settings


def create_mysql_engine(settings: Settings) -> Engine:
    """创建 SQLAlchemy MySQL 引擎。

    Args:
        settings: 应用配置对象。

    Returns:
        Engine: SQLAlchemy 引擎实例。

    Raises:
        RuntimeError: 如果缺少连接信息。
    """
    dsn = settings.mysql_dsn()
    if not dsn:
        raise RuntimeError("MySQL connection info missing. Set MYSQL_URL or MYSQL_HOST/USER/PASSWORD/DB.")

    connect_args = {}
    if "pymysql" in dsn:
        connect_args.update(
            {
                "connect_timeout": settings.mysql_connect_timeout_s,
                "read_timeout": settings.mysql_read_timeout_s,
                "write_timeout": settings.mysql_write_timeout_s,
            }
        )
    if settings.mysql_ssl_ca:
        connect_args["ssl"] = {
            "ca": settings.mysql_ssl_ca,
            "cert": settings.mysql_ssl_cert,
            "key": settings.mysql_ssl_key,
        }
    return create_engine(
        dsn,
        pool_pre_ping=True,
        pool_recycle=settings.mysql_pool_recycle_s,
        pool_size=settings.mysql_pool_size,
        max_overflow=settings.mysql_max_overflow,
        connect_args=connect_args,
    )


def load_mysql_schema_hint(settings: Settings, relevant_tables: List[str] | None = None) -> str | None:
    """加载 MySQL Schema 提示信息。

    用于辅助 LLM 生成 SQL 语句，包含表结构和特定的连接逻辑提示。

    Args:
        settings: 应用配置对象。
        relevant_tables: 相关表名列表。

    Returns:
        str | None: Schema 提示字符串，如果失败则返回 None。
    """
    dsn = settings.mysql_dsn()
    if not dsn:
        return None
    try:
        engine = create_mysql_engine(settings)
        insp = inspect(engine)
        all_tables = insp.get_table_names()
        if not all_tables:
            return None
        
        # If relevant_tables is provided, prioritize them
        tables_to_show = []
        if relevant_tables:
            tables_to_show = [t for t in relevant_tables if t in all_tables]
        
        # If no relevant tables found or not provided, show a few general ones
        if not tables_to_show:
            tables_to_show = all_tables[:10]
        
        hint_lines = []
        for name in tables_to_show:
            columns = [col["name"] for col in insp.get_columns(name)]
            hint_lines.append(f"Table: {name}\nColumns: {', '.join(columns)}")
        
        # Add extremely specific hints for joining and complex column names
        join_hints = """
### CRITICAL SCHEMA HINTS ###
1. EXACT COLUMN NAMES & FORMATS:
   - test_em_yjbb: `净利润-净利润`, `营业总收入-营业总收入`, `最新公告日期`, `report_date` (Format: 'YYYYMMDD' like '20231231', NO hyphens)
   - pv_financials: `report_period` (Format: '2023Q4' or '2024H1')
   - Date Filtering: Use 'YYYYMMDD' format without hyphens for `report_date` (e.g., `report_date >= '20231001'`).

2. JOINING LOGIC:
    - Base table: `pv_financials` (f)
    - Join `test_em_yjbb` (y): 
              Recommend using `LEFT JOIN` and match on company name/code.
              **CRITICAL: Date alignment for 2024H1**:
              `f.report_period = (CASE WHEN SUBSTR(y.report_date, 5, 2) = '06' THEN CONCAT(LEFT(y.report_date, 4), 'H1') ELSE CONCAT(LEFT(y.report_date, 4), 'Q', (CASE SUBSTR(y.report_date, 5, 2) WHEN '03' THEN 1 WHEN '09' THEN 3 WHEN '12' THEN 4 END)) END)`
    - Join `test_em_xjll` (x) and `test_em_zcfz` (z): 
      **Recommend matching on company AND announcement date**:
      `AND x.公告日期 = y.最新公告日期`
   - Join `stock_prices` (s):
     Match on ticker and `report_period`.

3. PERFORMANCE & RELIABILITY:
    - `pv_financials` already contains only PV companies. `industry_role` contains specific sub-sectors, NOT '光伏'.
    - **CRITICAL: AVAILABLE PERIODS**: The latest available periods in `pv_financials` are `2024H1`, `2023Q4`, `2023Q3`, etc. **DO NOT use `2024Q4`** as it does not exist yet.
    - **CRITICAL: LEFT JOIN & WHERE**: If using `LEFT JOIN` for `y`, `x`, `z`, **DO NOT** put their columns (like `y.最新公告日期`, `x.公告日期`) in the `WHERE` clause. This will filter out any row where that table has no matching data, effectively turning it into an INNER JOIN and likely returning zero results.
    - Filter ONLY by `f.report_period` in the `WHERE` clause.

4. COLUMN ALIASING:
   - Always use English aliases for Chinese columns. Example: `SELECT `净利润-净利润` AS net_profit ...`
"""
        hint_lines.append(join_hints)
        
        return "\n\n".join(hint_lines)
    except Exception as e:
        print(f"Error loading schema hint: {e}")
        return None
