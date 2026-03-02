"""Исправить ЗАТО Уральский: оставить только «городской округ ЗАТО Уральский»."""
import os
import sys

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

REGION_NAME = "Свердловская область"
CORRECT_NAME = "городской округ ЗАТО Уральский"
OLD_NAMES = [
    "ЗАТО посёлок Уральский",
    "ЗАТО поселок Уральский",
    "поселок Уральский",
    "посёлок Уральский",
]


def main():
    print(f"Исправление ЗАТО Уральский в {REGION_NAME}")
    print("=" * 60)

    with engine.begin() as conn:
        # Проверяем, есть ли правильное название
        correct_exists = conn.execute(
            text("""
                SELECT d.id FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": CORRECT_NAME},
        ).scalar()

        if not correct_exists:
            print(f"✗ «{CORRECT_NAME}» не найдено. Добавьте его сначала.")
            return

        # Удаляем старые варианты названий
        for old_name in OLD_NAMES:
            r = conn.execute(
                text("""
                    DELETE FROM districts d
                    USING regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                    RETURNING d.id
                """),
                {"region": REGION_NAME, "name": old_name},
            )
            if r.fetchone():
                print(f"  Удалено старое название: «{old_name}»")

        # Переназначаем события и зоны со старых названий на правильное
        for old_name in OLD_NAMES:
            r = conn.execute(
                text("UPDATE events SET district_name = :new WHERE district_name = :old RETURNING id"),
                {"new": CORRECT_NAME, "old": old_name},
            )
            ids = r.fetchall()
            if ids:
                print(f"  События «{old_name}» → «{CORRECT_NAME}»: {len(ids)} шт.")

        # Обновляем административные зоны
        import json
        rows = conn.execute(
            text("SELECT id, district_names FROM administrative_zones"),
        ).fetchall()
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
                if s in OLD_NAMES:
                    s = CORRECT_NAME
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
                print(f"  Зона {zone_id}: district_names обновлён.")

    print(f"\n✓ Готово. Остаётся только «{CORRECT_NAME}».")


if __name__ == "__main__":
    main()
