import { useEffect, useMemo, useState } from "react";

type LonLat = [number, number];

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

type ViewBox = { x: number; y: number; w: number; h: number };
const vbToString = (v: ViewBox) => `${v.x} ${v.y} ${v.w} ${v.h}`;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function walkCoords(geom: GeoJSONFeature["geometry"], cb: (pt: LonLat) => void) {
  if (geom.type === "Polygon") {
    const poly = geom.coordinates as LonLat[][];
    for (const ring of poly) for (const pt of ring) cb(pt);
  } else {
    const mp = geom.coordinates as LonLat[][][];
    for (const poly of mp) for (const ring of poly) for (const pt of ring) cb(pt);
  }
}

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
  const [currentVB, setCurrentVB] = useState<ViewBox | null>(null);

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

  const view = useMemo(() => {
    if (!bbox) return null;
    const w = bbox.maxX - bbox.minX;
    const h = bbox.maxY - bbox.minY;
    const vbW = w + padding * 2;
    const vbH = h + padding * 2;

    const mapXY = (pt: LonLat): [number, number] => {
      const [x, y] = project(pt);
      return [x - bbox.minX + padding, y - bbox.minY + padding];
    };

    return { vbW, vbH, mapXY };
  }, [bbox, padding]);

  const paths = useMemo(() => {
    if (!fc || !view || !bbox) return [];

    const built = fc.features
      .map((f) => {
        const name = String(f.properties?.name ?? "");
        const rawId = String(f.properties?.id ?? name);
        const resolvedId = resolveRegionId?.(name);
        const finalId = resolvedId ?? rawId;

        const d = buildPath(f.geometry, view.mapXY);

        let fMinX = Infinity,
          fMinY = Infinity,
          fMaxX = -Infinity,
          fMaxY = -Infinity;

        walkCoords(f.geometry, (pt) => {
          const [x, y] = project(pt);
          const vx = x - bbox.minX + padding;
          const vy = y - bbox.minY + padding;

          if (vx < fMinX) fMinX = vx;
          if (vy < fMinY) fMinY = vy;
          if (vx > fMaxX) fMaxX = vx;
          if (vy > fMaxY) fMaxY = vy;
        });

        const hasBox = isFinite(fMinX) && isFinite(fMinY) && isFinite(fMaxX) && isFinite(fMaxY);

        return {
          id: finalId,
          name,
          d,
          box: hasBox ? { minX: fMinX, minY: fMinY, maxX: fMaxX, maxY: fMaxY } : null,
        };
      })
      .filter((p) => p.name && p.d);

    console.log("path ids:", built.slice(0, 5).map((p) => p.id));
    console.log("selected ids:", selectedRegionIds);
    return built;
  }, [fc, view, bbox, padding, resolveRegionId, selectedRegionIds]);

  const fullVB = useMemo<ViewBox | null>(() => {
    if (!view) return null;
    return { x: 0, y: 0, w: view.vbW, h: view.vbH };
  }, [view]);

  const targetVB = useMemo<ViewBox | null>(() => {
    if (!view || !fullVB) return null;
    if (!selectedRegionIds?.length) return fullVB;

    const selectedBoxes = selectedRegionIds
      .map((id) => paths.find((p) => p.id === id)?.box)
      .filter(Boolean) as Array<{ minX: number; minY: number; maxX: number; maxY: number }>;

    if (selectedBoxes.length === 0) return fullVB;

    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    for (const b of selectedBoxes) {
      if (b.minX < minX) minX = b.minX;
      if (b.minY < minY) minY = b.minY;
      if (b.maxX > maxX) maxX = b.maxX;
      if (b.maxY > maxY) maxY = b.maxY;
    }

    const pad = 18;
    const w = maxX - minX;
    const h = maxY - minY;

    let x = minX - pad;
    let y = minY - pad;
    let vw = w + pad * 2;
    let vh = h + pad * 2;

    const k = 1.12;
    vw *= k;
    vh *= k;
    x -= (vw - (w + pad * 2)) / 2;
    y -= (vh - (h + pad * 2)) / 2;

    const clamped: ViewBox = { x, y, w: vw, h: vh };

    if (clamped.x < 0) clamped.x = 0;
    if (clamped.y < 0) clamped.y = 0;
    if (clamped.x + clamped.w > view.vbW) clamped.x = view.vbW - clamped.w;
    if (clamped.y + clamped.h > view.vbH) clamped.y = view.vbH - clamped.h;

    if (!isFinite(clamped.x) || !isFinite(clamped.y) || clamped.w <= 0 || clamped.h <= 0) {
      return fullVB;
    }

    return clamped;
  }, [selectedRegionIds, paths, view, fullVB]);

  useEffect(() => {
    if (fullVB && !currentVB) setCurrentVB(fullVB);
  }, [fullVB, currentVB]);

  useEffect(() => {
    if (!targetVB || !currentVB) return;

    const same =
      Math.abs(currentVB.x - targetVB.x) < 0.001 &&
      Math.abs(currentVB.y - targetVB.y) < 0.001 &&
      Math.abs(currentVB.w - targetVB.w) < 0.001 &&
      Math.abs(currentVB.h - targetVB.h) < 0.001;

    if (same) return;

    const prefersReduced =
      typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

    if (prefersReduced) {
      setCurrentVB(targetVB);
      return;
    }

    const from = currentVB;
    const to = targetVB;
    const dur = 260;
    let raf = 0;
    const t0 = performance.now();

    const tick = (now: number) => {
      const raw = (now - t0) / dur;
      const t = Math.min(1, Math.max(0, raw));
      const e = easeInOutCubic(t);

      setCurrentVB({
        x: lerp(from.x, to.x, e),
        y: lerp(from.y, to.y, e),
        w: lerp(from.w, to.w, e),
        h: lerp(from.h, to.h, e),
      });

      if (t < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [targetVB]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-red-200">
        {error}
      </div>
    );
  }

  if (!fc || !view || !currentVB) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-slate-300">
        Загрузка карты…
      </div>
    );
  }

  return (
    <svg
      className="w-full h-full"
      viewBox={vbToString(currentVB)}
      preserveAspectRatio="none"
      shapeRendering="geometricPrecision"
    >
      <g>
        {paths.map(({ id, name, d }) => {
          const known = Boolean(id);
          const active = known && selectedRegionIds.includes(id);
          return (
            <path
              key={id || name}
              d={d}
              fill={active ? "rgba(56,189,248,0.18)" : "rgba(148,163,184,0.06)"}
              stroke={active ? "rgba(56,189,248,0.95)" : "rgba(148,163,184,0.80)"}
              strokeWidth={0.22}
              vectorEffect="non-scaling-stroke"
              strokeLinecap="square"
              strokeLinejoin="miter"
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
