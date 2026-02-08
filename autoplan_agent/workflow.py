"""工作流引擎模块。

该模块使用 LangGraph 构建任务处理工作流，包括任务理解、计划制定和计划执行等节点。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TypedDict

import yaml
from langgraph.graph import END, StateGraph
from sqlalchemy import inspect

from autoplan_agent.config import Settings
from autoplan_agent.ids import new_step_id
from autoplan_agent.llm.model_factory import get_llm
from autoplan_agent.llm.prompts import get_prompt_env
from autoplan_agent.llm.runtime import call_llm, parse_json
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.schemas.plan import ExecutionPlan
from autoplan_agent.storage.checkpoint import get_checkpointer
from autoplan_agent.storage.run_store import init_run
from autoplan_agent.tools import build_registry
from autoplan_agent.tools.mysql.client import create_mysql_engine, load_mysql_schema_hint
from autoplan_agent.executor import execute_plan
from autoplan_agent.logging_ import setup_logger


class AgentState(TypedDict, total=False):
    """代理状态定义。

    Attributes:
        run_id: 运行 ID。
        user_task: 用户任务描述。
        understanding: 任务理解报告。
        plan: 执行计划。
        approved: 是否已批准。
        feedback: 用户反馈。
        patch_understanding: 修正后的理解数据。
        artifacts: 生成的产物列表。
        status: 当前状态。
        message: 状态消息。
        template_id: 模板 ID。
    """
    run_id: str
    user_task: str
    understanding: TaskUnderstandingReport
    plan: ExecutionPlan
    approved: bool
    feedback: str | None
    patch_understanding: dict | None
    artifacts: list
    status: str
    message: str
    template_id: str


def _prompt_dir() -> Path:
    """获取提示词模板目录。

    Returns:
        Path: 提示词模板目录路径。
    """
    return Path(__file__).parent / "llm" / "prompts"


def understand_task(state: AgentState, settings: Settings) -> TaskUnderstandingReport:
    """理解用户任务。

    Args:
        state: 当前代理状态。
        settings: 应用配置。

    Returns:
        TaskUnderstandingReport: 任务理解报告。
    """
    if state.get("understanding"):
        return state["understanding"]
    llm = get_llm(settings)
    env = get_prompt_env(_prompt_dir())
    schema_hint = load_mysql_schema_hint(settings)
    prompt = env.get_template("understand.j2").render(
        user_task=state["user_task"],
        schema_hint=schema_hint
    )
    content = call_llm(llm, "You are a data analysis agent.", prompt)
    data = parse_json(content)
    if not data:
        data = {"analysis_goal": state["user_task"], "open_questions": ["请补充数据范围/时间范围"], "assumptions": []}
    data = _normalize_understanding_payload(data, state["user_task"])
    return TaskUnderstandingReport(**data)


def _coerce_str_list(value: Any) -> list[str]:
    """将值强制转换为字符串列表。

    Args:
        value: 要转换的值。

    Returns:
        list[str]: 字符串列表。
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, (tuple, set)):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        return [value]
    return [str(value)]


