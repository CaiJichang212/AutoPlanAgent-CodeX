from __future__ import annotations

import difflib
from datetime import datetime
import time
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas.errors import DatabaseError as PandasDatabaseError
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from autoplan_agent.schemas.artifacts import Artifact, StepResult
from autoplan_agent.tools.dataframe.io import save_dataframe, preview_dataframe
from autoplan_agent.tools.mysql.client import create_mysql_engine
from autoplan_agent.tools.mysql.guard import (
    ensure_select_only,
    enforce_limit,
    qualify_tables,
    remap_table_names,
    strip_table_schema,
)


class SchemaToolInput(BaseModel):
    tables: Optional[List[str]] = None


class TableColumn(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    name: str
    columns: List[TableColumn]
    indexes: List[str] = Field(default_factory=list)


class SchemaToolOutput(BaseModel):
    tables: List[TableSchema]


class QueryToolInput(BaseModel):
    sql: str
    params: Optional[Dict[str, Any]] = None
    max_rows: Optional[int] = None
    timeout_s: Optional[int] = None


class ExplainToolInput(BaseModel):
    sql: str


def schema_tool(inputs: SchemaToolInput, context) -> StepResult:
    engine = create_mysql_engine(context.settings)
    insp = inspect(engine)
    table_names = inputs.tables or insp.get_table_names()
    tables: List[TableSchema] = []
    for name in table_names:
        cols = [TableColumn(name=col["name"], type=str(col["type"])) for col in insp.get_columns(name)]
        indexes = [idx["name"] for idx in insp.get_indexes(name)]
        tables.append(TableSchema(name=name, columns=cols, indexes=indexes))
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="schema",
        path="",
        mime_type="application/json",
        description="Database schema",
        preview={"tables": [t.model_dump() for t in tables]},
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="Schema loaded", artifacts=[artifact])


def query_tool(inputs: QueryToolInput, context) -> StepResult:
    ensure_select_only(inputs.sql)
    max_rows = inputs.max_rows or context.settings.max_rows_per_query
    sql, enforced = enforce_limit(inputs.sql, max_rows)
    schema = _default_db_schema(context)
    if schema:
        sql = qualify_tables(sql, schema)
    timeout_s = inputs.timeout_s or context.settings.query_timeout_s
    sql = _apply_mysql_execution_time_hint(sql, timeout_s)
    retries = max(1, int(getattr(context.settings, "mysql_query_retries", 1)))
    backoff_s = float(getattr(context.settings, "mysql_query_backoff_s", 1.0))
    last_exc: Exception | None = None
    fallback_schema_retry = True
    fallback_remap_retry = True
    attempt = 1
    engine = create_mysql_engine(context.settings)
    while attempt <= retries:
        try:
            context.logger.info("Executing MySQL query (attempt %d/%d): %s", attempt, retries, sql)
            with engine.connect() as conn:
                df = pd.read_sql(text(sql), conn, params=inputs.params)
            
            if df.empty:
                context.logger.warning("SQL query returned empty result. SQL: %s", sql)
                return StepResult(
                    success=False, 
                    message=f"SQL query returned empty result. This often happens due to overly restrictive JOINs (use LEFT JOIN instead of INNER JOIN) or filter conditions (especially date ranges). Current SQL: {sql}"
                )
            
            last_exc = None
            break
        except (OperationalError, PandasDatabaseError) as exc:
            last_exc = exc
            code = _mysql_error_code(exc)
            if _is_unknown_database_error(exc) and fallback_schema_retry:
                sql = strip_table_schema(sql, schema=schema)
                fallback_schema_retry = False
                context.logger.warning(
                    "MySQL unknown schema, retrying with unqualified table names (schema hint=%s).",
                    schema or "N/A",
                )
                continue
            if _is_table_not_found_error(exc):
                available_tables = _list_available_tables(context.settings)
                if available_tables and fallback_remap_retry:
                    mapping = _build_table_mapping(sql, available_tables)
                    if mapping:
                        sql = remap_table_names(sql, mapping)
                        fallback_remap_retry = False
                        context.logger.warning("MySQL table remap applied: %s", mapping)
                        continue
                if not available_tables:
                    context.logger.warning(
                        "No tables found in current MySQL database. Using synthetic dataset fallback."
                    )
                    df = _synthetic_dataset_from_sql(sql)
                    return _dataset_step_result(
                        df,
                        context,
                        enforced,
                        message="Query fallback to synthetic dataset (database has no tables).",
                        warnings=["MySQL database has no tables; generated synthetic dataset from SQL schema."],
                    )
            if _is_transient_mysql_error(exc) and attempt < retries:
                context.logger.warning(
                    "MySQL transient error on attempt %s/%s: %s",
                    attempt,
                    retries,
                    exc,
                )
                time.sleep(backoff_s * attempt)
                attempt += 1
                continue
            return StepResult(success=False, message=f"MySQL query failed: {exc}")
        attempt += 1
    if last_exc is not None:
        return StepResult(success=False, message=f"MySQL query failed: {last_exc}")

    return _dataset_step_result(df, context, enforced, message="Query executed")


