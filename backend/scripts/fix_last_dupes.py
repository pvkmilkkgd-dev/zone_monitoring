import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.begin() as c:
    # Горноуральский МО x2
    print("=== Горноуральский МО x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom) as pts
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Свердловская область' AND d.name LIKE '%Горноуральск%'
        ORDER BY ST_Area(d.geom::geography)
    """)).fetchall()
    for did, dname, area, pts in rows:
        print(f"  {dname} id={did} area={area} pts={pts}")
    
    # 9 km2 is a tiny fragment - delete it
    if len(rows) == 2 and rows[0][2] < 50:
        print(f"  DELETE tiny fragment: {rows[0][0]} ({rows[0][2]}km2)")
        c.execute(text("DELETE FROM districts WHERE id = :id"), {'id': str(rows[0][0])})

    # Also fix Партизанский: ОКТМО says "муниципальный округ город Партизанск"
    # We set it to "город Партизанск" but ОКТМО has it as "муниципальный округ город Партизанск"
    print("\n=== Партизанск check ===")
    rows = c.execute(text("""
        SELECT d.id, d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Приморский край' AND d.name LIKE '%Партизан%'
        ORDER BY d.name
    """)).fetchall()
    for did, dname in rows:
        print(f"  {dname} id={did}")
    # "муниципальный округ город Партизанск" is the official ОКТМО name
    c.execute(text("""
        UPDATE districts SET name = 'муниципальный округ город Партизанск'
        WHERE name = 'город Партизанск' AND region_id IN (
            SELECT id FROM regions WHERE name = 'Приморский край'
        )
        RETURNING name
    """))

# Final check
print("\n=== Final duplicate check ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name, COUNT(*)
        FROM districts d JOIN regions r ON d.region_id = r.id
        GROUP BY d.name, r.name HAVING COUNT(*) > 1
        ORDER BY r.name
    """)).fetchall()
    if rows:
        for dname, rname, cnt in rows:
            print(f"  [{rname}] {dname} x{cnt}")
    else:
        print("  Дубликатов нет!")

print("\nDone!")
