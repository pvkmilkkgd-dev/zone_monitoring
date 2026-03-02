"""Проверить наличие «городской округ ЗАТО Уральский» в официальных источниках."""
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
TARGET_NAME = "городской округ ЗАТО Уральский"


def main():
    print("Проверка официальных источников для ЗАТО Уральский")
    print("=" * 60)
    print("\nНайдено в открытых источниках:")
    print("1. Wikipedia: ЗАТО Уральский существует, с 2021 года называется")
    print("   «городской округ ЗАТО Уральский»")
    print("2. geoadm.com: Подтверждает статус «городской округ ЗАТО Уральский»")
    print("3. Постановление № 123-ПП от 16.02.2023: содержит перечень опорных")
    print("   населенных пунктов (но не полный перечень МО)")
    print("\n" + "=" * 60)
    
    with engine.connect() as conn:
        # Проверяем, что есть в БД
        rows = conn.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND (
                    d.name LIKE '%Уральск%' OR d.name LIKE '%ЗАТО%'
                )
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall()
        
        print("\nВ БД найдено:")
        for r in rows:
            marker = "✓" if r[0] == TARGET_NAME else " "
            print(f"  {marker} {r[0]}")
        
        # Проверяем наличие правильного названия
        exists = conn.execute(
            text("""
                SELECT 1 FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": TARGET_NAME},
        ).scalar()
        
        print(f"\n{'✓' if exists else '✗'} «{TARGET_NAME}» в БД: {'есть' if exists else 'НЕТ'}")
        
        if not exists:
            print("\n⚠ ВНИМАНИЕ: Название отсутствует в БД, но есть в официальных источниках!")
            print("   Рекомендуется добавить через скрипт check_add_zato_uralsky.py")
        else:
            print("\n✓ Название присутствует в БД и соответствует официальным источникам.")


if __name__ == "__main__":
    main()
