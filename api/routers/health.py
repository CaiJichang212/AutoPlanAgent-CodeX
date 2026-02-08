"""健康检查路由模块。

该模块提供 API 的健康检查接口。
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def health():
    """执行健康检查。

    Returns:
        dict: 包含状态信息的字典，例如 {"status": "ok"}。
    """
    return {"status": "ok"}
