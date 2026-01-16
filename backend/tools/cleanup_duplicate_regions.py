#!/usr/bin/env python
"""Удаление ошибочно добавленных регионов без name_original."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def cleanup_duplicate_regions(db: Session):
    """Удаляет регионы без name_original, которые были добавлены недавно."""
    print("=== Удаление ошибочно добавленных регионов ===\n")
    
    # Находим регионы без name_original
    result = db.execute(
        text(
            """
            SELECT id, name, created_at
            FROM regions
            WHERE name_original IS NULL
            ORDER BY created_at DESC
            """
        )
    ).all()
    
    print(f"Найдено регионов без name_original: {len(result)}")
    
    if result:
        print("\nРегионы для удаления:")
        for row in result:
            print(f"  - {row.name} (ID: {row.id}, создан: {row.created_at})")
        
        # Удаляем эти регионы (те, что были созданы недавно и не имеют name_original)
        # Удаляем только те, что были созданы сегодня (2026-01-09)
        deleted = db.execute(
            text(
                """
                DELETE FROM regions
                WHERE name_original IS NULL
                AND created_at >= '2026-01-09 00:00:00'
                """
            )
        ).rowcount
        
        db.commit()
        print(f"\nУдалено регионов: {deleted}")
    else:
        print("Регионов для удаления не найдено")
    
    # Проверяем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_original = db.execute(text("SELECT COUNT(*) FROM regions WHERE name_original IS NOT NULL")).scalar()
    without_original = db.execute(text("SELECT COUNT(*) FROM regions WHERE name_original IS NULL")).scalar()
    
    print(f"\n=== Финальное состояние ===")
    print(f"Всего регионов в БД: {total}")
    print(f"Регионов с name_original: {with_original}")
    print(f"Регионов без name_original: {without_original}")


def main():
    db = SessionLocal()
    try:
        cleanup_duplicate_regions(db)
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
