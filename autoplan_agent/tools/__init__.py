"""工具包初始化模块。

该模块负责构建并返回工具注册表，其中注册了所有可用的内置工具。
"""

from autoplan_agent.schemas.artifacts import StepResult
import importlib.util
from pathlib import Path

from autoplan_agent.config import Settings
from autoplan_agent.tools.registry import ToolRegistry, ToolSpec
from autoplan_agent.tools.mysql.tools import (
    SchemaToolInput,
    QueryToolInput,
    ExplainToolInput,
    schema_tool,
    query_tool,
    explain_tool,
)
from autoplan_agent.tools.builtins import (
    CleanInput,
    EDAInput,
    StatsInput,
    MiningInput,
    VizInput,
    ReportInput,
    dataframe_clean,
    dataframe_eda,
    stats_tool,
    mining_tool,
    viz_tool,
    report_tool,
)


def build_registry(settings: Settings | None = None) -> ToolRegistry:
    """构建并初始化工具注册表。

    Args:
        settings: 可选的应用配置。

    Returns:
        ToolRegistry: 已注册所有内置工具的注册表实例。
    """
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="mysql.schema",
            input_model=SchemaToolInput,
            output_model=StepResult,
            handler=schema_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="mysql.query",
            input_model=QueryToolInput,
            output_model=StepResult,
            handler=query_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="mysql.explain",
            input_model=ExplainToolInput,
            output_model=StepResult,
            handler=explain_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="dataframe.clean",
            input_model=CleanInput,
            output_model=StepResult,
            handler=dataframe_clean,
        )
    )
    registry.register(
        ToolSpec(
            name="dataframe.eda",
            input_model=EDAInput,
            output_model=StepResult,
            handler=dataframe_eda,
        )
    )
    registry.register(
        ToolSpec(
            name="stats.describe",
            input_model=StatsInput,
            output_model=StepResult,
            handler=stats_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="mining.anomaly",
            input_model=MiningInput,
            output_model=StepResult,
            handler=mining_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="viz.plotly",
            input_model=VizInput,
            output_model=StepResult,
            handler=viz_tool,
        )
    )
    registry.register(
        ToolSpec(
            name="report.generate",
            input_model=ReportInput,
            output_model=StepResult,
            handler=report_tool,
        )
    )
    if settings and settings.plugins_dir:
        _load_plugins(registry, Path(settings.plugins_dir))
    return registry


def _load_plugins(registry: ToolRegistry, plugins_dir: Path) -> None:
    if not plugins_dir.exists():
        return
    for plugin_file in plugins_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "register"):
            module.register(registry)
