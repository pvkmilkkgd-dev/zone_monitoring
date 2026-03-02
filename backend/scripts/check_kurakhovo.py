import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring')
REGION = 'Донецкая Народная Республика'

with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT d.name,
               ST_NumGeometries(d.geom) as num_parts,
               ST_NPoints(d.geom) as pts,
               ROUND(ST_Area(d.geom::geography)/1e6) as area_km2,
               ROUND(ST_XMin(d.geom)::numeric, 2) as xmin,
               ROUND(ST_YMin(d.geom)::numeric, 2) as ymin,
               ROUND(ST_XMax(d.geom)::numeric, 2) as xmax,
               ROUND(ST_YMax(d.geom)::numeric, 2) as ymax
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = 'Кураховский муниципальный округ'
    """), {"region": REGION}).fetchone()

    print(f"Район: {row[0]}")
    print(f"Частей (MultiPolygon): {row[1]}")
    print(f"Точек: {row[2]}")
    print(f"Площадь: {int(row[3])} km2")
    print(f"BBox: [{row[4]}, {row[5]}, {row[6]}, {row[7]}]")

    # Check each part
    parts = conn.execute(text("""
        SELECT g.path[1] as part_num,
               ST_NPoints(g.geom) as pts,
               ROUND(ST_Area(g.geom::geography)/1e6) as area_km2,
               ROUND(ST_X(ST_Centroid(g.geom))::numeric, 2) as cx,
               ROUND(ST_Y(ST_Centroid(g.geom))::numeric, 2) as cy
        FROM districts d
        JOIN regions r ON d.region_id = r.id,
        LATERAL ST_Dump(d.geom) AS g
        WHERE r.name = :region AND d.name = 'Кураховский муниципальный округ'
        ORDER BY ST_Area(g.geom::geography) DESC
    """), {"region": REGION}).fetchall()

    print(f"\nЧасти геометрии:")
    for p in parts:
        print(f"  Часть {p[0]}: {p[1]} pts, {float(p[2]):.1f} km2, центр=({p[3]}, {p[4]})")
