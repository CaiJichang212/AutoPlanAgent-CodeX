"""API 数据模型模块。

该模块定义了 API 请求和响应的 Pydantic 模型。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.schemas.plan import ExecutionPlan
from autoplan_agent.schemas.artifacts import Artifact


class RunCreateRequest(BaseModel):
    """创建运行任务的请求模型。

    Attributes:
        user_task: 用户任务描述。
        template_id: 可选的模板 ID。
        limits: 可选的限制条件字典。
    """
    user_task: str
    template_id: Optional[str] = None
    limits: Optional[Dict[str, Any]] = None


class RunCreateResponse(BaseModel):
    """创建运行任务的响应模型。

    Attributes:
        run_id: 运行 ID。
        status: 任务状态。
        understanding: 任务理解报告。
        plan: 执行计划。
        open_questions: 待回答的问题列表。
    """
    run_id: str
    status: str
    understanding: Optional[TaskUnderstandingReport] = None
    plan: Optional[ExecutionPlan] = None
    open_questions: List[str] = Field(default_factory=list)


class RunConfirmRequest(BaseModel):
    """确认运行任务的请求模型。

    Attributes:
        approved: 是否批准执行。
        feedback: 用户反馈。
        patch_understanding: 修正后的理解数据。
    """
    approved: bool
    feedback: Optional[str] = None
    patch_understanding: Optional[Dict[str, Any]] = None


class RunStatusResponse(BaseModel):
    """查询运行状态的响应模型。

    Attributes:
        run_id: 运行 ID。
        status: 任务状态。
        understanding: 任务理解报告。
        plan: 执行计划。
        artifacts: 生成的产物列表。
        message: 状态消息。
    """
    run_id: str
    status: str
    understanding: Optional[TaskUnderstandingReport] = None
    plan: Optional[ExecutionPlan] = None
    artifacts: List[Artifact] = Field(default_factory=list)
    message: Optional[str] = None

