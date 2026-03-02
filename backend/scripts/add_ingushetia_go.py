"""Добавить недостающие городские округа в Республику Ингушетия."""
import os
import uuid
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Республика Ингушетия"

GO_NAMES = [
    "городской округ город Магас",
    "городской округ город Назрань",
    "городской округ город Карабулак",
    "городской округ город Сунжа",
    "городской округ город Малгобек",
]


def main():
    with engine.begin() as conn:
        region_id = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": REGION_NAME},
        ).scalar()
        if not region_id:
            print(f"Регион «{REGION_NAME}» не найден.")
            return

        added = 0
        for name in GO_NAMES:
            exists = conn.execute(
                text("""
                    SELECT 1 FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": name},
            ).scalar()
            if exists:
                print(f"  Уже есть: {name}")
                continue
            conn.execute(
                text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
                {"id": uuid.uuid4(), "rid": region_id, "name": name},
            )
            print(f"  Добавлено: {name}")
            added += 1

        print(f"\nВсего добавлено: {added}")

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :name
                ORDER BY d.name
            """),
            {"name": REGION_NAME},
        ).fetchall()
        print(f"\nИнгушетия — всего районов в БД: {len(rows)}")
        for r in rows:
            print(f"  {r[0]}")


if __name__ == "__main__":
    main()
