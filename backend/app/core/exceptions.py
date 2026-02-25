"""
全局异常处理模块 (Global Exception Handling Module)

定义业务异常类和 FastAPI 全局异常处理器，提供统一的错误响应格式。
所有未捕获的异常都会被转换为结构化 JSON 响应，避免裸 500 错误。

Defines business exception classes and FastAPI global exception handlers,
providing a unified error response format. All uncaught exceptions are converted
to structured JSON responses, preventing raw 500 errors.
"""
import logging
import traceback
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ============================================================
# 业务异常类 (Business Exception Classes)
# ============================================================

class BusinessError(Exception):
    """业务异常基类 (Base Business Exception)"""
    status_code: int = 400
    error: str = "business_error"

    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(BusinessError):
    """资源不存在 (Resource Not Found)"""
    status_code = 404
    error = "not_found"


class PermissionDeniedError(BusinessError):
    """权限不足 (Permission Denied)"""
    status_code = 403
    error = "permission_denied"


class ValidationError(BusinessError):
    """数据校验失败 (Validation Error)"""
    status_code = 422
    error = "validation_error"


class ConflictError(BusinessError):
    """资源冲突 (Resource Conflict)"""
    status_code = 409
    error = "conflict"


# ============================================================
# 全局异常处理器注册 (Global Exception Handler Registration)
# ============================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器到 FastAPI 应用 (Register global exception handlers to FastAPI app)

    处理优先级：
    1. BusinessError 子类 → 对应 HTTP 状态码 + 结构化响应
    2. HTTPException → 保持原样，包装为统一格式
    3. Exception → 500 + 完整 traceback 日志
    """

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error,
                "message": exc.message,
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": str(exc.detail),
                "detail": None,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # 记录完整 traceback 用于调试 (Log full traceback for debugging)
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            str(exc),
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "服务器内部错误，请稍后重试 (Internal server error, please try again later)",
                "detail": None,
                "status_code": 500,
            },
        )