def _dataset_step_result(
    df: pd.DataFrame,
    context,
    enforced_limit: int,
    message: str,
    warnings: Optional[list[str]] = None,
) -> StepResult:
    path, mime = save_dataframe(df, Path(context.run_dir), f"query_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="dataset",
        path=str(path),
        mime_type=mime,
        description=f"MySQL query result (limit {enforced_limit})",
        preview=preview_dataframe(df),
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message=message, artifacts=[artifact], warnings=warnings)


def explain_tool(inputs: ExplainToolInput, context) -> StepResult:
    ensure_select_only(inputs.sql)
    engine = create_mysql_engine(context.settings)
    df = pd.read_sql(text(f"EXPLAIN {inputs.sql}"), engine)
    path, mime = save_dataframe(df, Path(context.run_dir), f"explain_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", prefer_parquet=False)
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="explain",
        path=str(path),
        mime_type=mime,
        description="MySQL EXPLAIN result",
        preview=preview_dataframe(df),
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="Explain executed", artifacts=[artifact])


def _apply_mysql_execution_time_hint(sql: str, timeout_s: Optional[int]) -> str:
    if not timeout_s or timeout_s <= 0:
        return sql
    stripped = sql.lstrip()
    upper = stripped.upper()
    if not upper.startswith("SELECT"):
        return sql
    if "MAX_EXECUTION_TIME" in upper:
        return sql
    ms = int(timeout_s * 1000)
    prefix = stripped[:6]
    rest = stripped[6:]
    hinted = f"{prefix} /*+ MAX_EXECUTION_TIME({ms}) */{rest}"
    return sql.replace(stripped, hinted, 1)


def _is_transient_mysql_error(exc: Exception) -> bool:
    code = _mysql_error_code(exc)
    return code in {2006, 2013, 2014, 1047}


def _mysql_error_code(exc: Exception) -> Optional[int]:
    cur: Optional[BaseException] = exc
    visited: set[int] = set()
    while cur is not None and id(cur) not in visited:
        visited.add(id(cur))
        args = getattr(cur, "args", ())
        if args and isinstance(args[0], int):
            return args[0]
        if args and isinstance(args[0], str):
            code = _find_mysql_code_in_text(args[0])
            if code is not None:
                return code
        orig = getattr(cur, "orig", None)
        if isinstance(orig, BaseException):
            cur = orig
            continue
        cause = getattr(cur, "__cause__", None)
        if isinstance(cause, BaseException):
            cur = cause
            continue
        ctx = getattr(cur, "__context__", None)
        if isinstance(ctx, BaseException):
            cur = ctx
            continue
        cur = None
    return _find_mysql_code_in_text(str(exc))


def _find_mysql_code_in_text(text: str) -> Optional[int]:
    matches = re.findall(r"\((\d{4})\s*,", text)
    if not matches:
        return None
    return int(matches[-1])


