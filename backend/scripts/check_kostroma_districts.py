"""Проверить и при необходимости исправить Мантурово в Костромской области.

С 2019 года Мантуровский муниципальный район преобразован в городской округ
город Мантурово. В БД переименовываем запись в актуальное название.
"""
import os
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.begin() as conn:
    # Переименовать Мантуровский муниципальный округ -> городской округ город Мантурово
    r = conn.execute(text("""
        UPDATE districts d
        SET name = 'городской округ город Мантурово'
        FROM regions r
        WHERE d.region_id = r.id
          AND r.name = 'Костромская область'
          AND d.name = 'Мантуровский муниципальный округ'
        RETURNING d.id
    """)).fetchone()
    if r:
        print("Переименовано: «Мантуровский муниципальный округ» -> «городской округ город Мантурово»")
    else:
        # Уже переименовано или нет такой записи
        exists = conn.execute(text("""
            SELECT 1 FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = 'Костромская область' AND d.name = 'городской округ город Мантурово'
        """)).scalar()
        if exists:
            print("Запись «городской округ город Мантурово» уже есть.")
        else:
            print("Запись «Мантуровский муниципальный округ» не найдена в Костромской области.")

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Костромская область'
        ORDER BY d.name
    """)).fetchall()
    print("\nРайоны/ГО Костромской области в БД:")
    for r in rows:
        print(f"  {r[0]}")
    manturovo = [x[0] for x in rows if "мантуров" in x[0].lower()]
    print("\nЗаписи с 'Мантуров':", manturovo if manturovo else "нет")
