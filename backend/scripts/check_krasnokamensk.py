"""Rename Krasnokamensk district to current official name (МО)."""
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

OLD_NAME = "Муниципальный район Город Краснокаменск и Краснокаменский район"
NEW_NAME = "Краснокаменский муниципальный округ"

with engine.begin() as conn:
    result = conn.execute(text("""
        UPDATE districts d
        SET name = :new_name
        FROM regions r
        WHERE d.region_id = r.id
          AND r.name = 'Забайкальский край'
          AND d.name = :old_name
        RETURNING d.id, d.name
    """), {"old_name": OLD_NAME, "new_name": NEW_NAME})
    row = result.fetchone()
    if row:
        print(f"Renamed: '{OLD_NAME}' -> '{NEW_NAME}'")
        print(f"  ID: {row[0]}")
    else:
        print("No matching district found (already renamed or missing).")
