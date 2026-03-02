import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    r = c.execute(text(
        "SELECT id, name, ST_AsText(ST_Centroid(geom)), ST_Area(geom::geography)/1e6 "
        "FROM regions WHERE name LIKE '%Архангел%'"
    )).fetchone()
    print(f"Region: {r[1]}")
    print(f"Region centroid: {r[2]}")
    print(f"Region area: {r[3]:.0f} km2")
    rid = str(r[0])
    
    rows = c.execute(text(
        "SELECT name, "
        "ST_Area(geom::geography)/1e6 as area_km2, "
        "ST_AsText(ST_Centroid(geom)) as centroid, "
        "ST_NPoints(geom) as npts "
        "FROM districts WHERE region_id = :rid ORDER BY name"
    ), {"rid": rid}).fetchall()
    
    print(f"\nDistricts: {len(rows)}")
    total = 0
    for name, area, centroid, npts in rows:
        print(f"  {area:>10.0f} km2  {npts:>6} pts  {centroid[:40]:40s}  {name}")
        total += area
    print(f"\nTotal district area: {total:.0f} km2")
    print(f"Region area: {r[3]:.0f} km2")
    print(f"Coverage: {total/r[3]*100:.1f}%")
    
    # Check if Nenets AO districts are mixed in
    nen = c.execute(text(
        "SELECT id FROM regions WHERE name LIKE '%Ненец%'"
    )).fetchone()
    if nen:
        nen_cnt = c.execute(text(
            "SELECT COUNT(*) FROM districts WHERE region_id = :rid"
        ), {"rid": str(nen[0])}).fetchone()
        print(f"\nНенецкий АО: {nen_cnt[0]} districts (separate region)")
    
    # Check region geometry itself
    rgeom = c.execute(text(
        "SELECT ST_GeometryType(geom), ST_NPoints(geom), "
        "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
        "FROM regions WHERE id = :rid"
    ), {"rid": rid}).fetchone()
    print(f"\nRegion geometry: {rgeom[0]}, {rgeom[1]} points")
    print(f"Bbox: ({rgeom[2]:.2f}, {rgeom[3]:.2f}) - ({rgeom[4]:.2f}, {rgeom[5]:.2f})")
    
    # Check districts bbox
    dbbox = c.execute(text(
        "SELECT ST_XMin(ST_Extent(geom)), ST_YMin(ST_Extent(geom)), "
        "ST_XMax(ST_Extent(geom)), ST_YMax(ST_Extent(geom)) "
        "FROM districts WHERE region_id = :rid"
    ), {"rid": rid}).fetchone()
    print(f"Districts bbox: ({dbbox[0]:.2f}, {dbbox[1]:.2f}) - ({dbbox[2]:.2f}, {dbbox[3]:.2f})")
