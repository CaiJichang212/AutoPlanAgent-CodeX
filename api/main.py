"""API 入口模块。

该模块初始化 FastAPI 应用并包含所有路由。
"""

from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.runs import router as runs_router

app = FastAPI(title="Autoplan Agent API", version="0.1.0")

app.include_router(health_router)
app.include_router(runs_router, prefix="/v1")

