from pathlib import Path

import pytest

from autoplan_agent.config import Settings
from autoplan_agent.workflow import run_graph


def test_checkpoint_resume(tmp_path: Path, monkeypatch):
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
