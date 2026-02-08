"""项目主入口模块。

提供命令行界面，支持启动 API 服务、运行任务、恢复任务执行以及查看生成的报告。
"""

import argparse
import json
from pathlib import Path

import uvicorn

from autoplan_agent.config import Settings
from autoplan_agent.ids import new_run_id
from autoplan_agent.storage.run_store import init_run, save_meta
from autoplan_agent.workflow import run_graph


def cmd_serve(args: argparse.Namespace) -> None:
    """启动 FastAPI 服务。

    Args:
        args: 命令行参数。
    """
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=False)


def cmd_run(args: argparse.Namespace) -> None:
    """运行新任务，支持交互式确认。

    Args:
        args: 命令行参数。
    """
    settings = Settings()
    run_id = new_run_id()
    run_path = init_run(settings.runs_dir, run_id)
    result = run_graph(
        {
            "run_id": run_id,
            "user_task": args.task,
            "approved": False,
            "template_id": args.template_id or "default",
        },
        settings,
    )
    understanding = result.get("understanding")
    plan = result.get("plan")
    if understanding:
        print(json.dumps(understanding.model_dump(), ensure_ascii=False, indent=2))
    if plan:
        print(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2))

    approved = args.auto_approve
    if not approved:
        ans = input("是否确认执行？[y/N]: ").strip().lower()
        approved = ans in {"y", "yes"}

    if not approved:
        feedback = args.feedback or input("请输入修改意见（可留空）: ").strip()
        result = run_graph(
            {
                "run_id": run_id,
                "approved": False,
                "feedback": feedback,
            },
            settings,
        )
        print("已更新计划。请重新运行确认。")
        save_meta(run_path, {"run_id": run_id, "status": result.get("status", "NEEDS_CONFIRMATION")})
        return

    result = run_graph({"run_id": run_id, "approved": True}, settings)
    print(f"执行完成，状态: {result.get('status')}")
    save_meta(run_path, {"run_id": run_id, "status": result.get("status", "DONE")})


def cmd_resume(args: argparse.Namespace) -> None:
    """根据运行 ID 恢复执行。

    Args:
        args: 命令行参数。
    """
    settings = Settings()
    result = run_graph({"run_id": args.run_id, "approved": True}, settings)
    print(f"执行完成，状态: {result.get('status')}")


def cmd_report(args: argparse.Namespace) -> None:
    """获取指定运行 ID 的报告路径。

    Args:
        args: 命令行参数。
    """
    settings = Settings()
    path = Path(settings.runs_dir) / args.run_id / "artifacts" / f"report.{args.fmt}"
    if not path.exists():
        raise SystemExit("报告不存在，请先执行任务。")
    print(str(path))


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Returns:
        argparse.ArgumentParser: 参数解析器对象。
    """
    parser = argparse.ArgumentParser(description="Autoplan Agent - simple main entry")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="Run FastAPI server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    p_run = sub.add_parser("run", help="Run a task with interactive confirmation")
    p_run.add_argument("task", help="User task description")
    p_run.add_argument("--template-id", default="default")
    p_run.add_argument("--auto-approve", action="store_true", help="Skip confirmation and execute directly")
    p_run.add_argument("--feedback", default="")
    p_run.set_defaults(func=cmd_run)

    p_resume = sub.add_parser("resume", help="Resume execution by run_id")
    p_resume.add_argument("run_id")
    p_resume.set_defaults(func=cmd_resume)

    p_report = sub.add_parser("report", help="Get report path by run_id")
    p_report.add_argument("run_id")
    p_report.add_argument("--fmt", default="pdf")
    p_report.set_defaults(func=cmd_report)

    return parser


def main() -> None:
    """程序主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
