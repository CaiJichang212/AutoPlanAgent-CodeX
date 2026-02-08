"""SQL 防护功能测试模块。

该模块测试 SQL 查询的安全性检查功能，包括只读检查和行数限制。
"""

import pytest

from autoplan_agent.tools.mysql import guard


def test_ensure_select_only_allows_select():
    """测试 ensure_select_only 允许合法的 SELECT 语句。"""
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    guard.ensure_select_only("SELECT * FROM users")


def test_ensure_select_only_blocks_update():
    """测试 ensure_select_only 拦截非 SELECT 语句（如 UPDATE）。"""
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    with pytest.raises(ValueError):
        guard.ensure_select_only("UPDATE users SET name='x'")


def test_enforce_limit_adds_limit():
    """测试 enforce_limit 是否能正确为 SQL 语句添加 LIMIT 子句。"""
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    sql, limit = guard.enforce_limit("SELECT * FROM users", 100)
    assert "LIMIT" in sql.upper()
    assert limit == 100
