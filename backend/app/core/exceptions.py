"""Централизованная обработка исключений."""
import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


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
    settings = get_settings()
    
    # Логируем ошибку для администратора
    error_msg = str(exc)
    logger.error(
        f"Database error on {request.method} {request.url.path}: {error_msg}",
        exc_info=True,
    )
    
    # Всегда показываем детали ошибки (для диагностики)
    # В production можно вернуть общее сообщение, но пока оставляем детали
    detail = f"Ошибка базы данных: {error_msg}"
    
    # Проверяем типичные ошибки и даем более понятные сообщения
    if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
        detail = f"Ошибка структуры базы данных: {error_msg}. Возможно, нужно применить миграции: alembic upgrade head"
    elif "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
        detail = f"Таблица не найдена: {error_msg}. Возможно, нужно применить миграции: alembic upgrade head"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Обработка общих исключений."""
    settings = get_settings()
    
    # Логируем ошибку
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    
    # В режиме разработки показываем детали ошибки
    if settings.DEBUG:
        detail = f"Внутренняя ошибка сервера: {str(exc)}"
    else:
        detail = "Произошла внутренняя ошибка сервера. Обратитесь к администратору."
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
        },
    )
