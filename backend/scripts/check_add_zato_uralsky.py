"""Проверить и добавить «городской округ ЗАТО Уральский» в Свердловскую область."""
import os
import sys
import uuid

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


def main():
    print(f"Проверка МО в {REGION_NAME}")
    print("=" * 60)

    with engine.connect() as conn:
        # Проверяем, что есть по Уральскому
        rows = conn.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND (
                    d.name LIKE '%Уральск%' OR d.name LIKE '%Уральский%'
                )
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall()
        print("\nНайдено МО с 'Уральск':")
        for r in rows:
            print(f"  {r[0]}")

        # Проверяем, есть ли правильное название
        exists = conn.execute(
            text("""
                SELECT 1 FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": CORRECT_NAME},
        ).scalar()

        if exists:
            print(f"\n✓ «{CORRECT_NAME}» уже есть в БД.")
            return

        # Получаем region_id
        region_id = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": REGION_NAME},
        ).scalar()
        if not region_id:
            print(f"\n✗ Регион «{REGION_NAME}» не найден.")
            return

        # Добавляем
        with engine.begin() as conn2:
            conn2.execute(
                text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
                {"id": uuid.uuid4(), "rid": region_id, "name": CORRECT_NAME},
            )
            print(f"\n✓ Добавлено: «{CORRECT_NAME}»")


if __name__ == "__main__":
    main()
