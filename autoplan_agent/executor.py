from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from autoplan_agent.schemas.artifacts import Artifact, StepResult
from autoplan_agent.schemas.plan import ExecutionPlan, PlanStep
from autoplan_agent.tools.registry import ToolRegistry, ToolContext
from autoplan_agent.llm.runtime import call_llm, parse_json
from autoplan_agent.llm.prompts import get_prompt_env
from autoplan_agent.tools.mysql.client import load_mysql_schema_hint


def _last_dataset(artifacts: List[Artifact]) -> Artifact | None:
    for art in reversed(artifacts):
        if art.type == "dataset":
            return art
    return None


def _build_report_inputs(state: Dict[str, Any], artifacts: List[Artifact], llm: Any = None) -> Dict[str, Any]:
    understanding = state.get("understanding")
    
    # Collect findings from artifacts
    context_parts = []
    if understanding:
        context_parts.append(f"Analysis Goal: {understanding.analysis_goal}")
    
    for art in artifacts:
        if art.preview:
            context_parts.append(f"Artifact: {art.artifact_id} ({art.type})")
            context_parts.append(f"Description: {art.description}")
            context_parts.append(f"Preview Data: {art.preview}")
            context_parts.append("-" * 20)
    
    context_str = "\n".join(context_parts)
    
    if llm:
        system_prompt = "你是一位资深的金融数据分析师。请将提供的数据分析结果综合成一份详尽的报告。使用专业、准确的中文。确保每个 JSON 字段都是单个字符串，而不是列表。"
        user_prompt = f"""请根据以下分析结果生成一份详细的报告。
结果：
{context_str}

请以 JSON 格式提供以下字段：
- summary: 对分析结果的简明摘要。
- findings: 对财务表现、市场表现及观察到的趋势的详细分析。
- recommendations: 基于数据的具体投资或业务建议。
- data_sources: 描述数据来源。
- data_quality: 对数据完整性和质量的评价。
- methods: 描述所使用的分析方法（如 EDA、异常检测等）。
- appendix: 任何额外的备注或参考资料。
"""
        try:
            from autoplan_agent.llm.runtime import parse_json
            content = call_llm(llm, system_prompt, user_prompt)
            report_data = parse_json(content)
            if report_data:
                # Ensure all expected fields are strings, joining lists if necessary
                for field in ["summary", "findings", "recommendations", "data_sources", "data_quality", "methods", "appendix"]:
                    val = report_data.get(field, "")
                    if isinstance(val, list):
                        report_data[field] = "\n".join(str(v) for v in val)
                    else:
                        report_data[field] = str(val)
                
                report_data["understanding"] = understanding
                return report_data
        except Exception as e:
            print(f"Error synthesizing report with LLM: {e}")

    # Fallback to boilerplate if LLM fails or is not provided
    summary = "自动生成的分析报告。"
    findings = "基于已执行步骤的结果生成。"
    recommendations = "请结合业务场景进一步评估。"
    data_sources = "MySQL 查询与本地清洗数据。"
    data_quality = "已执行基础清洗与缺失值统计。"
    methods = "EDA + 统计分析 + 异常检测 + 可视化。"
    appendix = "详见 artifacts 列表。"
    return {
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "data_sources": data_sources,
        "data_quality": data_quality,
        "methods": methods,
        "appendix": appendix,
        "understanding": understanding,
    }


def _repair_step(
    step: PlanStep,
    error_message: str,
    state: Dict[str, Any],
    settings,
    llm: Any,
) -> Dict[str, Any]:
    if not llm:
        return {}
    
    env = get_prompt_env(Path(__file__).parent / "llm" / "prompts")
    schema_hint = ""
    if step.tool.startswith("mysql"):
        relevant_tables = []
        understanding = state.get("understanding")
        if understanding:
            u_dict = understanding.model_dump()
            relevant_tables = u_dict.get("data_scope", {}).get("tables", [])
        schema_hint = load_mysql_schema_hint(settings, relevant_tables=relevant_tables) or ""

    prompt = env.get_template("repair.j2").render(
        error_message=error_message,
        step_json=step.model_dump_json(),
        schema_hint=schema_hint, # Although repair.j2 might not use it yet, it's good to have
    )
    
    content = call_llm(llm, "You are a repair assistant.", prompt)
    new_inputs = parse_json(content)
    
    # If the LLM returned the whole step or a nested inputs object, extract the inputs
    if isinstance(new_inputs, dict):
        if "inputs" in new_inputs and isinstance(new_inputs["inputs"], dict):
            new_inputs = new_inputs["inputs"]
        elif "step" in new_inputs and isinstance(new_inputs["step"], dict) and "inputs" in new_inputs["step"]:
            new_inputs = new_inputs["step"]["inputs"]
            
    return new_inputs


