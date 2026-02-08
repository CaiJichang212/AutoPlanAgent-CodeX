from dataclasses import dataclass
from typing import Callable, Dict, Type

from pydantic import BaseModel


@dataclass
class ToolContext:
    run_id: str
    run_dir: str
    settings: object
    logger: object
    state: dict


@dataclass
class ToolSpec:
    name: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    handler: Callable[[BaseModel, ToolContext], BaseModel]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def run(self, name: str, inputs: dict, context: ToolContext):
        tool = self.get(name)
        parsed = tool.input_model(**inputs)
        return tool.handler(parsed, context)
