"""ID 生成模块。

该模块提供生成运行 ID 和步骤 ID 的工具函数。
"""

from datetime import datetime
import secrets


def new_run_id() -> str:
    """生成基于日期时间的运行 ID。

    格式为 run_YYYYMMDD_HHMMSS_xxxx。

    Returns:
        str: 生成的运行 ID。
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(2)
    return f"run_{now}_{suffix}"


def new_step_id() -> str:
    """生成基于日期时间的步骤 ID。

    格式为 step_HHMMSS_xxxx。

    Returns:
        str: 生成的步骤 ID。
    """
    now = datetime.now().strftime("%H%M%S")
    suffix = secrets.token_hex(2)
    return f"step_{now}_{suffix}"

