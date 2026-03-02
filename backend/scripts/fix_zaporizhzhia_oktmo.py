"""
Привести перечень районов Запорожской области в соответствие с ОКТМО.

Исправления:
1. Удалить неверную запись «Запорожский муниципальный район» (в ОКТМО такого нет).
2. Удалить Бердянский МО и Мелитопольский МО — они входят в состав одноимённых ГО,
   чтобы не было дублирования территории.
3. Добавить недостающие МО: Акимовский, Веселовский, Каменско-Днепровский,
   Куйбышевский, Михайловский, Приазовский, Приморский, Токмакский, Черниговский.
4. Добавить ГО: городской округ Мелитополь, городской округ Бердянск, городской округ Энергодар.

Итоговый список по ОКТМО:
- МО: Акимовский, Веселовский, Васильевский, Каменско-Днепровский, Куйбышевский,
  Михайловский, Пологовский, Приазовский, Приморский, Токмакский, Черниговский.
- ГО: Бердянск, Мелитополь, Энергодар.
"""
import os
import uuid
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Запорожская область"

# Удалить: неверный «район» и два МО, входящие в состав ГО (избегаем дубля территории)
DELETE_NAMES = [
    "Запорожский муниципальный район",
    "Бердянский муниципальный округ",
    "Мелитопольский муниципальный округ",
]

# Новые МО (по ОКТМО; остаются Васильевский и Пологовский)
NEW_MO = [
    "Акимовский муниципальный округ",
    "Веселовский муниципальный округ",
    "Каменско-Днепровский муниципальный округ",
    "Куйбышевский муниципальный округ",
    "Михайловский муниципальный округ",
    "Приазовский муниципальный округ",
    "Приморский муниципальный округ",
    "Токмакский муниципальный округ",
    "Черниговский муниципальный округ",
]

# Городские округа
NEW_GO = [
    "городской округ Бердянск",
    "городской округ Мелитополь",
    "городской округ Энергодар",
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

        # 1) Удалить неверные/дублирующие записи
        for name in DELETE_NAMES:
            r = conn.execute(
                text("""
                    DELETE FROM districts d
                    USING regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                    RETURNING d.id
                """),
                {"region": REGION_NAME, "name": name},
            )
            if r.fetchone():
                print(f"  Удалено: {name}")
            else:
                print(f"  (не найден: {name})")

        # 2) Добавить новые МО, если ещё нет
        for name in NEW_MO:
            exists = conn.execute(
                text("""
                    SELECT 1 FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": name},
            ).scalar()
            if exists:
                print(f"  Уже есть МО: {name}")
                continue
            conn.execute(
                text("""
                    INSERT INTO districts (id, region_id, name, geom)
                    VALUES (:id, :region_id, :name, NULL)
                """),
                {
                    "id": uuid.uuid4(),
                    "region_id": region_id,
                    "name": name,
                },
            )
            print(f"  Добавлен МО: {name}")

        # 3) Добавить ГО, если ещё нет
        for name in NEW_GO:
            exists = conn.execute(
                text("""
                    SELECT 1 FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": name},
            ).scalar()
            if exists:
                print(f"  Уже есть ГО: {name}")
                continue
            conn.execute(
                text("""
                    INSERT INTO districts (id, region_id, name, geom)
                    VALUES (:id, :region_id, :name, NULL)
                """),
                {
                    "id": uuid.uuid4(),
                    "region_id": region_id,
                    "name": name,
                },
            )
            print(f"  Добавлен ГО: {name}")

    # Итоговый список
    print("\n" + "=" * 60)
    print("Итоговый перечень районов Запорожской области:")
    print("=" * 60)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT d.name
                FROM districts d
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
