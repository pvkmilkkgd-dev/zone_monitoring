"""
Объединить «город Торжок» и «Торжокский муниципальный округ» в один «Торжокский муниципальный округ».
Объединить геометрию, удалить запись «город Торжок», переназначить события и зоны.
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

REGION_NAME = "Тверская область"
CITY_NAME = "город Торжок"
MO_NAME = "Торжокский муниципальный округ"


def main():
    print(f"Объединение Торжка в {REGION_NAME}")
    print("=" * 60)
    print(f"Объединяем: «{CITY_NAME}» + «{MO_NAME}»")
    print(f"Результат: «{MO_NAME}» (с объединённой геометрией)")
    print("=" * 60)

    with engine.begin() as conn:
        # Проверяем наличие обеих записей
        city_id = conn.execute(
            text("""
                SELECT d.id, d.geom IS NOT NULL as has_geom FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": CITY_NAME},
        ).fetchone()
        
        mo_id = conn.execute(
            text("""
                SELECT d.id, d.geom IS NOT NULL as has_geom FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": MO_NAME},
        ).fetchone()
        
        if not city_id:
            print(f"\n⚠ «{CITY_NAME}» не найден в БД.")
        else:
            print(f"\n✓ Найден: «{CITY_NAME}» (id={city_id[0]}, геометрия={'есть' if city_id[1] else 'нет'})")
        
        if not mo_id:
            print(f"\n✗ «{MO_NAME}» не найден в БД! Создайте его сначала.")
            return
        else:
            print(f"✓ Найден: «{MO_NAME}» (id={mo_id[0]}, геометрия={'есть' if mo_id[1] else 'нет'})")
        
        # Объединяем геометрию, если обе есть
        if city_id and mo_id:
            if city_id[1] and mo_id[1]:
                # Обе геометрии есть - объединяем
                conn.execute(
                    text("""
                        UPDATE districts d
                        SET geom = ST_Multi(ST_MakeValid(ST_Union(
                            d.geom,
                            (SELECT geom FROM districts WHERE id = :city_id)
                        )))
                        FROM regions r
                        WHERE d.region_id = r.id AND r.name = :region AND d.name = :mo_name
                    """),
                    {"city_id": city_id[0], "region": REGION_NAME, "mo_name": MO_NAME},
                )
                print(f"\n✓ Геометрии объединены (ST_Union)")
            elif city_id[1] and not mo_id[1]:
                # Есть только у города - копируем в МО
                conn.execute(
                    text("""
                        UPDATE districts d
                        SET geom = (SELECT geom FROM districts WHERE id = :city_id)
                        FROM regions r
                        WHERE d.region_id = r.id AND r.name = :region AND d.name = :mo_name
                    """),
                    {"city_id": city_id[0], "region": REGION_NAME, "mo_name": MO_NAME},
                )
                print(f"\n✓ Геометрия скопирована из «{CITY_NAME}» в «{MO_NAME}»")
            elif not city_id[1] and mo_id[1]:
                print(f"\n✓ Геометрия уже есть в «{MO_NAME}», ничего не меняем")
            else:
                print(f"\n⚠ Геометрии нет ни у одного из МО")
        
        # Переназначаем события
        r = conn.execute(
            text("UPDATE events SET district_name = :new WHERE district_name = :old RETURNING id"),
            {"new": MO_NAME, "old": CITY_NAME},
        )
        ids = r.fetchall()
        if ids:
            print(f"\n✓ События «{CITY_NAME}» → «{MO_NAME}»: {len(ids)} шт.")
        
        # Обновляем административные зоны
        rows = conn.execute(
            text("SELECT id, district_names FROM administrative_zones"),
        ).fetchall()
        updated_zones = 0
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
                if s == CITY_NAME:
                    s = MO_NAME
                    changed = True
                if s and s not in seen:
                    seen.add(s)
                    new_arr.append(s)
            if changed:
                new_json = json.dumps(new_arr, ensure_ascii=False)
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": new_json, "id": zone_id},
                )
                updated_zones += 1
        if updated_zones > 0:
            print(f"✓ Зоны: обновлено {updated_zones} шт.")
        
        # Удаляем запись города
        if city_id:
            conn.execute(
                text("DELETE FROM districts WHERE id = :id"),
                {"id": city_id[0]},
            )
            print(f"\n✓ Удалён: «{CITY_NAME}»")
        
        # Проверяем результат
        result = conn.execute(
            text("""
                SELECT ROUND(ST_Area(d.geom::geography)/1000000), ST_NPoints(d.geom)
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name AND d.geom IS NOT NULL
            """),
            {"region": REGION_NAME, "name": MO_NAME},
        ).fetchone()
        
        if result:
            print(f"\n✓ Итоговая геометрия «{MO_NAME}»: ~{int(result[0])} км², {result[1]} точек")

    print("\n✓ Готово. Остаётся только «Торжокский муниципальный округ» с объединённой геометрией.")


if __name__ == "__main__":
    main()
