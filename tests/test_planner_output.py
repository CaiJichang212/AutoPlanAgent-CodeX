import os

from autoplan_agent.config import Settings
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.workflow import plan_task


def test_plan_fallback_generates_steps(monkeypatch):
    monkeypatch.setenv("LLM_FAKE", "1")
    monkeypatch.setenv("LLM_FAKE_JSON", "{}")
    settings = Settings()
    state = {
        "run_id": "run_test",
        "user_task": "测试任务",
        "understanding": TaskUnderstandingReport(analysis_goal="测试任务"),
    }
    plan = plan_task(state, settings)
    assert plan.steps
