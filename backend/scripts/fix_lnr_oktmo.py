"""
Привести перечень районов ЛНР в соответствие с ОКТМО (верхний уровень).

ГО (11): городской округ город X
МО (17): Xский муниципальный округ
"""
import os
import uuid
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Луганская Народная Республика"

# Городские округа — полное название как в ОКТМО
GO_NAMES = [
    "городской округ город Луганск",
    "городской округ город Алчевск",
    "городской округ город Брянка",
    "городской округ город Кировск",
    "городской округ город Красный Луч",
    "городской округ город Лисичанск",
    "городской округ город Первомайск",
    "городской округ город Ровеньки",
    "городской округ город Рубежное",
    "городской округ город Северодонецк",
    "городской округ город Стаханов",
]

# Муниципальные округа — в ОКТМО без суффикса, добавляем «муниципальный округ»
MO_NAMES = [
    "Антрацитовский муниципальный округ",
    "Беловодский муниципальный округ",
    "Белокуракинский муниципальный округ",
    "Краснодонский муниципальный округ",
    "Кременской муниципальный округ",
    "Лутугинский муниципальный округ",
    "Марковский муниципальный округ",
    "Меловский муниципальный округ",
    "Новоайдарский муниципальный округ",
    "Новопсковский муниципальный округ",
    "Перевальский муниципальный округ",
    "Сватовский муниципальный округ",
    "Свердловский муниципальный округ",
    "Славяносербский муниципальный округ",
    "Станично-Луганский муниципальный округ",
    "Старобельский муниципальный округ",
    "Троицкий муниципальный округ",
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

        # Удалить все текущие районы ЛНР
        deleted = conn.execute(
            text("DELETE FROM districts WHERE region_id = :rid RETURNING name"),
            {"rid": region_id},
        ).fetchall()
        print(f"Удалено районов: {len(deleted)}")
        for d in deleted:
            print(f"  - {d[0]}")

        # Добавить 11 ГО
        for name in GO_NAMES:
            conn.execute(
                text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
                {"id": uuid.uuid4(), "rid": region_id, "name": name},
            )
        print(f"\nДобавлено ГО: {len(GO_NAMES)}")

        # Добавить 17 МО
        for name in MO_NAMES:
            conn.execute(
                text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
                {"id": uuid.uuid4(), "rid": region_id, "name": name},
            )
        print(f"Добавлено МО: {len(MO_NAMES)}")

    # Итог
    print("\nИтоговый перечень районов ЛНР (по ОКТМО):")
    print("=" * 60)
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
        for r in rows:
            print(f"  {r[0]}")
        print(f"\nВсего: {len(rows)}")


if __name__ == "__main__":
    main()
