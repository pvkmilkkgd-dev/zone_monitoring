"""Diagnose DNR districts - check geometry status for all."""
import sqlalchemy as sa

engine = sa.create_engine("postgresql://postgres:postgres@localhost:5432/zone_monitoring")

with engine.connect() as conn:
    rows = conn.execute(sa.text("""
        SELECT d.id, d.name,
               CASE WHEN d.geom IS NULL THEN 'NO GEOM'
                    WHEN ST_IsEmpty(d.geom) THEN 'EMPTY'
                    WHEN ST_NPoints(d.geom) = 0 THEN '0 PTS'
                    ELSE 'OK'
               END as status,
               CASE WHEN d.geom IS NOT NULL AND NOT ST_IsEmpty(d.geom)
                    THEN ROUND(ST_Area(d.geom::geography)/1000000)
                    ELSE 0
               END as area_km2,
               CASE WHEN d.geom IS NOT NULL AND NOT ST_IsEmpty(d.geom)
                    THEN ST_NPoints(d.geom)
                    ELSE 0
               END as npoints
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
        ORDER BY status, d.name
    """)).fetchall()

    print(f"Total districts: {len(rows)}")
    ok = sum(1 for r in rows if r[2] == 'OK')
    no_geom = sum(1 for r in rows if r[2] == 'NO GEOM')
    empty = sum(1 for r in rows if r[2] in ('EMPTY', '0 PTS'))
    print(f"OK: {ok}, NO GEOM: {no_geom}, EMPTY/0PTS: {empty}")
    print()
    for r in rows:
        print(f"{str(r[0]):36s} | {r[1]:50s} | {r[2]:8s} | {int(r[3]):8d} km2 | {r[4]:6d} pts")
