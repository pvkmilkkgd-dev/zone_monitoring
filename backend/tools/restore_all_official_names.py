#!/usr/bin/env python
"""Восстановление всех официальных названий регионов."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

# Полный маппинг коротких названий из GeoJSON на официальные названия
# Составлен на основе стандартных официальных названий регионов России
SHORT_TO_OFFICIAL = {
    "Алтай": "Республика Алтай",
    "Бурятия": "Республика Бурятия",
    "Тыва": "Республика Тыва",
    "Тува": "Республика Тыва",
    "Калмыкия": "Республика Калмыкия",
    "Коми": "Республика Коми",
    "Марий Эл": "Республика Марий Эл",
    "Мордовия": "Республика Мордовия",
    "Саха": "Республика Саха (Якутия)",
    "Якутия": "Республика Саха (Якутия)",
    "Северная Осетия": "Республика Северная Осетия - Алания",
    "Татарстан": "Республика Татарстан",
    "Хакасия": "Республика Хакасия",
    "Чечня": "Чеченская Республика",
    "Чувашия": "Чувашская Республика",
    "Крым": "Республика Крым",
    "Адыгея": "Республика Адыгея",
    "Башкортостан": "Республика Башкортостан",
    "Ингушетия": "Республика Ингушетия",
    "Карелия": "Республика Карелия",
    "Удмуртия": "Удмуртская Республика",
    # Края обычно уже имеют правильные названия, но на всякий случай
    # Области тоже обычно правильные
}


def restore_official_names(db: Session):
    """Восстанавливает официальные названия для всех регионов."""
    print("=== Восстановление официальных названий ===\n")
    
    # Получаем все регионы где name = name_original (короткие названия)
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions WHERE name = name_original ORDER BY name")
    ).all()
    
    updated = 0
    not_found = []
    
    for region in regions:
        region_id = region.id
        current_name = region.name  # Это же и name_original
        
        # Ищем официальное название в маппинге
        official_name = SHORT_TO_OFFICIAL.get(current_name)
        
        if official_name:
            try:
                db.execute(
                    text("UPDATE regions SET name = :official_name WHERE id = :region_id"),
                    {"official_name": official_name, "region_id": region_id}
                )
                print(f"  '{current_name}' -> '{official_name}'")
                updated += 1
            except Exception as e:
                print(f"Ошибка при обновлении '{current_name}': {e}")
                db.rollback()
                continue
        else:
            # Если не нашли в маппинге, проверяем, содержит ли название официальные слова
            official_keywords = ["Республика", "Край", "Область", "Автономный", "Округ", "Город"]
            has_official = any(keyword in current_name for keyword in official_keywords)
            
            if not has_official:
                not_found.append(current_name)
    
    db.commit()
    
    print(f"\n=== Результаты ===")
    print(f"Обновлено названий: {updated}")
    
    if not_found:
        print(f"\nНе найдены официальные названия для ({len(not_found)}):")
        for name in sorted(not_found)[:10]:  # Показываем первые 10
            print(f"  - '{name}'")
        if len(not_found) > 10:
            print(f"  ... и еще {len(not_found) - 10}")
    
    # Проверяем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_short_names = db.execute(
        text("SELECT COUNT(*) FROM regions WHERE name = name_original AND name IS NOT NULL")
    ).scalar()
    
    print(f"\nВсего регионов: {total}")
    print(f"Регионов где name = name_original (короткие): {with_short_names}")


def main():
    db = SessionLocal()
    try:
        restore_official_names(db)
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
