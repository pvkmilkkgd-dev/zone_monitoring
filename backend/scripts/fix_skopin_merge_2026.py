"""
Скопин и Скопинский район с 2026 — один «Скопинский муниципальный округ».
Удаляем запись «городской округ город Скопин» / «городской округ Скопин» в Рязанской области,
переназначаем события и зоны на «Скопинский муниципальный округ».
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

REGION_NAME = "Рязанская область"
# Варианты названия городского округа в БД
CITY_OKRUG_NAMES = ["городской округ город Скопин", "городской округ Скопин"]
UNIFIED_NAME = "Скопинский муниципальный округ"


def main():
    with engine.begin() as conn:
        # 1) События: старый район -> единый Скопинский МО
        for old_name in CITY_OKRUG_NAMES:
            r = conn.execute(
                text("UPDATE events SET district_name = :new WHERE district_name = :old RETURNING id"),
                {"new": UNIFIED_NAME, "old": old_name},
            )
            ids = r.fetchall()
            if ids:
                print(f"  События district_name «{old_name}» → «{UNIFIED_NAME}»: {len(ids)} шт.")

        # 2) Админзоны: в district_names заменить старые названия на единое (и убрать дубли)
        # district_names — JSON массив строк; после замены может быть два "Скопинский муниципальный округ"
        for old_name in CITY_OKRUG_NAMES:
            # Получаем зоны, где в district_names есть old_name
            rows = conn.execute(
                text("SELECT id, district_names FROM administrative_zones WHERE district_names::text LIKE :pat"),
                {"pat": f"%{old_name.replace(chr(34), chr(39))}%"},
            ).fetchall()
            for row in rows:
                zone_id, dn = row[0], row[1]
                if not dn:
                    continue
                # Парсим JSON, заменяем вхождение, убираем дубли, сохраняем порядок
                try:
                    arr = dn if isinstance(dn, list) else json.loads(dn)
                except Exception:
                    continue
                new_arr = []
                seen = set()
                for x in arr:
                    s = str(x).strip()
                    if s in CITY_OKRUG_NAMES:
                        s = UNIFIED_NAME
                    if s and s not in seen:
                        seen.add(s)
                        new_arr.append(s)
                new_json = json.dumps(new_arr, ensure_ascii=False)
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": new_json, "id": zone_id},
                )
                print(f"  Зона {zone_id}: district_names обновлён (замена «{old_name}» → «{UNIFIED_NAME}»).")

        # 3) Удалить район «городской округ» по Рязанской области
        deleted_any = False
        for name in CITY_OKRUG_NAMES:
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
                print(f"  Удалён район: «{name}»")
                deleted_any = True
        if not deleted_any:
            print("  Ни одна запись «городской округ Скопин» в districts не найдена (уже удалено или другое написание).")

    print("\nГотово. Остаётся один «Скопинский муниципальный округ» в Рязанской области.")


if __name__ == "__main__":
    main()
