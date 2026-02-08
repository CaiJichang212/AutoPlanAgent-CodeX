"""检查点存储模块。

该模块提供基于 SQLite 的 LangGraph 检查点保存器。
"""

from pathlib import Path
import sqlite3


def get_checkpointer(run_path: Path):
    """获取检查点保存器实例。

    Args:
        run_path: 运行任务的存储目录。

    Returns:
        SqliteSaver: LangGraph 的 SQLite 检查点保存器。

    Raises:
        RuntimeError: 如果未安装 langgraph-checkpoint-sqlite。
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("langgraph-checkpoint-sqlite is required for checkpointing.") from exc
    checkpoint_path = run_path / "checkpoint.sqlite"
    conn = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    return SqliteSaver(conn)
