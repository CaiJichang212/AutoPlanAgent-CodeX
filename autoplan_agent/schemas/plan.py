from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    max_retries: int = 1
    backoff_s: float = 1.0


class PlanStep(BaseModel):
    step_id: str
    name: str
    tool: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    on_error: str = "ask_user"


class PlanCost(BaseModel):
    db_queries: int = 0
    expected_rows: int = 0
    runtime_s: int = 0
    memory_mb: int = 0


class ExecutionPlan(BaseModel):
    plan_id: str
    run_id: str
    version: int = 1
    steps: List[PlanStep]
    estimated_cost: PlanCost = Field(default_factory=PlanCost)
    risks: List[str] = Field(default_factory=list)

