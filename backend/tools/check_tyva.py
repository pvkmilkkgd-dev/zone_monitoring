#!/usr/bin/env python
"""Проверка регионов Тыва."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        # Ищем все регионы с Тыва/Тува
        result = db.execute(
            text("SELECT id, name, name_original FROM regions WHERE name LIKE '%Тыва%' OR name LIKE '%Тува%'")
        ).all()
        
        print("Регионы с Тыва/Тува в БД:")
        for row in result:
            print(f"  ID: {row.id}")
            print(f"  name: {row.name}")
            print(f"  name_original: {row.name_original}")
            print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
