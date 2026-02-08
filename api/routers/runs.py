"""运行管理路由模块。

该模块提供任务运行的创建、确认、执行和状态查询等接口。
"""

from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse

from autoplan_agent.config import Settings
from autoplan_agent.ids import new_run_id
from autoplan_agent.schemas.api import (
    RunCreateRequest,
    RunCreateResponse,
    RunConfirmRequest,
    RunStatusResponse,
)
from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.schemas.plan import ExecutionPlan
from autoplan_agent.storage.run_store import init_run, save_meta, load_meta
from autoplan_agent.workflow import run_graph

router = APIRouter()


def get_settings() -> Settings:
    """获取应用配置。

    Returns:
        Settings: 应用配置对象。
    """
    return Settings()


def require_api_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """验证 API Key。

    Args:
        settings: 应用配置。
        x_api_key: 请求头中的 API Key。

    Raises:
        HTTPException: 如果 API Key 无效。
    """
    if settings.agent_api_key:
        if not x_api_key or x_api_key != settings.agent_api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/runs", response_model=RunCreateResponse, dependencies=[Depends(require_api_key)])
def create_run(payload: RunCreateRequest, settings: Settings = Depends(get_settings)):
    """创建新的任务运行。

    Args:
        payload: 创建请求负载。
        settings: 应用配置。

    Returns:
        RunCreateResponse: 创建成功的响应。
    """
    run_id = new_run_id()
    run_path = init_run(settings.runs_dir, run_id)
    result = run_graph(
        {
            "run_id": run_id,
            "user_task": payload.user_task,
            "approved": False,
            "template_id": payload.template_id or "default",
        },
        settings,
    )
    meta = {
        "run_id": run_id,
        "status": result.get("status", "NEEDS_CONFIRMATION"),
        "understanding": result.get("understanding").model_dump() if result.get("understanding") else None,
        "plan": result.get("plan").model_dump() if result.get("plan") else None,
    }
    save_meta(run_path, meta)
    return RunCreateResponse(
        run_id=run_id,
        status=meta["status"],
        understanding=result.get("understanding"),
        plan=result.get("plan"),
        open_questions=(result.get("understanding").open_questions if result.get("understanding") else []),
    )


@router.post("/runs/{run_id}/confirm", response_model=RunStatusResponse, dependencies=[Depends(require_api_key)])
def confirm_run(run_id: str, payload: RunConfirmRequest, settings: Settings = Depends(get_settings)):
    """确认或提供任务运行的反馈。

    Args:
        run_id: 运行 ID。
        payload: 确认请求负载。
        settings: 应用配置。

    Returns:
        RunStatusResponse: 运行状态响应。
    """
    run_path = init_run(settings.runs_dir, run_id)
    result = run_graph(
        {
            "run_id": run_id,
            "approved": payload.approved,
            "feedback": payload.feedback,
            "patch_understanding": payload.patch_understanding,
        },
        settings,
    )
    meta = {
        "run_id": run_id,
        "status": result.get("status", "NEEDS_CONFIRMATION"),
        "understanding": result.get("understanding").model_dump() if result.get("understanding") else None,
        "plan": result.get("plan").model_dump() if result.get("plan") else None,
    }
    save_meta(run_path, meta)
    return RunStatusResponse(
        run_id=run_id,
        status=meta["status"],
        understanding=result.get("understanding"),
        plan=result.get("plan"),
        artifacts=result.get("artifacts", []),
        message=result.get("message"),
    )


@router.post("/runs/{run_id}/execute", response_model=RunStatusResponse, dependencies=[Depends(require_api_key)])
def execute_run(run_id: str, settings: Settings = Depends(get_settings)):
    """直接执行任务运行。

    Args:
        run_id: 运行 ID。
        settings: 应用配置。

    Returns:
        RunStatusResponse: 运行状态响应。
    """
    run_path = init_run(settings.runs_dir, run_id)
    result = run_graph({"run_id": run_id, "approved": True}, settings)
    meta = {
        "run_id": run_id,
        "status": result.get("status", "NEEDS_CONFIRMATION"),
        "understanding": result.get("understanding").model_dump() if result.get("understanding") else None,
        "plan": result.get("plan").model_dump() if result.get("plan") else None,
    }
    save_meta(run_path, meta)
    return RunStatusResponse(
        run_id=run_id,
        status=meta["status"],
        understanding=result.get("understanding"),
        plan=result.get("plan"),
        artifacts=result.get("artifacts", []),
        message=result.get("message"),
    )


@router.get("/runs/{run_id}", response_model=RunStatusResponse, dependencies=[Depends(require_api_key)])
def get_run(run_id: str, settings: Settings = Depends(get_settings)):
    """获取任务运行的状态。

    Args:
        run_id: 运行 ID。
        settings: 应用配置。

    Returns:
        RunStatusResponse: 运行状态响应。
    """
    run_path = Path(settings.runs_dir) / run_id
    meta = load_meta(run_path)
    understanding = TaskUnderstandingReport(**meta["understanding"]) if meta.get("understanding") else None
    plan = ExecutionPlan(**meta["plan"]) if meta.get("plan") else None
    return RunStatusResponse(
        run_id=run_id,
        status=meta.get("status", "UNKNOWN"),
        understanding=understanding,
        plan=plan,
        artifacts=[],
        message=None,
    )


@router.get("/runs/{run_id}/report", dependencies=[Depends(require_api_key)])
def get_report(run_id: str, format: str = "pdf", settings: Settings = Depends(get_settings)):
    """获取任务运行生成的报告。

    Args:
        run_id: 运行 ID。
        format: 报告格式（pdf 或 html）。
        settings: 应用配置。

    Returns:
        FileResponse: 报告文件响应。

    Raises:
        HTTPException: 如果报告不存在。
    """
    report_path = Path(settings.runs_dir) / run_id / "artifacts" / f"report.{format}"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path)
