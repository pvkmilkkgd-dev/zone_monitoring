import { useEffect, useMemo, useRef, useState } from "react";

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
  selectedRegionIds: string[]; // UUID[]
  onRegionClick?: (regionId: string) => void;
  resolveRegionId?: (regionName: string) => string | undefined; // name -> UUID
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

export function RussiaRegionsMapSvg({
  selectedRegionIds,
  onRegionClick,
  resolveRegionId,
  padding = 10,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const [fc, setFc] = useState<GeoJSONFeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentVB, setCurrentVB] = useState<ViewBox | null>(null);
  const [svgSize, setSvgSize] = useState({ w: 0, h: 0 });
  const initializedRef = useRef(false);
  const prevTargetVBRef = useRef<ViewBox | null>(null);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;

    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr) return;
      setSvgSize({ w: cr.width, h: cr.height });
    });

    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const ac = new AbortController();

    (async () => {
      try {
        setError(null);
        // Добавляем кеш-бастинг для обновления данных после загрузки нового региона
        const cacheBuster = `?t=${Date.now()}`;
        const res = await fetch(`/maps/ru/regions.geojson${cacheBuster}`, { 
          signal: ac.signal,
          cache: "no-cache"
        });
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
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

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
    
    // Увеличиваем вертикальный padding для более вертикального вида карты
    // Горизонтальный padding остается стандартным, вертикальный увеличен
    const horizontalPad = padding;
    const verticalPad = padding * 2; // Увеличенный вертикальный padding
    
    const vbW = w + horizontalPad * 2;
    const vbH = h + verticalPad * 2;

    const mapXY = (pt: LonLat): [number, number] => {
      const [x, y] = project(pt);
      return [x - bbox.minX + horizontalPad, y - bbox.minY + verticalPad];
    };

    return { vbW, vbH, mapXY };
  }, [bbox, padding]);

  const paths = useMemo(() => {
    if (!fc || !view || !bbox) return [];

    return fc.features
      .map((f) => {
        const name = String(f.properties?.name ?? "");
        const fallbackId = String(f.properties?.id ?? name);
        const resolvedId = resolveRegionId?.(name);
        const id = resolvedId ?? fallbackId; // ожидаем UUID

        const d = buildPath(f.geometry, view.mapXY);

        let fMinX = Infinity;
        let fMinY = Infinity;
        let fMaxX = -Infinity;
        let fMaxY = -Infinity;

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
          id,
          name,
          d,
          box: hasBox ? { minX: fMinX, minY: fMinY, maxX: fMaxX, maxY: fMaxY } : null,
        };
      })
      .filter((p) => p.name && p.d);
  }, [fc, view, bbox, padding, resolveRegionId]);

  const fullVB = useMemo<ViewBox | null>(() => {
    if (!view) return null;
    return {
      x: 0,
      y: 0,
      w: view.vbW,
      h: view.vbH,
    };
  }, [view]);

  const targetVB = useMemo<ViewBox | null>(() => {
    if (!view || !fullVB) return null;
    if (!selectedRegionIds?.length) return fullVB;

    const selectedBoxes = selectedRegionIds
      .map((id) => paths.find((p) => p.id === id)?.box)
      .filter(Boolean) as Array<{ minX: number; minY: number; maxX: number; maxY: number }>;

    if (selectedBoxes.length === 0) return fullVB;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (const b of selectedBoxes) {
      if (b.minX < minX) minX = b.minX;
      if (b.minY < minY) minY = b.minY;
      if (b.maxX > maxX) maxX = b.maxX;
      if (b.maxY > maxY) maxY = b.maxY;
    }

    const w = maxX - minX;
    const h = maxY - minY;

    // Вычисляем размер региона относительно полной карты для определения, мелкий ли он
    const regionArea = w * h;
    const fullMapArea = view.vbW * view.vbH;
    const regionSizeRatio = regionArea / fullMapArea;
    
    // Определяем, мелкий ли регион (если занимает меньше 2% площади карты)
    const isSmallRegion = regionSizeRatio < 0.02;
    // Определяем, большой ли регион (если занимает больше 3% площади карты)
    // Для больших регионов применяем только фокусировку без приближения
    const isLargeRegion = regionSizeRatio > 0.03;
    
    // Для мелких регионов применяем большой zoom (уменьшаем viewBox)
    // Для больших регионов применяем только фокусировку без приближения (zoomFactor = 1.0)
    // Для средних регионов применяем небольшое приближение
    const zoomFactor = isSmallRegion ? 0.75 : (isLargeRegion ? 1.0 : 0.95);

    // Используем динамический padding для лучшей видимости
    const pad = Math.max(18, Math.min(w, h) * 0.1); // Минимум 18, или 10% от меньшего размера

    // Вычисляем центр выбранной области
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    // Начальные размеры viewBox с padding
    // Для больших регионов используем только фокусировку без изменения размера
    let vw: number;
    let vh: number;
    
    if (isLargeRegion) {
      // Для больших регионов: используем размер региона с минимальным padding, без приближения
      vw = w + pad * 2;
      vh = h + pad * 2 * 0.7; // Минимальный вертикальный padding
    } else {
      // Для мелких и средних регионов: применяем zoom с padding
      const verticalPadMultiplier = 0.7; // Уменьшаем вертикальный padding на 30% для всех регионов
      vw = (w + pad * 2) * zoomFactor;
      vh = (h + pad * 2 * verticalPadMultiplier) * zoomFactor;
    }

    // Создаем viewBox с центром на выбранной области
    // Смещаем центр вверх, чтобы регион был выше на карте
    // Увеличиваем координату Y viewBox, чтобы регион поднялся выше
    const verticalOffset = 0.25; // Смещение центра вверх на 25% высоты viewBox
    let clamped: ViewBox = {
      x: centerX - vw / 2,
      y: centerY - vh / 2 + vh * verticalOffset, // Увеличиваем Y, чтобы поднять регион выше
      w: vw,
      h: vh,
    };

    // Приоритетная логика центрирования: сначала центрируем на выбранной области
    // Центрируем viewBox на выбранной области без учета границ, со смещением вверх
    clamped.x = centerX - clamped.w / 2;
    clamped.y = centerY - clamped.h / 2 + clamped.h * verticalOffset; // Увеличиваем Y, чтобы поднять регион выше
    
    // Затем корректируем только если viewBox выходит за пределы карты
    // Но стараемся сохранить центр видимым
    if (clamped.w <= view.vbW) {
      // ViewBox уже карты - корректируем только границы
      if (clamped.x < 0) {
        clamped.x = 0;
      } else if (clamped.x + clamped.w > view.vbW) {
        clamped.x = view.vbW - clamped.w;
      }
    } else {
      // ViewBox шире карты - обрезаем, но центрируем на выбранной области
      clamped.w = view.vbW;
      clamped.x = Math.max(0, Math.min(centerX - clamped.w / 2, view.vbW - clamped.w));
    }
    
    if (clamped.h <= view.vbH) {
      // ViewBox ниже карты - корректируем только границы
      if (clamped.y < 0) {
        clamped.y = 0;
      } else if (clamped.y + clamped.h > view.vbH) {
        clamped.y = view.vbH - clamped.h;
      }
    } else {
      // ViewBox выше карты - обрезаем, но центрируем на выбранной области
      clamped.h = view.vbH;
      clamped.y = Math.max(0, Math.min(centerY - clamped.h / 2, view.vbH - clamped.h));
    }
    
    // Финальная проверка: убеждаемся, что центр выбранной области всегда виден
    // Это критично, если после всех корректировок центр не виден
    if (centerX < clamped.x || centerX > clamped.x + clamped.w) {
      clamped.x = Math.max(0, Math.min(centerX - clamped.w / 2, view.vbW - clamped.w));
    }
    if (centerY < clamped.y || centerY > clamped.y + clamped.h) {
      // Сохраняем смещение вверх при корректировке
      clamped.y = Math.max(0, Math.min(centerY - clamped.h / 2 + clamped.h * verticalOffset, view.vbH - clamped.h));
    }

    if (!isFinite(clamped.x) || !isFinite(clamped.y) || clamped.w <= 0 || clamped.h <= 0) return fullVB;

    return clamped;
  }, [selectedRegionIds, paths, view, fullVB]);

  // Инициализация currentVB только один раз при появлении fullVB
  useEffect(() => {
    if (fullVB && !initializedRef.current) {
      setCurrentVB(fullVB);
      initializedRef.current = true;
    }
  }, [fullVB]);

  useEffect(() => {
    if (!targetVB || !currentVB) return;

    // Проверяем, изменился ли targetVB по сравнению с предыдущим значением
    const prev = prevTargetVBRef.current;
    if (prev) {
      const prevSame =
        Math.abs(prev.x - targetVB.x) < 0.001 &&
        Math.abs(prev.y - targetVB.y) < 0.001 &&
        Math.abs(prev.w - targetVB.w) < 0.001 &&
        Math.abs(prev.h - targetVB.h) < 0.001;
      
      if (prevSame) {
        // targetVB не изменился, проверяем текущее состояние
        const currentSame =
          Math.abs(currentVB.x - targetVB.x) < 0.001 &&
          Math.abs(currentVB.y - targetVB.y) < 0.001 &&
          Math.abs(currentVB.w - targetVB.w) < 0.001 &&
          Math.abs(currentVB.h - targetVB.h) < 0.001;
        
        if (currentSame) return; // Уже достигли целевого состояния
      }
    }

    // Сохраняем текущий targetVB для следующей проверки
    prevTargetVBRef.current = targetVB;

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

  const isOverview = !selectedRegionIds?.length;

  // Для общего вида используем "none" чтобы карта растягивалась по вертикали без сохранения пропорций
  // Для выбранных регионов тоже используем "none", так как viewBox уже адаптирован под пропорции контейнера
  const preserveAspectRatioValue = "xMidYMid meet";

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
    <div ref={hostRef} className="w-full h-full">
      <svg
        ref={svgRef}
        className="w-full h-full"
        viewBox={vbToString(currentVB)}
        preserveAspectRatio={preserveAspectRatioValue}
      >
        <g>
          {paths.map(({ id, name, d }) => {
            const known = Boolean(id);
            const active = known && selectedRegionIds.includes(id);

            return (
              <path
                key={id || name}
                d={d}
                vectorEffect="non-scaling-stroke"
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
                strokeWidth={0.25}
                shapeRendering="geometricPrecision"
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
    </div>
  );
}
