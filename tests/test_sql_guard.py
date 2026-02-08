import pytest

from autoplan_agent.tools.mysql import guard


def test_ensure_select_only_allows_select():
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    guard.ensure_select_only("SELECT * FROM users")


def test_ensure_select_only_blocks_update():
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    with pytest.raises(ValueError):
        guard.ensure_select_only("UPDATE users SET name='x'")


def test_enforce_limit_adds_limit():
    if guard.sqlglot is None:
        pytest.skip("sqlglot not installed")
    sql, limit = guard.enforce_limit("SELECT * FROM users", 100)
    assert "LIMIT" in sql.upper()
    assert limit == 100
