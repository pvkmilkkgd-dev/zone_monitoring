#!/usr/bin/env python
"""Восстановление официальных названий регионов в столбце name."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

# Маппинг для восстановления официальных названий
# Если name_original есть, но name неофициальный, восстанавливаем официальное название
OFFICIAL_NAMES_MAP = {
    # Короткие названия -> Официальные названия
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
    "Удмуртия": "Удмуртская Республика",
    "Хакасия": "Республика Хакасия",
    "Чечня": "Чеченская Республика",
    "Чувашия": "Чувашская Республика",
    "Крым": "Республика Крым",
    "Адыгея": "Республика Адыгея",
    "Башкортостан": "Республика Башкортостан",
    "Ингушетия": "Республика Ингушетия",
    "Карелия": "Республика Карелия",
    "Алтайский": "Алтайский край",
    "Краснодарский": "Краснодарский край",
    "Красноярский": "Красноярский край",
    "Пермский": "Пермский край",
    "Приморский": "Приморский край",
    "Ставропольский": "Ставропольский край",
    "Хабаровский": "Хабаровский край",
    "Камчатский": "Камчатский край",
    "Забайкальский": "Забайкальский край",
}


def restore_official_names(db: Session):
    """Восстанавливает официальные названия регионов."""
    print("=== Восстановление официальных названий ===\n")
    
    # Получаем все регионы
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions ORDER BY name")
    ).all()
    
    updated = 0
    skipped = 0
    
    for region in regions:
        region_id = region.id
        current_name = region.name
        name_original = region.name_original
        
        # Определяем, нужно ли обновлять название
        official_name = None
        
        # Если есть name_original, проверяем, соответствует ли текущий name официальному
        if name_original:
            # Если name_original совпадает с коротким названием, восстанавливаем официальное
            if current_name == name_original and name_original in OFFICIAL_NAMES_MAP:
                official_name = OFFICIAL_NAMES_MAP[name_original]
            # Если name уже официальный, но есть более точное соответствие
            elif current_name in OFFICIAL_NAMES_MAP.values():
                # Проверяем, правильно ли сопоставлен
                if name_original in OFFICIAL_NAMES_MAP and current_name != OFFICIAL_NAMES_MAP[name_original]:
                    official_name = OFFICIAL_NAMES_MAP[name_original]
        
        # Если нашли официальное название, отличное от текущего
        if official_name and official_name != current_name:
            try:
                db.execute(
                    text("UPDATE regions SET name = :official_name WHERE id = :region_id"),
                    {"official_name": official_name, "region_id": region_id}
                )
                print(f"  '{current_name}' -> '{official_name}'")
                updated += 1
            except Exception as e:
                print(f"Ошибка при обновлении региона '{current_name}': {e}")
                db.rollback()
                continue
        else:
            skipped += 1
    
    db.commit()
    print(f"\n=== Результаты ===")
    print(f"Обновлено названий: {updated}")
    print(f"Оставлено без изменений: {skipped}")
    
    # Показываем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    print(f"\nВсего регионов в БД: {total}")


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
