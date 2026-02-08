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
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


@app.command()
def run(task: str):
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
    settings = Settings()
    result = run_graph({"run_id": run_id, "approved": True}, settings)
    typer.echo(f"执行完成，状态: {result.get('status')}")


@app.command()
def report(run_id: str, fmt: str = "pdf"):
    settings = Settings()
    path = Path(settings.runs_dir) / run_id / "artifacts" / f"report.{fmt}"
    if not path.exists():
        typer.echo("报告不存在，请先执行任务。")
        raise typer.Exit(code=1)
    typer.echo(str(path))

