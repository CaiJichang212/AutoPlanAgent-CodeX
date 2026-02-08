"""计划器输出测试模块。

该模块测试计划制定功能在 LLM 输出为空或其他异常情况下的后备（fallback）逻辑。
"""

import os

from autoplan_agent.config import Settings
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.workflow import plan_task


def test_plan_fallback_generates_steps(monkeypatch):
    """测试计划制定的后备逻辑是否能生成步骤。

    Args:
        monkeypatch: pytest 环境变量修改工具。
    """
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
