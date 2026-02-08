"""任务理解模型模块。

该模块定义了任务理解报告及其相关组件（如时间范围、数据范围、约束条件、产物要求）的 Pydantic 模型。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    """时间范围模型。

    Attributes:
        start: 开始时间。
        end: 结束时间。
        timezone: 时区，默认为 UTC。
        grain: 时间粒度（如 daily, monthly）。
    """
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: Optional[str] = "UTC"
    grain: Optional[str] = None


class DataScope(BaseModel):
    """数据范围模型。

    Attributes:
        dialect: 数据库方言，默认为 mysql。
        db_schema: 数据库 schema。
        tables: 表名列表。
        columns: 列名列表。
        filters: 过滤条件列表。
        metrics: 指标列表。
    """
    dialect: str = "mysql"
    db_schema: Optional[str] = Field(default=None, alias="schema")
    tables: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)


class Constraints(BaseModel):
    """约束条件模型。

    Attributes:
        max_rows: 最大返回行数。
        max_runtime_s: 最大运行时间（秒）。
        privacy_notes: 隐私注意事项。
        sampling: 采样策略。
    """
    max_rows: Optional[int] = None
    max_runtime_s: Optional[int] = None
    privacy_notes: Optional[str] = None
    sampling: Optional[str] = None


class Deliverables(BaseModel):
    """交付物模型。

    Attributes:
        charts: 图表类型列表。
        tables: 表格类型列表。
        report_sections: 报告章节列表。
        format: 交付格式列表（如 markdown, html, pdf）。
    """
    charts: List[str] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)
    report_sections: List[str] = Field(default_factory=list)
    format: List[str] = Field(default_factory=lambda: ["markdown", "html", "pdf"])


class TaskUnderstandingReport(BaseModel):
    """任务理解报告模型。

    Attributes:
        analysis_goal: 分析目标。
        business_context: 业务背景。
        time_range: 时间范围。
        data_scope: 数据范围。
        detection_type: 检测类型（如 anomaly）。
        constraints: 约束条件。
        expected_deliverables: 预期交付物。
        open_questions: 待回答的问题列表。
        assumptions: 假设列表。
    """
    analysis_goal: str
    business_context: Optional[str] = None
    time_range: Optional[TimeRange] = None
    data_scope: DataScope = Field(default_factory=DataScope)
    detection_type: str = "anomaly"
    constraints: Constraints = Field(default_factory=Constraints)
    expected_deliverables: Deliverables = Field(default_factory=Deliverables)
    open_questions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