def _normalize_understanding_payload(data: Any, user_task: str) -> Dict[str, Any]:
    """规范化任务理解的数据负载。

    Args:
        data: 原始数据。
        user_task: 用户任务描述。

    Returns:
        Dict[str, Any]: 规范化后的数据字典。
    """
    if not isinstance(data, dict):
        data = {}

    if not isinstance(data.get("analysis_goal"), str) or not data.get("analysis_goal"):
        data["analysis_goal"] = user_task

    business_context = data.get("business_context")
    if business_context is not None and not isinstance(business_context, str):
        data["business_context"] = str(business_context)

    time_range = data.get("time_range")
    if isinstance(time_range, str):
        data["time_range"] = {"start": None, "end": None, "timezone": "UTC", "grain": time_range}
    elif time_range is not None and not isinstance(time_range, dict):
        data["time_range"] = None

    data_scope = data.get("data_scope")
    if not isinstance(data_scope, dict):
        data_scope = {}
    dialect = data_scope.get("dialect")
    if not isinstance(dialect, str) or not dialect:
        data_scope["dialect"] = "mysql"
    data_scope["tables"] = _coerce_str_list(data_scope.get("tables"))
    data_scope["columns"] = _coerce_str_list(data_scope.get("columns"))
    data_scope["filters"] = _coerce_str_list(data_scope.get("filters"))
    data_scope["metrics"] = _coerce_str_list(data_scope.get("metrics"))
    data["data_scope"] = data_scope

    detection_type = data.get("detection_type")
    if not isinstance(detection_type, str) or not detection_type:
        data["detection_type"] = "anomaly"

    constraints = data.get("constraints")
    if not isinstance(constraints, dict):
        constraints = {}
    sampling = constraints.get("sampling")
    if isinstance(sampling, bool):
        constraints["sampling"] = "true" if sampling else "false"
    elif sampling is not None and not isinstance(sampling, str):
        constraints["sampling"] = str(sampling)
    data["constraints"] = constraints

    deliverables = data.get("expected_deliverables")
    if not isinstance(deliverables, dict):
        deliverables = {}
    deliverables["charts"] = _coerce_str_list(deliverables.get("charts"))
    deliverables["tables"] = _coerce_str_list(deliverables.get("tables"))
    deliverables["report_sections"] = _coerce_str_list(deliverables.get("report_sections"))
    deliverables["format"] = _coerce_str_list(deliverables.get("format")) or ["markdown", "html", "pdf"]
    data["expected_deliverables"] = deliverables

    data["open_questions"] = _coerce_str_list(data.get("open_questions"))
    data["assumptions"] = _coerce_str_list(data.get("assumptions"))

    return data


def plan_task(state: AgentState, settings: Settings) -> ExecutionPlan:
    """为任务制定执行计划。

    Args:
        state: 当前代理状态。
        settings: 应用配置。

    Returns:
        ExecutionPlan: 执行计划对象。
    """
    if state.get("plan"):
        return state["plan"]
    llm = get_llm(settings)
    env = get_prompt_env(_prompt_dir())
    template_id = state.get("template_id", "default")
    template_path = settings.templates_dir / "plans" / f"{template_id}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template_yaml = template_path.read_text(encoding="utf-8")

    # Extract relevant tables from understanding to filter schema hint
    relevant_tables = []
    understanding = state.get("understanding")
    if understanding:
        u_dict = understanding.model_dump()
        relevant_tables = u_dict.get("data_scope", {}).get("tables", [])

    schema_hint = load_mysql_schema_hint(settings, relevant_tables=relevant_tables)
    prompt = env.get_template("plan.j2").render(
        understanding_json=state["understanding"].model_dump_json(),
        template_yaml=template_yaml,
        schema_hint=schema_hint,
    )
    content = call_llm(llm, "You are a planning engine.", prompt)
    data = parse_json(content)
    if not data or not data.get("steps"):
        # Retry once with a stronger hint
        prompt += "\n\nCRITICAL: Your previous output was not valid JSON or was missing steps. Please ensure you output a valid JSON object with a 'steps' list, and fill in the 'inputs' for each step."
        content = call_llm(llm, "You are a planning engine.", prompt)
        data = parse_json(content)
        
    if not data or not data.get("steps"):
        data = _fallback_plan(state, template_yaml)
    data = _normalize_plan_payload(data, state["run_id"])
    data = _ensure_step_ids(data)
    plan = ExecutionPlan(**data)
    return plan


def _fallback_plan(state: AgentState, template_yaml: str) -> Dict[str, Any]:
    """在计划制定失败时提供后备计划。

    Args:
        state: 当前代理状态。
        template_yaml: 计划模板 YAML 字符串。

    Returns:
        Dict[str, Any]: 后备计划数据。
    """
    template = yaml.safe_load(template_yaml)
    steps = []
    for item in template.get("steps", []):
        steps.append(
            {
                "step_id": new_step_id(),
                "name": item.get("name"),
                "tool": item.get("tool"),
                "inputs": {},
                "depends_on": [],
                "outputs": item.get("outputs", []),
                "retry_policy": {"max_retries": 1, "backoff_s": 1},
                "on_error": "ask_user",
            }
        )
    return {
        "plan_id": f"plan_{state['run_id']}",
        "run_id": state["run_id"],
        "version": 1,
        "steps": steps,
        "estimated_cost": {"db_queries": 1, "expected_rows": 1000, "runtime_s": 30, "memory_mb": 256},
        "risks": [],
    }