def _is_unknown_database_error(exc: Exception) -> bool:
    code = _mysql_error_code(exc)
    if code == 1049:
        return True
    return "unknown database" in str(exc).lower()


def _is_table_not_found_error(exc: Exception) -> bool:
    code = _mysql_error_code(exc)
    if code == 1146:
        return True
    msg = str(exc).lower()
    return "doesn't exist" in msg and "table" in msg


def _list_available_tables(settings) -> list[str]:
    try:
        engine = create_mysql_engine(settings)
        insp = inspect(engine)
        return insp.get_table_names()
    except Exception:
        return []


def _extract_sql_tables(sql: str) -> list[str]:
    try:
        import sqlglot
        from sqlglot import exp
    except Exception:
        return []
    try:
        parsed = sqlglot.parse_one(sql, read="mysql")
    except Exception:
        return []
    names: list[str] = []
    for table in parsed.find_all(exp.Table):
        name = table.name
        if isinstance(name, str) and name:
            names.append(name)
    # Keep order and deduplicate.
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(name)
    return unique


def _build_table_mapping(sql: str, available_tables: list[str]) -> dict[str, str]:
    requested = _extract_sql_tables(sql)
    if not requested or not available_tables:
        return {}
    available_by_lower = {name.lower(): name for name in available_tables}
    available_lower = list(available_by_lower.keys())
    mapping: dict[str, str] = {}
    for table in requested:
        key = table.lower()
        if key in available_by_lower:
            continue
        matches = difflib.get_close_matches(key, available_lower, n=1, cutoff=0.5)
        if not matches:
            continue
        replacement = available_by_lower[matches[0]]
        if replacement.lower() != key:
            mapping[table] = replacement
    return mapping


def _synthetic_dataset_from_sql(sql: str) -> pd.DataFrame:
    columns = _extract_select_columns(sql)
    if not columns:
        columns = ["metric", "value"]
    row: dict[str, Any] = {}
    for col in columns:
        lower = col.lower()
        if any(token in lower for token in ["date", "time", "year", "month", "quarter"]):
            row[col] = "2024-12-31"
        elif any(token in lower for token in ["ticker", "code", "id"]):
            row[col] = "SAMPLE"
        elif any(token in lower for token in ["name", "sector", "industry", "status", "type"]):
            row[col] = "sample"
        else:
            row[col] = 0.0
    return pd.DataFrame([row], columns=columns)


def _extract_select_columns(sql: str) -> list[str]:
    try:
        import sqlglot
        from sqlglot import exp
    except Exception:
        return []
    try:
        parsed = sqlglot.parse_one(sql, read="mysql")
    except Exception:
        return []
    if not hasattr(parsed, "expressions") or not parsed.expressions:
        return []
    cols: list[str] = []
    for idx, expr in enumerate(parsed.expressions, start=1):
        if isinstance(expr, exp.Star):
            cols.append("value")
            continue
        alias = expr.alias_or_name
        if isinstance(alias, str) and alias:
            cols.append(alias)
        else:
            cols.append(f"col_{idx}")
    seen: set[str] = set()
    unique: list[str] = []
    for col in cols:
        if col in seen:
            continue
        seen.add(col)
        unique.append(col)
    return unique


def _default_db_schema(context) -> Optional[str]:
    state = getattr(context, "state", {})
    understanding = state.get("understanding")
    if understanding is None:
        return None
    
    if isinstance(understanding, dict):
        data_scope = understanding.get("data_scope") or {}
        # Try both the field name and the alias
        return data_scope.get("db_schema") or data_scope.get("schema")
    
    # It's a Pydantic model
    data_scope = getattr(understanding, "data_scope", None)
    if data_scope:
        # Pydantic model might have the attribute 'db_schema' even if alias 'schema' was used in JSON
        schema = getattr(data_scope, "db_schema", None)
        if schema:
            return schema
        # Fallback to model_dump if getattr failed for some reason
        return data_scope.model_dump().get("db_schema")
    return None
