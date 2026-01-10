import { useEffect, useMemo, useState } from "react";

type LonLat = [number, number];

// GeoJSON (минимально нужные типы)
type GeoJSONFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
};

type GeoJSONFeature = {
  type: "Feature";
  properties?: {
    id?: number | string;
    name?: string;
    [k: string]: any;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: LonLat[][] | LonLat[][][];
  };
};

type Props = {
  selectedRegionIds: string[];
  onRegionClick?: (regionId: string) => void;
  resolveRegionId?: (regionName: string) => string | undefined;
  padding?: number;
};

function walkCoords(geom: GeoJSONFeature["geometry"], cb: (pt: LonLat) => void) {
  if (geom.type === "Polygon") {
    const poly = geom.coordinates as LonLat[][];
    for (const ring of poly) for (const pt of ring) cb(pt);
  } else {
    const mp = geom.coordinates as LonLat[][][];
    for (const poly of mp) for (const ring of poly) for (const pt of ring) cb(pt);
  }
}

// простая проекция: lon -> x, lat -> y (но y переворачиваем, чтобы север был сверху)
function project([lon, lat]: LonLat): [number, number] {
  return [lon, -lat];
}

function buildPath(geom: GeoJSONFeature["geometry"], mapXY: (pt: LonLat) => [number, number]) {
  const ringToPath = (ring: LonLat[]) => {
    if (!ring.length) return "";
    const [x0, y0] = mapXY(ring[0]);
    let d = `M ${x0.toFixed(2)} ${y0.toFixed(2)}`;
    for (let i = 1; i < ring.length; i++) {
      const [x, y] = mapXY(ring[i]);
      d += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
    }
    d += " Z";
    return d;
  };

  if (geom.type === "Polygon") {
    const poly = geom.coordinates as LonLat[][];
    return poly.map(ringToPath).join(" ");
  } else {
    const mp = geom.coordinates as LonLat[][][];
    return mp.map((poly) => poly.map(ringToPath).join(" ")).join(" ");
  }
}

export function RussiaRegionsMapSvg({ selectedRegionIds, onRegionClick, resolveRegionId, padding = 10 }: Props) {
  const [fc, setFc] = useState<GeoJSONFeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();

    (async () => {
      try {
        setError(null);
        const res = await fetch("/maps/ru/regions.geojson", { signal: ac.signal });
        if (!res.ok) throw new Error(`GeoJSON HTTP ${res.status}`);
        const data = (await res.json()) as GeoJSONFeatureCollection;
        setFc(data);
      } catch (e: any) {
        if (e?.name === "AbortError") return;
        setError(e?.message ?? "Ошибка загрузки карты");
      }
    })();

    return () => ac.abort();
  }, []);

  // вычисляем bbox в проекции
  const bbox = useMemo(() => {
    if (!fc) return null;
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    for (const f of fc.features) {
      walkCoords(f.geometry, (pt) => {
        const [x, y] = project(pt);
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      });
    }

    if (!isFinite(minX)) return null;
    return { minX, minY, maxX, maxY };
  }, [fc]);

  // задаём виртуальный размер svg (viewBox) — компонент сам растянется в контейнере
  const view = useMemo(() => {
    if (!bbox) return null;
    const w = bbox.maxX - bbox.minX;
    const h = bbox.maxY - bbox.minY;
    const vbW = w + padding * 2;
    const vbH = h + padding * 2;

    // функция перевода lon/lat -> координаты внутри viewBox
    const mapXY = (pt: LonLat): [number, number] => {
      const [x, y] = project(pt);
      return [x - bbox.minX + padding, y - bbox.minY + padding];
    };

    return { vbW, vbH, mapXY };
  }, [bbox, padding]);

  const paths = useMemo(() => {
    if (!fc || !view) return [];
    return fc.features
      .map((f) => {
        const name = String(f.properties?.name ?? "").trim();
        const resolvedId = resolveRegionId?.(name);
        const id = resolvedId ?? name;
        const d = buildPath(f.geometry, view.mapXY);
        return { id, name, d };
      })
      .filter((p) => p.name && p.d);
  }, [fc, view, resolveRegionId]);

  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-red-200">
        {error}
      </div>
    );
  }

  if (!fc || !view) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-slate-300">
        Загрузка карты…
      </div>
    );
  }

  return (
    <svg className="w-full h-full" viewBox={`0 0 ${view.vbW} ${view.vbH}`} preserveAspectRatio="none">
      <g>
        {paths.map(({ id, name, d }) => {
          const known = Boolean(id);
          const active = known && selectedRegionIds.includes(id);
          return (
            <path
              key={id || name}
              d={d}
              fill={
                !known
                  ? "rgba(148,163,184,0.06)"
                  : active
                  ? "rgba(56,189,248,0.25)"
                  : "rgba(148,163,184,0.10)"
              }
              stroke={
                !known
                  ? "rgba(148,163,184,0.25)"
                  : active
                  ? "rgba(56,189,248,0.9)"
                  : "rgba(148,163,184,0.55)"
              }
              strokeWidth={0.35}
              fillRule="evenodd"
              className={known ? "cursor-pointer transition" : "cursor-default"}
              onClick={() => {
                if (known) onRegionClick?.(id);
              }}
            >
              <title>{name}</title>
            </path>
          );
        })}
      </g>
    </svg>
  );
}
