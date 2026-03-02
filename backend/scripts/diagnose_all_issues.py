"""Diagnose all reported issues at once"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    # 1. Murom in Vladimir
    print("=== 1. Муром во Владимирской области ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Владимирская%%' AND d.name LIKE '%%уром%%'
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")

    # 2. DNR geometry
    print("\n=== 2. ДНР ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6 as area_km2, ST_NPoints(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Донецкая%%'
        ORDER BY d.name
    """)).fetchall()
    total = sum(r[1] or 0 for r in rows)
    for r in rows: print(f"  {r[0]}: {r[1]:.0f} km2, {r[2]} pts")
    print(f"  Total area: {total:.0f} km2")

    # 3. Zaporizhzhia
    print("\n=== 3. Запорожская область ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6 as area_km2
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Запорожская%%'
        ORDER BY d.name
    """)).fetchall()
    for r in rows: print(f"  {r[0]}: {r[1]:.0f} km2")

    # 4. Dubensky in Kaluga
    print("\n=== 4. Дубенский район в Калужской ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Калужская%%' AND d.name LIKE '%%убен%%'
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")
    # Check where Dubensky actually should be
    rows2 = c.execute(text("""
        SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name LIKE '%%убенск%%'
    """)).fetchall()
    print("  All Dubensky in DB:")
    for r in rows2: print(f"    {r[0]} -> {r[1]}")

    # 5. Karachaevsky in KChR  
    print("\n=== 5. Карачаевский в КЧР ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Карачаево%%'
        ORDER BY d.name
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")

    # 6. Nerekhta in Kostroma
    print("\n=== 6. Нерехтский в Костромской ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Костромская%%' AND d.name LIKE '%%ерехт%%'
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")
    rows2 = c.execute(text("""
        SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name LIKE '%%ерехт%%'
    """)).fetchall()
    print("  All Nerekhta in DB:")
    for r in rows2: print(f"    {r[0]} -> {r[1]}")

    # 7. Krasnoyarsk - check bounds
    print("\n=== 7. Красноярский край - bounds ===")
    row = c.execute(text("""
        SELECT ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom)
        FROM regions WHERE name LIKE '%%Красноярский%%'
    """)).fetchone()
    if row: print(f"  Region bbox: lon {row[0]:.1f}-{row[2]:.1f}, lat {row[1]:.1f}-{row[3]:.1f}")
    
    rows = c.execute(text("""
        SELECT d.name, ST_YMax(d.geom), ST_YMin(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Красноярский%%'
        ORDER BY ST_YMax(d.geom) DESC LIMIT 5
    """)).fetchall()
    for r in rows: print(f"  Northernmost: {r[0]} lat {r[2]:.1f}-{r[1]:.1f}")

    # 8. LNR geometry
    print("\n=== 8. ЛНР ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6, ST_NPoints(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Луганская%%'
        ORDER BY d.name
    """)).fetchall()
    total = sum(r[1] or 0 for r in rows)
    for r in rows: print(f"  {r[0]}: {r[1]:.0f} km2, {r[2]} pts")
    print(f"  Total area: {total:.0f} km2")

    # 9. Kovdorsky in Murmansk
    print("\n=== 9. Ковдорский в Мурманской ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Мурманская%%' AND d.name LIKE '%%овдор%%'
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")
    rows2 = c.execute(text("""
        SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name LIKE '%%овдор%%'
    """)).fetchall()
    print("  All Kovdor in DB:")
    for r in rows2: print(f"    {r[0]} -> {r[1]}")

    # 10. Zapolyarny in NAO
    print("\n=== 10. Заполярный в НАО ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Ненецкий%%'
        ORDER BY d.name
    """)).fetchall()
    for r in rows: print(f"  {r[0]}: {r[1]:.0f} km2")

    # 11. Veliky Novgorod
    print("\n=== 11. Великий Новгород ===")
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Новгородская%%' AND d.name LIKE '%%овгород%%'
    """)).fetchall()
    for r in rows: print(f"  {r[0]}")

    # Moscow/SPb/Sevastopol
    print("\n=== Москва/Питер/Севастополь ===")
    for city in ['Москва', 'Санкт-Петербург', 'Севастополь']:
        row = c.execute(text("""
            SELECT COUNT(*), ST_Area(r.geom::geography)/1e6
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            WHERE r.name = :name
            GROUP BY r.geom
        """), {'name': city}).fetchone()
        if row: print(f"  {city}: {row[0]} districts, area={row[1]:.0f} km2")
