"""
资料服务 - FastAPI 应用入口

轻量示例微服务：
- 内存存储头像/部门/岗位（无数据库依赖）
- 通过 HTTP 调用 user-service 获取用户基本信息，合并后返回
- user-service 故障时接口降级，不把整页失败透传给前端
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import demo, health, profiles
from app.services.demo_faults import demo_faults

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)),
)
logger = structlog.get_logger(__name__)


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: dict[str, Any] | None = None,
):
    """构造与 user-service 一致的统一错误响应"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "error_code": error_code,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        },
    )


def _http_status_to_error_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "HTTP_ERROR")


app = FastAPI(
    title="资料服务 API",
    description="""
## 资料服务（服务间调用示例）

- 维护用户扩展资料：头像、部门、岗位（内存存储）
- 处理请求时通过 HTTP 调用 **user-service** 获取用户基本信息并合并返回
- user-service 故障时**降级**：仍返回资料数据并标记 `degraded=true`

### 演示降级
使用 `/api/v1/profiles/demo/faults/*` 开关模拟 user-service 故障或本服务故障。
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        status_code=422,
        message="请求参数校验失败",
        error_code="VALIDATION_ERROR",
        details={"errors": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=_http_status_to_error_code(exc.status_code),
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=_http_status_to_error_code(exc.status_code),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("未处理的异常", error=str(exc), exc_info=True)
    return _error_response(
        status_code=500,
        message="服务器内部错误",
        error_code="INTERNAL_ERROR",
    )


# 演示用：self_fail 开启时，资料业务接口直接返回 503
# 故障管理接口本身豁免，否则开关开启后将无法通过接口关闭
@app.middleware("http")
async def demo_self_fault_middleware(request: Request, call_next):
    path = request.url.path
    if demo_faults.self_fail and path.startswith("/api/v1/profiles") and not path.startswith("/api/v1/profiles/demo"):
        return _error_response(
            status_code=503,
            message="资料服务暂时不可用（演示故障）",
            error_code="SERVICE_UNAVAILABLE",
        )
    return await call_next(request)


# 请求 ID 中间件
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        http_method=request.method,
        http_path=request.url.path,
    )
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        structlog.contextvars.clear_contextvars()


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router, tags=["健康检查"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["资料"])
app.include_router(demo.router, prefix="/api/v1/profiles", tags=["演示故障注入"])


@app.get("/", summary="服务信息")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "upstream": {
            "user_service": settings.USER_SERVICE_URL,
        },
        "timestamp": datetime.now().isoformat(),
        "docs_url": "/docs",
    }
