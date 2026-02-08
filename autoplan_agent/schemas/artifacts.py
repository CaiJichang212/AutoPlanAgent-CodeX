from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Artifact(BaseModel):
    artifact_id: str
    type: str
    path: str
    mime_type: str
    description: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class StepResult(BaseModel):
    success: bool
    message: str
    artifacts: List[Artifact] = Field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None

