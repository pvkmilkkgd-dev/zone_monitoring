#!/usr/bin/env python
"""Проверка структуры таблицы regions."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'regions' ORDER BY ordinal_position")
        ).all()
        
        print("=== Структура таблицы regions ===")
        for row in result:
            print(f"  - {row.column_name}: {row.data_type}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
