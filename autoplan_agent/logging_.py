"""日志管理模块。

该模块提供配置标准日志记录器和记录 JSONL 格式日志的功能。
"""

import json
import logging
from pathlib import Path
from typing import Any


def setup_logger(name: str, log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """配置并返回一个日志记录器。

    Args:
        name: 日志记录器名称。
        log_file: 可选的日志文件路径。
        level: 日志级别，默认为 logging.INFO。

    Returns:
        logging.Logger: 配置好的日志记录器对象。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_jsonl(log_file: Path, payload: dict[str, Any]) -> None:
    """将字典以 JSONL 格式追加到日志文件中。

    Args:
        log_file: 日志文件路径。
        payload: 要记录的字典数据。
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

