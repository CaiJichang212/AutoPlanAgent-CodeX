from pathlib import Path
import sqlite3


def get_checkpointer(run_path: Path):
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("langgraph-checkpoint-sqlite is required for checkpointing.") from exc
    checkpoint_path = run_path / "checkpoint.sqlite"
    conn = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    return SqliteSaver(conn)
