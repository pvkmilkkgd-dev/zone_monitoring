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
  width: number;
  height: number;
  padding?: number;
};

const loadingText = "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u0430\u0440\u0442\u044b\u2026"; // Загрузка карты…
const errorPrefix = "\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u043a\u0430\u0440\u0442\u044b: "; // Ошибка загрузки карты:

export function RussiaRegionsMapSvg({ selectedRegions, width, height, padding = 12 }: MapProps) {
  const [geo, setGeo] = useState<GeoFC | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

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
        const data = unwrapDatelineIfNeeded(raw);

        if (!cancelled) setGeo(data);
      } catch (e: any) {
        if (!cancelled) setLoadError(e?.message || "Не удалось загрузить GeoJSON");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [url]);

  const svgWidth = Math.max(1, Math.floor(width));
  const svgHeight = Math.max(1, Math.floor(height));

  const { featuresToDraw, projection } = useMemo(() => {
    if (!geo) return { featuresToDraw: [] as GeoFeature[], projection: null as any };

    const all = geo.features || [];
    const chosen = new Set(selectedRegions.map((s) => s.trim()));
    const filtered = selectedRegions.length ? all.filter((f) => chosen.has(getFeatureName(f))) : all;
    const featuresToUse = filtered.length ? filtered : all;

    const pad = selectedRegions.length ? 6 : padding;
    const fitFc: GeoFC = { type: "FeatureCollection", features: featuresToUse };
    const x1 = Math.max(pad + 1, svgWidth - pad);
    const y1 = Math.max(pad + 1, svgHeight - pad);
    const proj = geoMercator()
      .rotate([-105, 0])
      .fitExtent(
        [
          [pad, pad],
          [x1, y1],
        ],
        fitFc as any,
      );

    return { featuresToDraw: featuresToUse, projection: proj };
  }, [geo, selectedRegions, svgWidth, svgHeight, padding]);

  const pathGen = useMemo(() => {
    if (!projection) return null;
    return geoPath(projection);
  }, [projection]);

  if (loadError) {
    return (
      <div className="h-full w-full flex items-center justify-center px-4 text-xs text-slate-600">
        {errorPrefix}
        {loadError}
      </div>
    );
  }

  if (!geo || !pathGen) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-slate-500">
        {loadingText}
      </div>
    );
  }

  const selectedSet = new Set(selectedRegions.map((s) => s.trim()));
  const strokeWidth = selectedRegions.length ? 1.5 : 0.8;

  return (
    <svg
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full block"
    >
      <rect x="0" y="0" width={svgWidth} height={svgHeight} fill="white" />

      {featuresToDraw.map((f, idx) => {
        const name = getFeatureName(f);
        const isSelected = selectedSet.has(name);

        return (
          <path
            key={`${name}-${idx}`}
            d={pathGen(f as any) || ""}
            fill={selectedRegions.length ? (isSelected ? "rgba(14,165,233,0.22)" : "transparent") : "transparent"}
            stroke="rgba(100,116,139,0.55)"
            strokeWidth={strokeWidth}
          >
            <title>{name || "Без названия"}</title>
          </path>
        );
      })}
    </svg>
  );
}

export function RussiaRegionsMapCard(props: { selectedRegions: string[]; padding?: number }) {
  const { selectedRegions, padding = 12 } = props;
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
    <div className="w-full rounded-2xl bg-white">
      <div ref={ref} className="w-full min-h-[520px] h-[60vh] max-h-[780px] p-4">
        <RussiaRegionsMapSvg selectedRegions={selectedRegions} width={size.w} height={size.h} padding={padding} />
      </div>
    </div>
  );
}
