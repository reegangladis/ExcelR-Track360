"""
ExcelR Track360 - Error Handling & RFC 7807 Problem Details Specification
Provides consistent, machine-readable error responses across all API endpoints.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class AppException(Exception):
    """Base application exception with RFC 7807 metadata."""
    
    def __init__(
        self,
        title: str,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "ERR_INTERNAL",
        invalid_params: Optional[List[Dict[str, Any]]] = None,
    ):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.invalid_params = invalid_params or []
        super().__init__(detail)


class DatabaseConnectionError(AppException):
    """Raised when the database connection fails or times out."""
    
    def __init__(self, detail: str = "Database connection unavailable"):
        super().__init__(
            title="Database Connection Failure",
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="ERR_DATABASE_UNAVAILABLE",
        )


def create_problem_response(
    request: Request,
    title: str,
    detail: str,
    status_code: int,
    error_code: str,
    invalid_params: Optional[List[Dict[str, Any]]] = None,
) -> JSONResponse:
    """Constructs an RFC 7807 compliant Problem Details JSON response."""
    problem = {
        "type": f"https://errors.track360.excelr.com/{error_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
        "code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if invalid_params:
        problem["invalid_params"] = invalid_params
        
    return JSONResponse(
        status_code=status_code,
        content=problem,
        headers={"Content-Type": "application/problem+json"}
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles domain AppException instances."""
    logger.warning(f"Domain exception on {request.method} {request.url.path}: [{exc.error_code}] {exc.detail}")
    return create_problem_response(
        request=request,
        title=exc.title,
        detail=exc.detail,
        status_code=exc.status_code,
        error_code=exc.error_code,
        invalid_params=exc.invalid_params,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard Starlette / FastAPI HTTPExceptions."""
    code_map = {
        400: "ERR_BAD_REQUEST",
        401: "ERR_UNAUTHORIZED",
        403: "ERR_FORBIDDEN",
        404: "ERR_NOT_FOUND",
        405: "ERR_METHOD_NOT_ALLOWED",
        409: "ERR_CONFLICT",
        422: "ERR_UNPROCESSABLE_ENTITY",
        500: "ERR_INTERNAL_SERVER_ERROR",
        503: "ERR_SERVICE_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, f"ERR_HTTP_{exc.status_code}")
    title = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
    
    return create_problem_response(
        request=request,
        title=title,
        detail=str(exc.detail),
        status_code=exc.status_code,
        error_code=error_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic request validation errors."""
    invalid_params = []
    for error in exc.errors():
        param_path = ".".join(str(loc) for loc in error.get("loc", []))
        invalid_params.append({
            "name": param_path,
            "reason": error.get("msg", "Invalid parameter"),
            "type": error.get("type", "validation_error"),
        })
        
    return create_problem_response(
        request=request,
        title="Request Validation Failed",
        detail="One or more fields in the request body, query, or path are invalid.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="ERR_VALIDATION_FAILED",
        invalid_params=invalid_params,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled runtime exceptions."""
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return create_problem_response(
        request=request,
        title="Internal Server Error",
        detail="An unexpected internal error occurred. Please contact system support.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="ERR_UNEXPECTED_SERVER_ERROR",
    )
