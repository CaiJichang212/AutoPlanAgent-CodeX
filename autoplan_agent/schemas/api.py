from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.schemas.plan import ExecutionPlan
from autoplan_agent.schemas.artifacts import Artifact


class RunCreateRequest(BaseModel):
    user_task: str
    template_id: Optional[str] = None
    limits: Optional[Dict[str, Any]] = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: str
    understanding: Optional[TaskUnderstandingReport] = None
    plan: Optional[ExecutionPlan] = None
    open_questions: List[str] = Field(default_factory=list)


class RunConfirmRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    patch_understanding: Optional[Dict[str, Any]] = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    understanding: Optional[TaskUnderstandingReport] = None
    plan: Optional[ExecutionPlan] = None
    artifacts: List[Artifact] = Field(default_factory=list)
    message: Optional[str] = None