def execute_plan(
    state: Dict[str, Any],
    registry: ToolRegistry,
    settings,
    logger,
    run_path: Path,
    llm: Any = None,
) -> Dict[str, Any]:
    plan: ExecutionPlan = state["plan"]
    artifacts: List[Artifact] = state.get("artifacts", [])
    completed: set[str] = set()

    for step in plan.steps:
        if step.step_id in completed:
            continue

        tool = registry.get(step.tool)
        inputs = dict(step.inputs)

        # Auto-repair missing SQL
        if step.tool in {"mysql.query", "mysql.explain"} and not inputs.get("sql"):
            logger.info("Step %s missing SQL, attempting auto-repair", step.name)
            repaired_inputs = _repair_step(step, "Missing SQL input", state, settings, llm)
            if repaired_inputs and repaired_inputs.get("sql"):
                inputs.update(repaired_inputs)
                step.inputs.update(repaired_inputs)
            else:
                return {
                    "status": "NEEDS_CONFIRMATION",
                    "message": f"Step {step.name} missing SQL input and auto-repair failed.",
                }

        if "dataset_path" in tool.input_model.model_fields and not inputs.get("dataset_path"):
            last_dataset = _last_dataset(artifacts)
            if not last_dataset:
                return {
                    "status": "NEEDS_CONFIRMATION",
                    "message": f"Step {step.name} requires dataset but none available.",
                }
            inputs["dataset_path"] = last_dataset.path

        if step.tool == "report.generate":
            inputs = _build_report_inputs(state, artifacts, llm=llm)

        current_inputs = inputs
        logger.info("Executing step %s (%s) with inputs: %s", step.step_id, step.tool, current_inputs)
        
        # Max attempts for this step (initial + auto-repairs)
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            try:
                # Pre-execution validation
                try:
                    tool.input_model(**current_inputs)
                except Exception as val_err:
                    logger.warning("Input validation failed for step %s: %s. Attempting to fix inputs.", step.step_id, val_err)
                    if "dataset_path" in tool.input_model.model_fields and not current_inputs.get("dataset_path"):
                        last_dataset = _last_dataset(artifacts)
                        if last_dataset:
                            current_inputs["dataset_path"] = last_dataset.path
                    
                    # Try validating again after injection
                    try:
                        tool.input_model(**current_inputs)
                    except Exception:
                        # If still failing, trigger repair early
                        repaired_inputs = _repair_step(step, f"Input validation failed: {val_err}", state, settings, llm)
                        if isinstance(repaired_inputs, dict):
                            current_inputs = repaired_inputs
                            continue
                
                result: StepResult = registry.run(step.tool, current_inputs, ToolContext(
                    run_id=state["run_id"],
                    run_dir=str(run_path),
                    settings=settings,
                    logger=logger,
                    state=state,
                ))
                
                if result.success:
                    artifacts.extend(result.artifacts)
                    completed.add(step.step_id)
                    break # Step succeeded
                
                # Step failed but success=False was returned
                logger.error("Step %s failed (attempt %d/%d): %s", step.step_id, attempt, max_attempts, result.message)
                
                if attempt < max_attempts:
                    logger.info("Attempting auto-repair for step %s", step.step_id)
                    repaired_inputs = _repair_step(step, result.message, state, settings, llm)
                    if isinstance(repaired_inputs, dict):
                        current_inputs = repaired_inputs
                        # Re-inject dataset_path if missing
                        if "dataset_path" in tool.input_model.model_fields and not current_inputs.get("dataset_path"):
                            last_dataset = _last_dataset(artifacts)
                            if last_dataset:
                                current_inputs["dataset_path"] = last_dataset.path
                        continue
                
                # If we reach here, we've exhausted attempts or repair failed
                return {"status": "NEEDS_CONFIRMATION", "message": result.message}

            except Exception as exc:
                logger.exception("Step %s raised exception (attempt %d/%d): %s", step.step_id, attempt, max_attempts, exc)
                
                if attempt < max_attempts:
                    logger.info("Attempting auto-repair after exception for step %s", step.step_id)
                    repaired_inputs = _repair_step(step, str(exc), state, settings, llm)
                    if isinstance(repaired_inputs, dict):
                        current_inputs = repaired_inputs
                        # Re-inject dataset_path if missing
                        if "dataset_path" in tool.input_model.model_fields and not current_inputs.get("dataset_path"):
                            last_dataset = _last_dataset(artifacts)
                            if last_dataset:
                                current_inputs["dataset_path"] = last_dataset.path
                        continue
                
                return {
                    "status": "NEEDS_CONFIRMATION",
                    "message": f"Step {step.name} failed with exception: {exc}",
                }
    
    return {
        "status": "DONE",
        "artifacts": artifacts,
        "message": f"Completed at {datetime.utcnow().isoformat()}",
    }
