"""Централизованная обработка исключений."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработка ошибок валидации запросов."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработка ошибок базы данных."""
    # В production не показываем детали ошибки БД
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred. Please contact administrator.",
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Обработка общих исключений."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
        },
    )
