"""SQL 安全防护工具模块。

该模块提供 SQL 语句的校验、限制和修饰功能，确保仅执行安全的 SELECT 查询。
"""

import re
from typing import Tuple

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover
    sqlglot = None
    exp = None


UNSAFE_PATTERN = re.compile(r"--|/\*|\*/", re.MULTILINE)
ALLOWED_HINT_PATTERN = re.compile(r"/\*\+\s*MAX_EXECUTION_TIME\(\d+\)\s*\*/", re.IGNORECASE)


def _extract_allowed_hint(sql: str) -> Tuple[str, str | None]:
    """提取 SQL 中允许的提示（如 MAX_EXECUTION_TIME）。"""
    match = ALLOWED_HINT_PATTERN.search(sql)
    if not match:
        return sql, None
    cleaned = ALLOWED_HINT_PATTERN.sub("", sql, count=1)
    return cleaned, match.group(0)


def _strip_trailing_semicolon(sql: str) -> str:
    """去除 SQL 末尾的分号，并检查安全性。"""
    stripped = sql.rstrip()
    if ";" not in stripped:
        return stripped
    if stripped.endswith(";"):
        body = stripped[:-1]
        if ";" in body:
            raise ValueError("SQL contains potentially unsafe tokens.")
        return body.rstrip()
    raise ValueError("SQL contains potentially unsafe tokens.")


def _reapply_hint(sql: str, hint: str | None) -> str:
    """重新将提取的提示应用到 SQL 中。"""
    if not hint:
        return sql
    stripped = sql.lstrip()
    if not stripped.upper().startswith("SELECT"):
        return sql
    prefix = sql[: len(sql) - len(stripped)]
    return prefix + stripped.replace("SELECT", f"SELECT {hint}", 1)


def ensure_select_only(sql: str) -> None:
    """确保 SQL 仅包含 SELECT 语句。

    Args:
        sql: 待校验的 SQL 字符串。

    Raises:
        ValueError: 如果包含非 SELECT 语句或不安全字符。
        RuntimeError: 如果未安装 sqlglot。
    """
    cleaned, _ = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    if UNSAFE_PATTERN.search(cleaned):
        raise ValueError("SQL contains potentially unsafe tokens.")
    if sqlglot is None or exp is None:
        raise RuntimeError("sqlglot is required for SQL validation. Install sqlglot.")
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    if not isinstance(parsed, exp.Select):
        raise ValueError("Only SELECT statements are allowed.")


def enforce_limit(sql: str, max_rows: int) -> Tuple[str, int]:
    """强制为 SQL 添加 LIMIT 限制。

    Args:
        sql: 待处理的 SQL 字符串。
        max_rows: 最大允许行数。

    Returns:
        Tuple[str, int]: 处理后的 SQL 和实际使用的限制行数。

    Raises:
        RuntimeError: 如果未安装 sqlglot。
    """
    if sqlglot is None or exp is None:
        raise RuntimeError("sqlglot is required for SQL validation. Install sqlglot.")
    cleaned, hint = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    limit = parsed.args.get("limit")
    if limit is None:
        parsed.set("limit", exp.Limit(this=exp.Literal.number(max_rows)))
        return _reapply_hint(parsed.sql(dialect="mysql"), hint), max_rows

    try:
        current = int(limit.expression.name)
    except Exception:
        current = max_rows
    if current > max_rows:
        limit.set("expression", exp.Literal.number(max_rows))
        return _reapply_hint(parsed.sql(dialect="mysql"), hint), max_rows
    return _reapply_hint(parsed.sql(dialect="mysql"), hint), current


def qualify_tables(sql: str, schema: str) -> str:
    """为 SQL 中的表名添加指定的 Schema 前缀。

    Args:
        sql: 待处理的 SQL 字符串。
        schema: Schema 名称。

    Returns:
        str: 处理后的 SQL 字符串。
    """
    if sqlglot is None or exp is None:
        return sql
    if not schema:
        return sql
    cleaned, hint = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    schema_id = exp.to_identifier(schema)
    for table in parsed.find_all(exp.Table):
        if table.args.get("db") is None:
            table.set("db", schema_id)
    return _reapply_hint(parsed.sql(dialect="mysql"), hint)


def strip_table_schema(sql: str, schema: str | None = None) -> str:
    """去除 SQL 中表名的 Schema 前缀。

    Args:
        sql: 待处理的 SQL 字符串。
        schema: 可选的特定 Schema 名称，如果提供则仅移除该 Schema。

    Returns:
        str: 处理后的 SQL 字符串。
    """
    if sqlglot is None or exp is None:
        return sql
    cleaned, hint = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    target = schema.lower() if isinstance(schema, str) and schema else None
    for table in parsed.find_all(exp.Table):
        db = table.args.get("db")
        if db:
            if target is None or db.name.lower() == target:
                table.set("db", None)
    return _reapply_hint(parsed.sql(dialect="mysql"), hint)


def remap_table_names(sql: str, mapping: dict[str, str]) -> str:
    if sqlglot is None or exp is None:
        return sql
    if not mapping:
        return sql
    normalized = {k.lower(): v for k, v in mapping.items()}
    cleaned, hint = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    for table in parsed.find_all(exp.Table):
        name = table.name
        if not isinstance(name, str):
            continue
        replacement = normalized.get(name.lower())
        if replacement:
            table.set("this", exp.to_identifier(replacement))
            table.set("db", None)
    return _reapply_hint(parsed.sql(dialect="mysql"), hint)
