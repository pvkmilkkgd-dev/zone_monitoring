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
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'regions' 
                ORDER BY ordinal_position
            """)
        ).all()
        
        print("Структура таблицы regions:")
        for r in result:
            print(f"  {r.column_name}: {r.data_type}")
        
        # Проверяем map_id
        map_id_check = db.execute(
            text("SELECT map_id FROM regions LIMIT 1")
        ).first()
        
        if map_id_check:
            print(f"\nПример map_id: {map_id_check[0]}")
        else:
            print("\nТаблица regions пуста")
            
    finally:
        db.close()


if __name__ == "__main__":
    main()
