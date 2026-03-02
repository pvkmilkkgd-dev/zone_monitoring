"""
Объединение Торжка: удалить «городской округ город Торжок» (объединён с Торжокским МО).
Закон Тверской области от 08.12.2025 № 65-ЗО.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Тверская область"
OLD_NAME = "городской округ город Торжок"
NEW_NAME = "Торжокский муниципальный округ"


def main():
    print(f"Объединение Торжка в {REGION_NAME}")
    print("=" * 60)
    print(f"Удаляем: «{OLD_NAME}»")
    print(f"Остаётся: «{NEW_NAME}»")
    print("Закон Тверской области от 08.12.2025 № 65-ЗО")
    print("=" * 60)

    with engine.begin() as conn:
        # Проверяем, есть ли новое название
        new_exists = conn.execute(
            text("""
                SELECT d.id FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": NEW_NAME},
        ).scalar()
        
        if not new_exists:
            print(f"\n⚠ ВНИМАНИЕ: «{NEW_NAME}» не найден в БД!")
            print("   Убедитесь, что он существует перед удалением старого.")
            return

        # 1) События: старый ГО → единый Торжокский МО
        r = conn.execute(
            text("UPDATE events SET district_name = :new WHERE district_name = :old RETURNING id"),
            {"new": NEW_NAME, "old": OLD_NAME},
        )
        ids = r.fetchall()
        if ids:
            print(f"\n  События «{OLD_NAME}» → «{NEW_NAME}»: {len(ids)} шт.")

        # 2) Админзоны: в district_names заменить старое название на новое
        rows = conn.execute(
            text("SELECT id, district_names FROM administrative_zones"),
        ).fetchall()
        updated_zones = 0
        for row in rows:
            zone_id, dn = row[0], row[1]
            if not dn:
                continue
            try:
                arr = dn if isinstance(dn, list) else json.loads(dn)
            except Exception:
                continue
            changed = False
            new_arr = []
            seen = set()
            for x in arr:
                s = str(x).strip()
                if s == OLD_NAME:
                    s = NEW_NAME
                    changed = True
                if s and s not in seen:
                    seen.add(s)
                    new_arr.append(s)
            if changed:
                new_json = json.dumps(new_arr, ensure_ascii=False)
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": new_json, "id": zone_id},
                )
                updated_zones += 1
        if updated_zones > 0:
            print(f"  Зоны: обновлено {updated_zones} шт. (замена «{OLD_NAME}» → «{NEW_NAME}»).")

        # 3) Удалить старый ГО
        r = conn.execute(
            text("""
                DELETE FROM districts d
                USING regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                RETURNING d.id
            """),
            {"region": REGION_NAME, "name": OLD_NAME},
        )
        if r.fetchone():
            print(f"\n  ✓ Удалён: «{OLD_NAME}»")
        else:
            print(f"\n  (не найден: «{OLD_NAME}» — возможно, уже удалён)")

    print(f"\n✓ Готово. Остаётся только «{NEW_NAME}».")


if __name__ == "__main__":
    main()
