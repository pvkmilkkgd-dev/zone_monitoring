import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";

type GeoFeature = {
  type: "Feature";
  properties?: Record<string, any>;
  geometry: any;
};

type GeoFC = {
  type: "FeatureCollection";
  features: GeoFeature[];
};

const UI_TO_GEO: Record<string, string> = {
  "Кабардино-Балкарская Республика": "Кабардино-Балкарская республика",
  "Карачаево-Черкесская Республика": "Карачаево-Черкесская республика",
  "Удмуртская Республика": "Удмуртская республика",
  "Чеченская Республика": "Чеченская республика",
  "Ханты-Мансийский автономный округ — Югра":
    "Ханты-Мансийский автономный округ - Югра",
  "Республика Северная Осетия — Алания":
    "Республика Северная Осетия - Алания",
};

const GEO_TO_UI: Record<string, string> = Object.fromEntries(
  Object.entries(UI_TO_GEO).map(([ui, geo]) => [geo, ui]),
);

function getFeatureName(f: GeoFeature): string {
  const p = f.properties || {};
  return (
    p.name_ru ||
    p.name ||
    p.NAME ||
    p.region ||
    p.subject ||
    p.NAME_1 ||
    ""
  )
    .toString()
    .trim();
}

/**
 * Аккуратно разворачиваем координаты по антимеридиану (±180),
 * чтобы кольца/линии не "рвались" и fitExtent не ужимал карту.
 */
function unwrapDatelineIfNeeded(fc: GeoFC): GeoFC {
  let minLon = Infinity;
  let maxLon = -Infinity;

  const scan = (coords: any) => {
    if (!coords) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const lon = coords[0];
      if (Number.isFinite(lon)) {
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
      }
      return;
    }
    for (const c of coords) scan(c);
  };

  for (const f of fc.features || []) scan((f as any)?.geometry?.coordinates);

  const span = maxLon - minLon;
  if (!Number.isFinite(span) || span < 300) return fc;

  const fix = (coords: any): any => {
    if (!coords) return coords;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const lon = coords[0];
      const lat = coords[1];
      if (Number.isFinite(lon) && lon < 0) return [lon + 360, lat];
      return [lon, lat];
    }
    return coords.map((c: any) => fix(c));
  };

  return {
    ...fc,
    features: (fc.features || []).map((f) => ({
      ...f,
      geometry: {
        ...(f as any).geometry,
        coordinates: fix((f as any).geometry?.coordinates),
      },
    })),
  };
}

type MapProps = {
  selectedRegions: string[];
  width?: number;
  height?: number;
  padding?: number;
  onRegionClick?: (name: string) => void;
};

export function RussiaRegionsMapSvg({
  selectedRegions,
  width,
  height,
  padding = 12,
  onRegionClick,
}: MapProps) {
  const [geo, setGeo] = useState<GeoFC | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const hostRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  const selectedGeoRegions = useMemo(
    () => (selectedRegions ?? []).map((s) => UI_TO_GEO[s.trim()] ?? s.trim()),
    [selectedRegions],
  );
  const selectedSet = useMemo(() => new Set(selectedGeoRegions), [selectedGeoRegions]);

  const backend = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "";
  const url = backend ? `${backend}/maps/ru/regions.geojson` : `/maps/ru/regions.geojson`;

  // Load GeoJSON
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoadError(null);

        const resp = await fetch(url, { cache: "no-store" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status} при загрузке ${url}`);

        const ct = resp.headers.get("content-type") || "";
        if (!ct.includes("application/json") && !ct.includes("geo+json")) {
          const text = await resp.text();
          throw new Error(
            `Ожидали GeoJSON, но получили не JSON (content-type=${ct}). Превью: ${text.slice(0, 80)}`,
          );
        }

        const raw = (await resp.json()) as GeoFC;
        const fixed = unwrapDatelineIfNeeded(raw);

        if (!cancelled) setGeo(fixed);
      } catch (e: any) {
        if (!cancelled) setLoadError(e?.message || "Не удалось загрузить GeoJSON");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [url]);

  // Measure container
  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;

    const ro = new ResizeObserver(([entry]) => {
      const { width: w, height: h } = entry.contentRect;
      setSize({ w: Math.max(0, w), h: Math.max(0, h) });
    });

    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const svgWidth = Math.max(1, Math.floor(size.w || width || 1));
  const svgHeight = Math.max(1, Math.floor(size.h || height || 1));

  const { pathGen, featuresToDraw } = useMemo(() => {
    if (!geo) return { pathGen: null as any, featuresToDraw: [] as GeoFeature[] };
    if (svgWidth < 40 || svgHeight < 40) return { pathGen: null as any, featuresToDraw: [] as GeoFeature[] };

    const features = geo.features || [];
    const fc: GeoFC = { type: "FeatureCollection", features };

    const pad = Math.min(padding, Math.floor(Math.min(svgWidth, svgHeight) / 10));
    const ZOOM = 1.85;
    const Y_SHIFT = 120;

    const proj = geoMercator()
      .rotate([-105, 0])
      .fitExtent(
        [
          [pad, pad],
          [svgWidth - pad, svgHeight - pad],
        ],
        fc as any,
      );

    // Увеличиваем зум и рецентрируем (с небольшим смещением вниз)
    proj.scale(proj.scale() * ZOOM);

    const p = geoPath(proj);
    const b = p.bounds(fc as any);
    const cx = (b[0][0] + b[1][0]) / 2;
    const cy = (b[0][1] + b[1][1]) / 2;
    const targetX = svgWidth / 2;
    const targetY = svgHeight / 2 + Y_SHIFT;
    const [tx, ty] = proj.translate();
    proj.translate([tx + (targetX - cx), ty + (targetY - cy)]);

    return { pathGen: geoPath(proj), featuresToDraw: features };
  }, [geo, svgWidth, svgHeight, padding]);

  // Светлое оформление на темной карточке
  const stroke = "rgba(226,232,240,0.70)";
  const strokeSelected = "rgba(125,211,252,0.95)";
  const fillSelected = "rgba(56,189,248,0.22)";
  const strokeWidth = selectedGeoRegions.length ? 1.2 : 0.8;

  return (
    <div ref={hostRef} className="w-full h-full min-w-0 relative">
      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center px-4 text-xs text-slate-400">
          Ошибка загрузки карты: {loadError}
        </div>
      )}

      {!loadError && (!geo || !pathGen) && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-400">
          Загрузка карты…
        </div>
      )}

      {!loadError && geo && pathGen && (
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          preserveAspectRatio="xMidYMid meet"
          className="block w-full h-full"
          style={{ display: "block" }}
        >
          {featuresToDraw.map((f, idx) => {
            const geoName = getFeatureName(f);
            const isSelected = selectedSet.has(geoName);

            return (
              <path
                key={`${geoName || "region"}-${idx}`}
                d={pathGen(f as any) || ""}
                fill={isSelected ? fillSelected : "transparent"}
                stroke={isSelected ? strokeSelected : stroke}
                strokeWidth={strokeWidth}
                vectorEffect="non-scaling-stroke"
                className="cursor-pointer transition-colors"
                fillRule="evenodd"
                clipRule="evenodd"
                onClick={() => {
                  if (!geoName) return;
                  const uiName = GEO_TO_UI[geoName] ?? geoName;
                  onRegionClick?.(uiName);
                }}
              >
                <title>{geoName || "Без названия"}</title>
              </path>
            );
          })}
        </svg>
      )}
    </div>
  );
}
