from sqlalchemy.orm import declarative_base

# Base должен быть определен здесь, чтобы избежать циклических зависимостей
# НЕ импортируем модели здесь - это вызывает циклический импорт!
# Модели регистрируются в Base.metadata при импорте через app/models/__init__.py
# Для Alembic импорты моделей находятся в migrations/env.py
Base = declarative_base()

__all__ = ["Base"]
