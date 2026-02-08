from typing import List, Optional
from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: Optional[str] = "UTC"
    grain: Optional[str] = None


class DataScope(BaseModel):
    dialect: str = "mysql"
    db_schema: Optional[str] = Field(default=None, alias="schema")
    tables: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)


class Constraints(BaseModel):
    max_rows: Optional[int] = None
    max_runtime_s: Optional[int] = None
    privacy_notes: Optional[str] = None
    sampling: Optional[str] = None


class Deliverables(BaseModel):
    charts: List[str] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)
    report_sections: List[str] = Field(default_factory=list)
    format: List[str] = Field(default_factory=lambda: ["markdown", "html", "pdf"])


class TaskUnderstandingReport(BaseModel):
    analysis_goal: str
    business_context: Optional[str] = None
    time_range: Optional[TimeRange] = None
    data_scope: DataScope = Field(default_factory=DataScope)
    detection_type: str = "anomaly"
    constraints: Constraints = Field(default_factory=Constraints)
    expected_deliverables: Deliverables = Field(default_factory=Deliverables)
    open_questions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
