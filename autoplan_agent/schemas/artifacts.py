"""任务产物模型模块。

该模块定义了任务执行过程中生成的产物及其结果的 Pydantic 模型。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """任务产物模型。

    Attributes:
        artifact_id: 产物唯一标识。
        type: 产物类型（如 dataset, plot, report）。
        path: 产物存储路径。
        mime_type: MIME 类型。
        description: 产物描述。
        preview: 产物预览数据。
        created_at: 创建时间。
    """
    artifact_id: str
    type: str
    path: str
    mime_type: str
    description: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class StepResult(BaseModel):
    """步骤执行结果模型。

    Attributes:
        success: 是否成功。
        message: 结果消息或错误信息。
        artifacts: 该步骤生成的产物列表。
        metrics: 执行指标。
        warnings: 警告信息列表。
    """
    success: bool
    message: str
    artifacts: List[Artifact] = Field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None

