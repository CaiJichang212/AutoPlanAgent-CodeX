"""运行数据存储模块。

该模块负责管理运行任务的文件系统存储，包括目录初始化、元数据保存与加载。
"""

import json
from pathlib import Path
from typing import Any


def run_dir(base_dir: Path, run_id: str) -> Path:
    """获取运行任务的目录路径。

    Args:
        base_dir: 基础目录。
        run_id: 运行 ID。

    Returns:
        Path: 运行任务的完整路径。
    """
    return base_dir / run_id


def init_run(base_dir: Path, run_id: str) -> Path:
    """初始化运行任务目录。

    创建 artifacts 和 logs 子目录。

    Args:
        base_dir: 基础目录。
        run_id: 运行 ID。

    Returns:
        Path: 初始化后的运行任务目录路径。
    """
    run_path = run_dir(base_dir, run_id)
    (run_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_path / "logs").mkdir(parents=True, exist_ok=True)
    return run_path


def save_meta(run_path: Path, meta: dict[str, Any]) -> None:
    """保存运行元数据。

    Args:
        run_path: 运行任务目录。
        meta: 待保存的元数据字典。
    """
    meta_path = run_path / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(run_path: Path) -> dict[str, Any]:
    """加载运行元数据。

    Args:
        run_path: 运行任务目录。

    Returns:
        dict[str, Any]: 元数据字典，如果文件不存在则返回空字典。
    """
    meta_path = run_path / "meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def update_status(run_path: Path, status: str) -> None:
    """更新运行状态。

    Args:
        run_path: 运行任务目录。
        status: 新的状态字符串。
    """
    meta = load_meta(run_path)
    meta["status"] = status
    save_meta(run_path, meta)

