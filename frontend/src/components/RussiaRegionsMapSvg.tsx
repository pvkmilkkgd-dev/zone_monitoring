import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";

const DEBUG_MAP = true;

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
  "Ханты-Мансийский автономный округ — Югра": "Ханты-Мансийский автономный округ - Югра",
  "Республика Северная Осетия — Алания": "Северная Осетия - Алания",
};

const GEO_TO_UI: Record<string, string> = Object.fromEntries(
  Object.entries(UI_TO_GEO).map(([ui, geo]) => [geo, ui]),
);

function unwrapDatelineIfNeeded(fc: GeoFC): GeoFC {
  let minLon = Infinity;
  let maxLon = -Infinity;

  const scan = (coords: any) => {
    if (!coords) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const lon = coords[0];
      if (Number.isFinite(lon)) {
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
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

type MapProps = {
  selectedRegions: string[];
  width?: number;
  height?: number;
  padding?: number;
  onRegionClick?: (name: string) => void;
};

const loadingText = "Загрузка карты…";
const errorPrefix = "Ошибка загрузки карты: ";

export function RussiaRegionsMapSvg({ selectedRegions, width, height, padding = 12, onRegionClick }: MapProps) {
  const [geo, setGeo] = useState<GeoFC | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  const selectedGeoRegions = useMemo(
    () => (selectedRegions ?? []).map((s) => UI_TO_GEO[s.trim()] ?? s.trim()),
    [selectedRegions],
  );

  const backend = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "";
  const url = backend ? `${backend}/maps/ru/regions.geojson` : `/maps/ru/regions.geojson`;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoadError(null);
        const resp = await fetch(url, { cache: "no-store" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status} при загрузке ${url}`);

        const ct = resp.headers.get("content-type") || "";
        if (!ct.includes("application/json") && !ct.includes("geo+json")) {
          const text = await resp.text();
          throw new Error(
            `Ожидали GeoJSON, но получили не JSON (content-type=${ct}). Превью: ${text.slice(0, 40)}`,
          );
        }

        const raw = (await resp.json()) as GeoFC;
        const data = raw;

        const names = (data.features ?? [])
          .map((f) =>
            String(
              (f.properties as any)?.name ??
                (f.properties as any)?.NAME ??
                (f.properties as any)?.region ??
                "",
            ).trim(),
          )
          .filter(Boolean);
        const uniq = Array.from(new Set(names)).sort((a, b) => a.localeCompare(b));
        const missing = selectedGeoRegions.filter((r) => !uniq.includes(r));
        console.log("[MAP] geojson regions:", uniq);
        console.log("[MAP] selected missing in geojson:", missing);

        if (!cancelled) setGeo(data);
      } catch (e: any) {
        if (!cancelled) setLoadError(e?.message || "Не удалось загрузить GeoJSON");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [url, selectedGeoRegions]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width: w, height: h } = entry.contentRect;
      setSize({ w: Math.max(0, w), h: Math.max(0, h) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const measuredW = size.w || (width ?? 0);
  const measuredH = size.h || (height ?? 0);
  const svgWidth = Math.max(1, Math.floor(measuredW));
  const svgHeight = Math.max(1, Math.floor(measuredH));

  const { featuresToDraw, projection } = useMemo(() => {
    if (!geo) return { featuresToDraw: [] as GeoFeature[], projection: null as any };
    if (svgWidth < 50 || svgHeight < 50) return { featuresToDraw: [] as GeoFeature[], projection: null as any };

    const all = geo.features || [];
    const featuresToUse = all; // рисуем всю Россию, подсветка только по selected

    const pad = Math.min(padding, Math.floor(Math.min(svgWidth, svgHeight) / 10));
    const right = Math.max(pad + 1, svgWidth - pad);
    const bottom = Math.max(pad + 1, svgHeight - pad);
    const fitFc: GeoFC = { type: "FeatureCollection", features: all };
    const proj = geoMercator().rotate([-105, 0]).fitExtent(
      [
        [pad, pad],
        [right, bottom],
      ],
      fitFc as any,
    );

    return { featuresToDraw: featuresToUse, projection: proj };
  }, [geo, svgWidth, svgHeight, padding]);

  const pathGen = useMemo(() => (projection ? geoPath(projection) : null), [projection]);

  const selectedSet = new Set(selectedGeoRegions);
  const strokeWidth = selectedGeoRegions.length ? 1.5 : 0.8;

  if (DEBUG_MAP && pathGen) {
    try {
      const fcBounds = pathGen.bounds({ type: "FeatureCollection", features: geo?.features || [] } as any);
      let selBounds: [number, number][] | null = null;
      const firstSel = (geo.features || []).find((f) => selectedSet.has(getFeatureName(f)));
      if (firstSel) {
        selBounds = pathGen.bounds(firstSel as any);
      }
      console.log("[MAP DEBUG] svg size:", { svgWidth, svgHeight });
      console.log("[MAP DEBUG] bounds(all/fit):", fcBounds);
      if (selBounds) console.log("[MAP DEBUG] bounds(selected):", selBounds);
    } catch (e) {
      console.warn("[MAP DEBUG] bounds error", e);
    }
  }

  const showLoading = !geo || !pathGen || svgWidth < 50 || svgHeight < 50;

  return (
    <div ref={containerRef} className="w-full h-full min-w-0 relative">
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        preserveAspectRatio="xMidYMid meet"
        className="w-full h-full block"
        style={{ display: "block" }}
      >
        <rect x="0" y="0" width={svgWidth} height={svgHeight} fill="rgba(255,255,255,0.96)" stroke="none" />
        {pathGen && featuresToDraw.length
          ? featuresToDraw.map((f, idx) => {
              const name = getFeatureName(f);
              const isSelected = selectedSet.has(name);

              return (
                <path
                  key={`${name}-${idx}`}
                  d={pathGen ? pathGen(f as any) || "" : ""}
                  fill={
                    selectedGeoRegions.length ? (isSelected ? "rgba(14,165,233,0.25)" : "transparent") : "transparent"
                  }
                  stroke="rgba(15,23,42,0.35)"
                  strokeWidth={strokeWidth}
                  className="cursor-pointer transition-colors hover:fill-[rgba(14,165,233,0.12)]"
                  fillRule="evenodd"
                  clipRule="evenodd"
                  onClick={() => {
                    if (!name) return;
                    const uiName = GEO_TO_UI[name] ?? name;
                    onRegionClick?.(uiName);
                  }}
                >
                  <title>{name || "Без названия"}</title>
                </path>
              );
            })
          : null}
      </svg>

      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center px-4 text-xs text-slate-600 bg-transparent">
          {errorPrefix}
          {loadError}
        </div>
      )}

      {!loadError && showLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500 bg-transparent">
          {loadingText}
        </div>
      )}
    </div>
  );
}

type CardProps = {
  selectedRegions: string[];
  padding?: number;
  onRegionClick?: (name: string) => void;
};

export function RussiaRegionsMapCard({ selectedRegions, padding = 12, onRegionClick }: CardProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });

  useEffect(() => {
    if (!ref.current) return;

    const ro = new ResizeObserver(([entry]) => {
      const cr = entry.contentRect;
      setSize({ w: Math.max(1, cr.width), h: Math.max(1, cr.height) });
    });

    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  return (
    <div className="w-full h-full">
      <div ref={ref} className="w-full h-full">
        <RussiaRegionsMapSvg
          selectedRegions={selectedRegions}
          width={size.w}
          height={size.h}
          padding={padding}
          onRegionClick={onRegionClick}
        />
      </div>
    </div>
  );
}
