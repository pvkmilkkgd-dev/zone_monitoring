# -*- coding: utf-8 -*-
"""
Удалить из Бабаюртовского осколки Гумбетовского и Хунзахского:
территория Гумбетовского и Хунзахского, лежащая внутри Бабаюртовского,
вычитается из Бабаюртовского (Гумбетовский и Хунзахский не меняем).
"""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"

with engine.begin() as conn:
    conn.execute(
        text("""
            WITH babay AS (
                SELECT d.geom AS g FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = 'Бабаюртовский муниципальный район'
            ),
            gumbet AS (
                SELECT d.geom AS g FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = 'Гумбетовский муниципальный район'
            ),
            khunzakh AS (
                SELECT d.geom AS g FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = 'Хунзахский муниципальный район'
            ),
            to_cut AS (
                SELECT ST_Union(geom) AS geom FROM (
                    SELECT ST_Intersection(g.g, b.g) AS geom FROM gumbet g, babay b
                    UNION ALL
                    SELECT ST_Intersection(k.g, b.g) FROM khunzakh k, babay b
                ) t
            ),
            new_babay AS (
                SELECT ST_Multi(ST_MakeValid(ST_Difference(b.g, COALESCE(c.geom, ST_GeomFromText('POLYGON EMPTY', 4326))))) AS geom
                FROM babay b, to_cut c
            )
            UPDATE districts SET geom = nb.geom
            FROM new_babay nb, districts d JOIN regions r ON d.region_id = r.id
            WHERE districts.id = d.id AND r.name = :region AND d.name = 'Бабаюртовский муниципальный район'
        """),
        {"region": REGION},
    )

print("OK: из Бабаюртовского вычтена территория Гумбетовского и Хунзахского (осколки удалены).")