def _ensure_step_ids(data: Dict[str, Any]) -> Dict[str, Any]:
    """确保计划中的每个步骤都有 ID。

    Args:
        data: 计划数据。

    Returns:
        Dict[str, Any]: 更新后的计划数据。
    """
    steps = data.get("steps", [])
    for step in steps:
        if not step.get("step_id"):
            step["step_id"] = new_step_id()
    data["steps"] = steps
    if not data.get("plan_id"):
        data["plan_id"] = f"plan_{data.get('run_id', 'unknown')}"
    return data


def _coerce_int(value: Any, default: int = 0) -> int:
    """将值强制转换为整数。

    Args:
        value: 要转换的值。
        default: 转换失败时的默认值。

    Returns:
        int: 转换后的整数。
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return default
    return default


def _normalize_plan_payload(data: Any, run_id: str) -> Dict[str, Any]:
    """规范化执行计划的数据负载。

    Args:
        data: 原始计划数据。
        run_id: 运行 ID。

    Returns:
        Dict[str, Any]: 规范化后的计划数据字典。
    """
    if not isinstance(data, dict):
        data = {}

    plan_id = data.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        data["plan_id"] = f"plan_{run_id}"

    if not isinstance(data.get("run_id"), str) or not data.get("run_id"):
        data["run_id"] = run_id

    version = data.get("version")
    if not isinstance(version, int):
        data["version"] = _coerce_int(version, default=1)

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raw_steps = []

    steps: list[dict[str, Any]] = []
    for idx, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raw_step = {"name": str(raw_step), "tool": "unknown"}
        step: dict[str, Any] = {}
        step_id = raw_step.get("step_id")
        if step_id is not None and not isinstance(step_id, str):
            step_id = str(step_id)
        if isinstance(step_id, str) and step_id.strip():
            step["step_id"] = step_id
        name = raw_step.get("name")
        if not isinstance(name, str) or not name:
            name = f"step_{idx + 1}"
        step["name"] = name
        tool = raw_step.get("tool")
        if not isinstance(tool, str) or not tool:
            tool = "unknown"
        step["tool"] = tool
        inputs = raw_step.get("inputs")
        step["inputs"] = inputs if isinstance(inputs, dict) else {}
        step["depends_on"] = _coerce_str_list(raw_step.get("depends_on"))
        step["outputs"] = _coerce_str_list(raw_step.get("outputs"))
        retry_policy = raw_step.get("retry_policy")
        if isinstance(retry_policy, dict):
            step["retry_policy"] = {
                "max_retries": _coerce_int(retry_policy.get("max_retries"), default=1),
                "backoff_s": float(retry_policy.get("backoff_s", 1.0) or 1.0),
            }
        on_error = raw_step.get("on_error")
        if isinstance(on_error, str) and on_error:
            step["on_error"] = on_error
        steps.append(step)

    data["steps"] = steps

    estimated_cost = data.get("estimated_cost")
    if not isinstance(estimated_cost, dict):
        estimated_cost = {}
    data["estimated_cost"] = {
        "db_queries": _coerce_int(estimated_cost.get("db_queries"), default=0),
        "expected_rows": _coerce_int(estimated_cost.get("expected_rows"), default=0),
        "runtime_s": _coerce_int(estimated_cost.get("runtime_s"), default=0),
        "memory_mb": _coerce_int(estimated_cost.get("memory_mb"), default=0),
    }

    data["risks"] = _coerce_str_list(data.get("risks"))

    return data


def node_understand(state: AgentState, settings: Settings) -> Dict[str, Any]:
    """理解节点处理函数。

    Args:
        state: 当前代理状态。
        settings: 应用配置。

    Returns:
        Dict[str, Any]: 更新后的状态字典。
    """
    understanding = understand_task(state, settings)
    return {"understanding": understanding}


def node_plan(state: AgentState, settings: Settings) -> Dict[str, Any]:
    """计划节点处理函数。

    Args:
        state: 当前代理状态。
        settings: 应用配置。

    Returns:
        Dict[str, Any]: 更新后的状态字典。
    """
    plan = plan_task(state, settings)
    return {"plan": plan}


def node_confirm(state: AgentState) -> Dict[str, Any]:
    """确认节点处理函数。

    Args:
        state: 当前代理状态。

    Returns:
        Dict[str, Any]: 更新后的状态字典，设置状态为需要确认。
    """
    return {"status": "NEEDS_CONFIRMATION"}


def node_apply_feedback(state: AgentState) -> Dict[str, Any]:
    """应用用户反馈节点处理函数。

    Args:
        state: 当前代理状态。

    Returns:
        Dict[str, Any]: 更新后的状态字典，包含更新后的理解报告。
    """
    if not state.get("feedback"):
        if not state.get("patch_understanding"):
            return {}
    understanding = state.get("understanding")
    if not understanding:
        return {}
    updated = understanding.model_dump()
    if state.get("patch_understanding"):
        updated.update(state["patch_understanding"])
    if state.get("feedback"):
        updated.setdefault("assumptions", []).append(f"User feedback: {state['feedback']}")
    return {"understanding": TaskUnderstandingReport(**updated), "plan": None}


def node_execute(state: AgentState, settings: Settings) -> Dict[str, Any]:
    """执行节点处理函数。

    Args:
        state: 当前代理状态。
        settings: 应用配置。

    Returns:
        Dict[str, Any]: 任务执行结果。
    """
    registry = build_registry(settings)
    run_path = init_run(settings.runs_dir, state["run_id"])
    logger = setup_logger("autoplan-agent", log_file=run_path / "logs" / "run.log")
    llm = get_llm(settings)
    result = execute_plan(state, registry, settings, logger, run_path, llm=llm)
    result["understanding"] = state.get("understanding")
    result["plan"] = state.get("plan")
    return result


def node_report(state: AgentState) -> Dict[str, Any]:
    """报告节点处理函数。

    Args:
        state: 当前代理状态。

    Returns:
        Dict[str, Any]: 更新后的状态字典。
    """
    status = state.get("status")
    if status and status != "DONE":
        return {}
    return {"status": "DONE"}


def decide_next(state: AgentState) -> str:
    """根据审批状态决定下一个节点。

    Args:
        state: 当前代理状态。

    Returns:
        str: 下一个节点的名称。
    """
    if state.get("approved"):
        return "execute"
    return "confirm"


def build_graph(settings: Settings):
    """构建工作流图。

    Args:
        settings: 应用配置。

    Returns:
        StateGraph: 编译前的工作流图对象。
    """
    graph = StateGraph(AgentState)
    graph.add_node("understand", lambda s: node_understand(s, settings))
    graph.add_node("apply_feedback", node_apply_feedback)
    graph.add_node("plan", lambda s: node_plan(s, settings))
    graph.add_node("confirm", node_confirm)
    graph.add_node("execute", lambda s: node_execute(s, settings))
    graph.add_node("report", node_report)

    graph.set_entry_point("understand")
    graph.add_edge("understand", "apply_feedback")
    graph.add_edge("apply_feedback", "plan")
    graph.add_conditional_edges("plan", decide_next, {"confirm": "confirm", "execute": "execute"})
    graph.add_edge("confirm", END)
    graph.add_edge("execute", "report")
    graph.add_edge("report", END)

    return graph


def run_graph(input_state: Dict[str, Any], settings: Settings):
    """运行工作流。

    Args:
        input_state: 初始状态字典。
        settings: 应用配置。

    Returns:
        Any: 工作流运行结果。
    """
    run_path = init_run(settings.runs_dir, input_state["run_id"])
    checkpointer = get_checkpointer(run_path)
    graph = build_graph(settings)
    compiled = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": input_state["run_id"]}}
    return compiled.invoke(input_state, config=config)
