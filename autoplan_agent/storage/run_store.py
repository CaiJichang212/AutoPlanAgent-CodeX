import json
from pathlib import Path
from typing import Any


def run_dir(base_dir: Path, run_id: str) -> Path:
    return base_dir / run_id


def init_run(base_dir: Path, run_id: str) -> Path:
    run_path = run_dir(base_dir, run_id)
    (run_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_path / "logs").mkdir(parents=True, exist_ok=True)
    return run_path


def save_meta(run_path: Path, meta: dict[str, Any]) -> None:
    meta_path = run_path / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(run_path: Path) -> dict[str, Any]:
    meta_path = run_path / "meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def update_status(run_path: Path, status: str) -> None:
    meta = load_meta(run_path)
    meta["status"] = status
    save_meta(run_path, meta)

