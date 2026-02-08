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
    match = ALLOWED_HINT_PATTERN.search(sql)
    if not match:
        return sql, None
    cleaned = ALLOWED_HINT_PATTERN.sub("", sql, count=1)
    return cleaned, match.group(0)


def _strip_trailing_semicolon(sql: str) -> str:
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
    if not hint:
        return sql
    stripped = sql.lstrip()
    if not stripped.upper().startswith("SELECT"):
        return sql
    prefix = sql[: len(sql) - len(stripped)]
    return prefix + stripped.replace("SELECT", f"SELECT {hint}", 1)


def ensure_select_only(sql: str) -> None:
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
    if sqlglot is None or exp is None:
        return sql
    cleaned, hint = _extract_allowed_hint(sql)
    cleaned = _strip_trailing_semicolon(cleaned)
    parsed = sqlglot.parse_one(cleaned, read="mysql")
    target = schema.lower() if isinstance(schema, str) and schema else None
    for table in parsed.find_all(exp.Table):
        db = table.args.get("db")
        if db is None:
            continue
        db_name = db.name.lower() if hasattr(db, "name") else str(db).lower()
        if target is None or db_name == target:
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
