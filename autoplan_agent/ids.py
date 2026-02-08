from datetime import datetime
import secrets


def new_run_id() -> str:
    """生成基于日期时间的 run_id，格式为 run_YYYYMMDD_HHMMSS_xxxx"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(2)
    return f"run_{now}_{suffix}"


def new_step_id() -> str:
    """生成基于日期时间的 step_id，格式为 step_HHMMSS_xxxx"""
    now = datetime.now().strftime("%H%M%S")
    suffix = secrets.token_hex(2)
    return f"step_{now}_{suffix}"

