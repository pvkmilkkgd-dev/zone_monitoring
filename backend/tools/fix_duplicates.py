#!/usr/bin/env python
"""Удаление дубликатов регионов с одинаковым name_original."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def fix_duplicates(db: Session):
    """Находит и удаляет дубликаты регионов с одинаковым name_original."""
    print("=== Поиск и удаление дубликатов ===\n")
    
    # Находим регионы с одинаковым name_original
    duplicates = db.execute(
        text(
            """
            SELECT name_original, COUNT(*) as cnt, array_agg(id ORDER BY name) as ids, array_agg(name ORDER BY name) as names
            FROM regions
            WHERE name_original IS NOT NULL
            GROUP BY name_original
            HAVING COUNT(*) > 1
            ORDER BY name_original
            """
        )
    ).all()
    
    if not duplicates:
        print("Дубликатов не найдено")
        return
    
    print(f"Найдено дубликатов: {len(duplicates)}")
    
    deleted_count = 0
    
    for dup in duplicates:
        original_name = dup.name_original
        ids = dup.ids
        names = dup.names
        
        print(f"\nname_original: '{original_name}'")
        print(f"  Регионы: {list(names)}")
        
        # Выбираем регион с более полным официальным названием
        # (который длиннее или содержит "Республика", "Край", "Область")
        keep_id = None
        keep_name = None
        delete_ids = []
        
        for i, name in enumerate(names):
            # Предпочитаем регионы с полными названиями
            if any(word in name for word in ["Республика", "Край", "Область", "Автономный"]):
                if keep_id is None or len(name) > len(keep_name):
                    # Если уже есть выбранный, добавляем его в удаление
                    if keep_id:
                        delete_ids.append(keep_id)
                    keep_id = ids[i]
                    keep_name = name
                else:
                    delete_ids.append(ids[i])
            else:
                # Короткие названия добавляем в удаление
                delete_ids.append(ids[i])
        
        # Если не нашли регион с полным названием, оставляем первый
        if keep_id is None:
            keep_id = ids[0]
            keep_name = names[0]
            delete_ids = ids[1:]
        
        print(f"  Оставляем: '{keep_name}' (ID: {keep_id})")
        print(f"  Удаляем: {len(delete_ids)} регионов")
        
        # Удаляем дубликаты
        for delete_id in delete_ids:
            try:
                db.execute(
                    text("DELETE FROM regions WHERE id = :region_id"),
                    {"region_id": delete_id}
                )
                deleted_count += 1
            except Exception as e:
                print(f"    Ошибка при удалении ID {delete_id}: {e}")
                db.rollback()
                continue
    
    db.commit()
    print(f"\n=== Результаты ===")
    print(f"Удалено дубликатов: {deleted_count}")
    
    # Проверяем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_original = db.execute(text("SELECT COUNT(*) FROM regions WHERE name_original IS NOT NULL")).scalar()
    print(f"\nВсего регионов в БД: {total}")
    print(f"Регионов с name_original: {with_original}")


def main():
    db = SessionLocal()
    try:
        fix_duplicates(db)
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
