"""CLI 命令行界面模块。

该模块提供基于 Typer 的命令行工具，用于启动 API 服务和运行任务。
"""

import json
from pathlib import Path

import typer
import uvicorn

from autoplan_agent.config import Settings
from autoplan_agent.ids import new_run_id
from autoplan_agent.storage.run_store import init_run, save_meta
from autoplan_agent.workflow import run_graph

app = typer.Typer(help="Autoplan Agent CLI")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000):
    """启动 API 服务。

    Args:
        host: 绑定地址。
        port: 监听端口。
    """
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


@app.command()
def run(task: str):
    """运行数据分析任务。

    Args:
        task: 任务描述字符串。
    """
    settings = Settings()
    run_id = new_run_id()
    run_path = init_run(settings.runs_dir, run_id)
    result = run_graph({"run_id": run_id, "user_task": task, "approved": False}, settings)
    typer.echo(json.dumps(result.get("understanding").model_dump(), ensure_ascii=False, indent=2))
    typer.echo(json.dumps(result.get("plan").model_dump(), ensure_ascii=False, indent=2))

    approved = typer.confirm("是否确认执行？", default=False)
    if not approved:
        feedback = typer.prompt("请输入修改意见（可留空）", default="")
        result = run_graph({"run_id": run_id, "approved": False, "feedback": feedback}, settings)
        typer.echo("已更新计划。请重新运行确认。")
        save_meta(run_path, {"run_id": run_id, "status": result.get("status", "NEEDS_CONFIRMATION")})
        return

    result = run_graph({"run_id": run_id, "approved": True}, settings)
    typer.echo(f"执行完成，状态: {result.get('status')}")
    save_meta(run_path, {"run_id": run_id, "status": result.get("status", "DONE")})


@app.command()
def resume(run_id: str):
    """恢复并继续执行之前的任务。

    Args:
        run_id: 运行 ID。
    """
    settings = Settings()
    result = run_graph({"run_id": run_id, "approved": True}, settings)
    typer.echo(f"执行完成，状态: {result.get('status')}")


@app.command()
def report(run_id: str, fmt: str = "pdf"):
    """查看生成的任务报告路径。

    Args:
        run_id: 运行 ID。
        fmt: 报告格式，默认为 pdf。
    """
    settings = Settings()
    path = Path(settings.runs_dir) / run_id / "artifacts" / f"report.{fmt}"
    if not path.exists():
        typer.echo("报告不存在，请先执行任务。")
        raise typer.Exit(code=1)
    typer.echo(str(path))

