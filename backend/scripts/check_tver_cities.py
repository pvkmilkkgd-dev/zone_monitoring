"""Проверить наличие городов Тверской области в БД и ОКТМО."""
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

REGION_NAME = "Тверская область"
CITIES_TO_CHECK = [
    "город Вышний Волочек",
    "город Кимры",
    "город Ржев",
    "город Удомля",
]


def main():
    print(f"Проверка городов в {REGION_NAME}")
    print("=" * 60)
    print("\nОфициальный ОКТМО (okp-okpd.ru):")
    print("✓ 28714000000 | город ВышнийВолочек")
    print("✓ 28726000000 | город Кимры")
    print("✓ 28745000000 | город Ржев")
    print("✗ город Удомля - НЕТ в ОКТМО (есть только Удомельский муниципальный район)")
    print("\n" + "=" * 60)
    
    with engine.connect() as conn:
        print("\nВ БД найдено:")
        for city_name in CITIES_TO_CHECK:
            exists = conn.execute(
                text("""
                    SELECT d.name FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": city_name},
            ).fetchone()
            
            marker = "✓" if exists else "✗"
            status = "есть" if exists else "НЕТ"
            print(f"  {marker} {city_name}: {status}")
            if exists:
                print(f"      (в БД: {exists[0]})")
        
        # Проверяем также похожие названия
        print("\nПохожие названия в БД:")
        rows = conn.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND (
                    d.name LIKE '%Вышний%' OR
                    d.name LIKE '%Кимр%' OR
                    d.name LIKE '%Ржев%' OR
                    d.name LIKE '%Удомл%'
                )
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall()
        for r in rows:
            print(f"  - {r[0]}")


if __name__ == "__main__":
    main()
