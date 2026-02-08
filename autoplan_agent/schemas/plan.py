"""执行计划模型模块。

该模块定义了执行计划及其相关组件（如步骤、重试策略、成本估算）的 Pydantic 模型。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    """重试策略模型。

    Attributes:
        max_retries: 最大重试次数。
        backoff_s: 退避时间（秒）。
    """
    max_retries: int = 1
    backoff_s: float = 1.0


class PlanStep(BaseModel):
    """计划步骤模型。

    Attributes:
        step_id: 步骤唯一标识。
        name: 步骤名称。
        tool: 使用的工具名称。
        inputs: 工具输入参数。
        depends_on: 依赖的步骤 ID 列表。
        outputs: 输出定义列表。
        retry_policy: 重retry策略。
        on_error: 出错时的处理方式（如 ask_user, stop, continue）。
    """
    step_id: str
    name: str
    tool: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    on_error: str = "ask_user"


class PlanCost(BaseModel):
    """计划成本估算模型。

    Attributes:
        db_queries: 预计数据库查询次数。
        expected_rows: 预计处理的行数。
        runtime_s: 预计运行时间（秒）。
        memory_mb: 预计消耗的内存（MB）。
    """
    db_queries: int = 0
    expected_rows: int = 0
    runtime_s: int = 0
    memory_mb: int = 0


class ExecutionPlan(BaseModel):
    """执行计划模型。

    Attributes:
        plan_id: 计划唯一标识。
        run_id: 运行 ID。
        version: 计划版本。
        steps: 计划包含的步骤列表。
        estimated_cost: 预计成本。
        risks: 潜在风险列表。
    """
    plan_id: str
    run_id: str
    version: int = 1
    steps: List[PlanStep]
    estimated_cost: PlanCost = Field(default_factory=PlanCost)
    risks: List[str] = Field(default_factory=list)

