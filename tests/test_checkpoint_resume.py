"""检查点恢复功能测试模块。

该模块测试工作流在暂停后通过检查点正确恢复并继续执行的功能。
"""

from pathlib import Path

import pytest

from autoplan_agent.config import Settings
from autoplan_agent.workflow import run_graph


def test_checkpoint_resume(tmp_path: Path, monkeypatch):
    """测试工作流通过检查点恢复执行的过程。

    Args:
        tmp_path: 临时路径对象。
        monkeypatch: pytest 环境变量修改工具。
    """
    try:
        import langgraph.checkpoint.sqlite  # noqa: F401
    except Exception:
        pytest.skip("langgraph[sqlite] not installed")
    templates_dir = tmp_path / "templates"
    (templates_dir / "plans").mkdir(parents=True)
    (templates_dir / "report").mkdir(parents=True)

    (templates_dir / "plans" / "default.yaml").write_text(
        "steps:\n  - name: 报告生成\n    tool: report.generate\n    outputs: ['report']\n",
        encoding="utf-8",
    )
    (templates_dir / "report" / "report.md.j2").write_text("# {{ summary }}", encoding="utf-8")
    (templates_dir / "report" / "report.html.j2").write_text("<html>{{ summary }}</html>", encoding="utf-8")

    monkeypatch.setenv("LLM_FAKE", "1")
    monkeypatch.setenv("LLM_FAKE_JSON", "{}")
    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    settings = Settings()

    run_id = "run_checkpoint"
    first = run_graph({"run_id": run_id, "user_task": "test task", "approved": False}, settings)
    assert first["status"] == "NEEDS_CONFIRMATION"

    second = run_graph({"run_id": run_id, "approved": True}, settings)
    assert second["status"] == "DONE"
