"""
Аудит всех регионов (как Москва и СПб): кол-во районов, площадь, нулевые геометрии, дубликаты.
Изменения НЕ вносятся — только отчёт.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Примерные площади субъектов РФ (км2) для сравнения
REGION_AREAS_KM2 = {
    "Республика Адыгея": 7600,
    "Республика Алтай": 93000,
    "Алтайский край": 168000,
    "Амурская область": 362000,
    "Архангельская область": 590000,
    "Астраханская область": 49000,
    "Белгородская область": 27000,
    "Брянская область": 35000,
    "Республика Бурятия": 351000,
    "Владимирская область": 29000,
    "Волгоградская область": 113000,
    "Вологодская область": 144000,
    "Воронежская область": 52000,
    "город Москва": 2561,
    "город Санкт-Петербург": 1439,
    "город Севастополь": 864,
    "Донецкая Народная Республика": 26500,
    "Еврейская автономная область": 36000,
    "Забайкальский край": 432000,
    "Запорожская область": 27200,
    "Ивановская область": 21000,
    "Республика Ингушетия": 3600,
    "Иркутская область": 774000,
    "Кабардино-Балкарская Республика": 12500,
    "Калининградская область": 15100,
    "Республика Калмыкия": 75000,
    "Калужская область": 29800,
    "Камчатский край": 464000,
    "Карачаево-Черкесская Республика": 14300,
    "Республика Карелия": 180500,
    "Кемеровская область": 95800,
    "Кировская область": 120400,
    "Республика Коми": 416800,
    "Костромская область": 60200,
    "Краснодарский край": 76000,
    "Красноярский край": 2366800,
    "Республика Крым": 26080,
    "Курганская область": 71000,
    "Курская область": 30000,
    "Луганская Народная Республика": 26684,
    "Ленинградская область": 83900,
    "Липецкая область": 24000,
    "Магаданская область": 462500,
    "Республика Марий Эл": 23300,
    "Республика Мордовия": 26100,
    "Московская область": 44300,
    "Мурманская область": 144900,
    "Ненецкий автономный округ": 176800,
    "Нижегородская область": 76600,
    "Новгородская область": 54500,
    "Новосибирская область": 177800,
    "Омская область": 141100,
    "Оренбургская область": 124000,
    "Орловская область": 24600,
    "Пензенская область": 43300,
    "Пермский край": 160200,
    "Приморский край": 165600,
    "Псковская область": 55300,
    "Ростовская область": 101000,
    "Рязанская область": 39600,
    "Самарская область": 53500,
    "Саратовская область": 101200,
    "Республика Саха (Якутия)": 3083500,
    "Сахалинская область": 87100,
    "Свердловская область": 194300,
    "Севастополь": 864,
    "Республика Северная Осетия - Алания": 8000,
    "Смоленская область": 49800,
    "Ставропольский край": 66100,
    "Тамбовская область": 34400,
    "Республика Татарстан": 67800,
    "Тверская область": 84200,
    "Томская область": 314400,
    "Тульская область": 25600,
    "Республика Тыва": 168600,
    "Тюменская область": 146400,
    "Удмуртская Республика": 42000,
    "Ульяновская область": 37180,
    "Хабаровский край": 787600,
    "Ханты-Мансийский автономный округ - Югра": 534800,
    "Челябинская область": 88500,
    "Чеченская Республика": 16100,
    "Чувашская Республика": 18340,
    "Чукотский автономный округ": 721500,
    "Ямало-Ненецкий автономный округ": 769250,
    "Ярославская область": 36170,
}

with ENGINE.connect() as c:
    regions = c.execute(text("""
        SELECT r.id, r.name, 
               COUNT(d.id) as cnt,
               ROUND(SUM(ST_Area(d.geom::geography))/1e6) as sum_km2
        FROM regions r
        LEFT JOIN districts d ON d.region_id = r.id AND d.geom IS NOT NULL AND ST_NPoints(d.geom) > 0
        GROUP BY r.id, r.name
        ORDER BY r.name
    """)).fetchall()

print("=" * 80)
print("АУДИТ РЕГИОНОВ (без внесения изменений)")
print("=" * 80)

issues = []
for rid, rname, cnt, sum_km2 in regions:
    sum_km2 = sum_km2 or 0
    expected = REGION_AREAS_KM2.get(rname)
    # Районы с нулевой геометрией
    with ENGINE.connect() as c2:
        zero = c2.execute(text("""
            SELECT name FROM districts 
            WHERE region_id = :rid AND (geom IS NULL OR ST_NPoints(geom) = 0)
        """), {'rid': str(rid)}).fetchall()
        zero_names = [r[0] for r in zero]
        dupes = c2.execute(text("""
            SELECT name, COUNT(*) FROM districts WHERE region_id = :rid GROUP BY name HAVING COUNT(*) > 1
        """), {'rid': str(rid)}).fetchall()

    status = []
    if zero_names:
        status.append(f"НЕТ_ГЕОМ: {len(zero_names)}")
        issues.append((rname, "no_geom", zero_names))
    if dupes:
        status.append(f"ДУБЛИ: {len(dupes)}")
        issues.append((rname, "dupes", [(n, c) for n, c in dupes]))
    if expected and sum_km2 > 0:
        ratio = sum_km2 / expected
        if ratio < 0.5:
            status.append("ПЛОЩАДЬ_МАЛО")
            issues.append((rname, "area_small", f"{sum_km2} vs ~{expected}"))
        elif ratio > 1.8:
            status.append("ПЛОЩАДЬ_БОЛЬШЕ")
            issues.append((rname, "area_large", f"{sum_km2} vs ~{expected}"))

    expected_str = f" (ожид. ~{expected})" if expected else ""
    status_str = " | " + ", ".join(status) if status else ""
    print(f"\n{rname}")
    print(f"  Районов: {cnt}, суммарная площадь: {sum_km2} km2{expected_str}{status_str}")
    if zero_names:
        print(f"  Без геометрии: {zero_names[:8]}{'...' if len(zero_names) > 8 else ''}")
    if dupes:
        print(f"  Дубликаты имён: {[(n, c) for n, c in dupes]}")

print("\n" + "=" * 80)
print("СВОДКА ПРОБЛЕМ (требуют проверки)")
print("=" * 80)
by_type = {}
for rname, kind, detail in issues:
    by_type.setdefault(kind, []).append((rname, detail))
for kind, items in sorted(by_type.items()):
    print(f"\n  [{kind}] {len(items)} регионов:")
    for rname, detail in items[:15]:
        print(f"    - {rname}: {detail}")
    if len(items) > 15:
        print(f"    ... и ещё {len(items) - 15}")

with ENGINE.connect() as c:
    total_regions = c.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    total_districts = c.execute(text("SELECT COUNT(*) FROM districts")).scalar()
    no_geom_total = c.execute(text("""
        SELECT COUNT(*) FROM districts WHERE geom IS NULL OR ST_NPoints(geom) = 0
    """)).scalar()
print(f"\nВсего регионов: {total_regions}, районов: {total_districts}, без геометрии: {no_geom_total}")
