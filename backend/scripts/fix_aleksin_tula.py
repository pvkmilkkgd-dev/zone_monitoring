"""
Тульская область: удалить «городской округ Алексин»,
переименовать «Алексинский муниципальный район» в «городской округ Алексин».
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

REGION_NAME = "Тульская область"
CITY_OKRUG = "городской округ Алексин"
DISTRICT_OLD = "Алексинский муниципальный район"
DISTRICT_NEW = "городской округ Алексин"  # то же, что CITY_OKRUG


def main():
    print(f"Тульская область: Алексин")
    print("=" * 60)
    print(f"Удалить: «{CITY_OKRUG}»")
    print(f"Переименовать: «{DISTRICT_OLD}» → «{DISTRICT_NEW}»")
    print("=" * 60)

    with engine.begin() as conn:
        # 1) События: район → новое название
        r = conn.execute(
            text("UPDATE events SET district_name = :new WHERE district_name = :old RETURNING id"),
            {"new": DISTRICT_NEW, "old": DISTRICT_OLD},
        )
        ids = r.fetchall()
        if ids:
            print(f"\n  События «{DISTRICT_OLD}» → «{DISTRICT_NEW}»: {len(ids)} шт.")

        # 2) Админзоны: заменить старое название района на новое
        rows = conn.execute(
            text("SELECT id, district_names FROM administrative_zones"),
        ).fetchall()
        updated = 0
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
                if s == DISTRICT_OLD:
                    s = DISTRICT_NEW
                    changed = True
                if s and s not in seen:
                    seen.add(s)
                    new_arr.append(s)
            if changed:
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": json.dumps(new_arr, ensure_ascii=False), "id": zone_id},
                )
                updated += 1
        if updated:
            print(f"  Зоны: обновлено {updated} шт.")

        # 3) Удалить запись «городской округ Алексин»
        r = conn.execute(
            text("""
                DELETE FROM districts d
                USING regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                RETURNING d.id
            """),
            {"region": REGION_NAME, "name": CITY_OKRUG},
        )
        if r.fetchone():
            print(f"\n  Удалён: «{CITY_OKRUG}»")
        else:
            print(f"\n  (запись «{CITY_OKRUG}» не найдена)")

        # 4) Переименовать «Алексинский муниципальный район» в «городской округ Алексин»
        r = conn.execute(
            text("""
                UPDATE districts d
                SET name = :new
                FROM regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :old
                RETURNING d.id
            """),
            {"new": DISTRICT_NEW, "region": REGION_NAME, "old": DISTRICT_OLD},
        )
        if r.fetchone():
            print(f"  Переименован: «{DISTRICT_OLD}» → «{DISTRICT_NEW}»")
        else:
            print(f"  (запись «{DISTRICT_OLD}» не найдена)")

    print("\nГотово.")


if __name__ == "__main__":
    main()
