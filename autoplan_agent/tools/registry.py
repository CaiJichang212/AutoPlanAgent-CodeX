"""工具注册表模块。

该模块定义了工具上下文、工具规范以及用于管理和执行工具的注册表类。
"""

from dataclasses import dataclass
from typing import Callable, Dict, Type

from pydantic import BaseModel


@dataclass
class ToolContext:
    """工具执行上下文。

    Attributes:
        run_id: 运行 ID。
        run_dir: 运行目录路径。
        settings: 应用配置对象。
        logger: 日志记录器。
        state: 当前工作流状态。
    """
    run_id: str
    run_dir: str
    settings: object
    logger: object
    state: dict


@dataclass
class ToolSpec:
    """工具规范定义。

    Attributes:
        name: 工具名称。
        input_model: 输入数据模型类。
        output_model: 输出数据模型类。
        handler: 处理函数。
    """
    name: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    handler: Callable[[BaseModel, ToolContext], BaseModel]


class ToolRegistry:
    """工具注册表，管理所有可用的工具。"""

    def __init__(self) -> None:
        """初始化工具字典。"""
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        """注册一个新工具。

        Args:
            tool: 工具规范对象。
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec:
        """获取指定名称的工具规范。

        Args:
            name: 工具名称。

        Returns:
            ToolSpec: 工具规范对象。
        """
        return self._tools[name]

    def run(self, name: str, inputs: dict, context: ToolContext):
        """执行指定名称的工具。

        Args:
            name: 工具名称。
            inputs: 输入参数字典。
            context: 工具执行上下文。

        Returns:
            BaseModel: 工具执行结果（输出模型实例）。
        """
        tool = self.get(name)
        parsed = tool.input_model(**inputs)
        return tool.handler(parsed, context)
