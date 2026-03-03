import React, { useEffect, useState, useRef, useMemo, useCallback } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
  Marker,
} from "react-simple-maps";
import { geoMercator } from "d3-geo";
import { requireAuth, handleAuthError, logout, canEdit, isAdmin } from "../utils/auth";
import { Modal } from "../components/Modal";
import { fetchSystemSettings, fetchCurrentUser } from "../api/admin";
import { getAdministrativeZones, type AdministrativeZone } from "../api/administrative-zones";
import { getEvents, getEvent, updateEvent, addEventComment, deleteEventComment, type EventListItem, type EventDetail } from "../api/events";
import { getLayers, type Layer } from "../api/layers";

type City = {
  name: string;
  population: number;
  lat: number;
  lon: number;
  importance: number;
};

type DistrictStats = {
  totalImportance: number;
  eventCount: number;
  maxImportance: number;
  avgImportance: number;
  integralScore: number; // Интегральная оценка района
};

export function SituationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noRegion, setNoRegion] = useState(false);
  
  // Данные карты
  const [mergedGeoJson, setMergedGeoJson] = useState<any>(null);
  const [regionName, setRegionName] = useState<string>("");
  const [departmentName, setDepartmentName] = useState<string>("");
  const [currentUserName, setCurrentUserName] = useState<string>("");
  
  // Данные
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  
  // Фильтр по слоям
  const [selectedLayerFilter, setSelectedLayerFilter] = useState<string>("all");
  
  // Зум карты
  const [zoom] = useState(1);
  const [currentZoom, setCurrentZoom] = useState(1);
  const [center, setCenter] = useState<[number, number]>([60.5, 59.5]);
  const [mapScale, setMapScale] = useState(2200);
  const [mapRotate, setMapRotate] = useState<[number, number, number] | undefined>(undefined);
  
  // Боковая панель
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  
  // Просмотр события
  const [selectedEvent, setSelectedEvent] = useState<EventDetail | null>(null);
  const [loadingEvent, setLoadingEvent] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [savingComment, setSavingComment] = useState(false);
  const [savingArchive, setSavingArchive] = useState(false);
  const [deletingCommentId, setDeletingCommentId] = useState<number | null>(null);
  
  // Фильтр слоя в панели
  const [panelLayerFilter, setPanelLayerFilter] = useState<string>("all");

  // Словарь статусов
  const STATUS_LABELS: Record<string, string> = {
    ok: "В норме",
    warning: "Внимание",
    alert: "Тревога",
  };

  // Получить название слоя по ID
  const getLayerName = (layerId: number | null, subLayerId: number | null, subSubLayerId: number | null): string => {
    if (!layerId && !subLayerId && !subSubLayerId) return "Не указан";
    
    for (const layer of layers) {
      if (subSubLayerId) {
        for (const sub of layer.sub_layers || []) {
          for (const subSub of sub.sub_sub_layers || []) {
            if (subSub.id === subSubLayerId) {
              return `${layer.name} → ${sub.name} → ${subSub.name}`;
            }
          }
        }
      }
      if (subLayerId) {
        for (const sub of layer.sub_layers || []) {
          if (sub.id === subLayerId) {
            return `${layer.name} → ${sub.name}`;
          }
        }
      }
      if (layer.id === layerId) {
        return layer.name;
      }
    }
    return "Не найден";
  };

  useEffect(() => {
    if (!requireAuth()) return;
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Загружаем данные текущего пользователя
      try {
        const user = await fetchCurrentUser();
        if (user?.full_name) {
          setCurrentUserName(user.full_name);
        } else if (user?.username) {
          setCurrentUserName(user.username);
        }
      } catch (e) {
        console.error("Failed to fetch current user:", e);
      }

      // Загружаем настройки
      const settings = await fetchSystemSettings();
      if (!settings || !settings.region_ids || settings.region_ids.length === 0) {
        setLoading(false);
        setNoRegion(true);
        return;
      }

      // Название управления
      if (settings.department_name) {
        setDepartmentName(settings.department_name);
      }

      const selectedIds = settings.region_ids.map(String);

      // Загружаем информацию о регионах
      const regionsResp = await fetch("/api/regions");
      if (regionsResp.ok) {
        const regions = await regionsResp.json();
        const selectedRegions = regions.filter((r: any) => selectedIds.includes(r.id));
        if (selectedRegions.length > 0) {
          setRegionName(selectedRegions.map((r: any) => r.name).join(", "));
        }
      }

      // Загружаем GeoJSON и города из ВСЕХ выбранных регионов параллельно
      const geoFetches = selectedIds.map(async (id) => {
        const resp = await fetch(`/maps/ru/region/${id}/districts.geojson?v=2`);
        if (!resp.ok) return null;
        return resp.json();
      });
      const cityFetches = selectedIds.map(async (id) => {
        try {
          const resp = await fetch(`/maps/ru/region/${id}/cities.json`);
          if (!resp.ok) return [];
          return resp.json();
        } catch { return []; }
      });
      const [geoJsons, citiesArrays] = await Promise.all([
        Promise.all(geoFetches).then(r => r.filter(Boolean)),
        Promise.all(cityFetches),
      ]);
      setCities(citiesArrays.flat());

      // Объединяем все features
      const allFeatures: any[] = [];
      geoJsons.forEach((gj: any) => {
        if (gj?.features) allFeatures.push(...gj.features);
      });

      const merged = { type: "FeatureCollection", features: allFeatures };
      setMergedGeoJson(merged);

      // Вычисляем центр и масштаб по объединённой геометрии
      if (allFeatures.length > 0) {
        let minLon = Infinity, minLat = Infinity;
        let maxLon = -Infinity, maxLat = -Infinity;

        const processCoords = (coords: any[]): void => {
          if (typeof coords[0] === 'number') {
            const [lon, lat] = coords;
            minLon = Math.min(minLon, lon);
            maxLon = Math.max(maxLon, lon);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
          } else {
            coords.forEach((item: any) => processCoords(item));
          }
        };

        allFeatures.forEach((f: any) => {
          const geom = f.geometry;
          if (!geom?.coordinates) return;
          if (geom.type === 'MultiPolygon') {
            geom.coordinates.forEach((p: any) => p.forEach((r: any) => r.forEach((c: any) => processCoords(c))));
          } else if (geom.type === 'Polygon') {
            geom.coordinates.forEach((r: any) => r.forEach((c: any) => processCoords(c)));
          } else {
            processCoords(geom.coordinates);
          }
        });

        if (minLon !== Infinity) {
          // API сдвигает координаты через ST_ShiftLongitude для антимеридиана
          const crossesAntimeridian = maxLon > 180;
          const centerLon = (minLon + maxLon) / 2;
          const mercatorY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI / 180) / 2));
          const mercYCenter = (mercatorY(minLat) + mercatorY(maxLat)) / 2;
          const centerLat = (2 * Math.atan(Math.exp(mercYCenter)) - Math.PI / 2) * 180 / Math.PI;

          const svgW = 800;
          const svgH = 600;
          const deltaLonRad = (maxLon - minLon) * Math.PI / 180;
          const deltaMercY = Math.abs(mercatorY(maxLat) - mercatorY(minLat));
          const scaleX = svgW / deltaLonRad;
          const scaleY = svgH / deltaMercY;
          const computedScale = Math.max(500, Math.min(80000, Math.round(Math.min(scaleX, scaleY) * 0.7)));
          setMapScale(computedScale);

          if (crossesAntimeridian) {
            const rotateLon = centerLon > 180 ? centerLon - 360 : centerLon;
            setCenter([0, centerLat]);
            setMapRotate([-rotateLon, 0, 0]);
          } else {
            setCenter([centerLon, centerLat]);
            setMapRotate(undefined);
          }
        }
      }
      
      // Загружаем данные
      const [zonesData, eventsData, layersData] = await Promise.all([
        getAdministrativeZones(),
        getEvents(),
        getLayers(),
      ]);
      
      setZones(zonesData);
      setEvents(eventsData);
      setLayers(layersData);
      
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  };

  // Фильтрованные события по выбранному слою
  const filteredEvents = useMemo(() => {
    if (selectedLayerFilter === "all") return events;
    
    const [type, id] = selectedLayerFilter.split("_");
    const layerId = parseInt(id);
    
    return events.filter(ev => {
      if (type === "layer") return ev.layer_id === layerId;
      if (type === "sub") return ev.sub_layer_id === layerId;
      if (type === "subsub") return ev.sub_sub_layer_id === layerId;
      return true;
    });
  }, [events, selectedLayerFilter]);

  // Статистика по районам (только актуальные события влияют на цвет)
  const districtStats = useMemo(() => {
    const stats: Record<string, DistrictStats> = {};
    
    // Фильтруем архивированные события - они не влияют на цвет района
    const activeEvents = filteredEvents.filter(ev => !ev.is_archived);
    
    activeEvents.forEach(ev => {
      if (!ev.district_name) return;
      
      if (!stats[ev.district_name]) {
        stats[ev.district_name] = {
          totalImportance: 0,
          eventCount: 0,
          maxImportance: 0,
          avgImportance: 0,
          integralScore: 0,
        };
      }
      
      stats[ev.district_name].totalImportance += ev.importance;
      stats[ev.district_name].eventCount += 1;
      stats[ev.district_name].maxImportance = Math.max(
        stats[ev.district_name].maxImportance,
        ev.importance
      );
    });
    
    // Вычисляем средние значения и интегральную оценку
    Object.keys(stats).forEach(name => {
      if (stats[name].eventCount > 0) {
        stats[name].avgImportance = stats[name].totalImportance / stats[name].eventCount;
        // Интегральная оценка: maxImportance + log2(eventCount + 1) * 0.5, max 10
        stats[name].integralScore = Math.min(
          10,
          stats[name].maxImportance + Math.log2(stats[name].eventCount + 1) * 0.5
        );
      }
    });
    
    return stats;
  }, [filteredEvents]);

  // Цвет района по важности (на основе интегральной оценки событий в районе)
  const getDistrictColor = useCallback((districtName: string) => {
    const stats = districtStats[districtName];
    if (!stats || stats.eventCount === 0) {
      return "#22c55e"; // Зелёный - нет событий (минимальный уровень)
    }
    
    // Используем интегральную оценку района (шкала 1-10)
    // Нормализуем: 1 = 0 (зелёный), 10 = 1 (красный)
    const normalized = (stats.integralScore - 1) / 9;
    
    // Градиент от зеленого к желтому к красному
    if (normalized < 0.5) {
      // Зелёный -> Жёлтый
      const t = normalized * 2;
      const r = Math.round(34 + (234 - 34) * t);
      const g = Math.round(197 + (179 - 197) * t);
      const b = Math.round(94 + (8 - 94) * t);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      // Жёлтый -> Красный
      const t = (normalized - 0.5) * 2;
      const r = Math.round(234 + (239 - 234) * t);
      const g = Math.round(179 + (68 - 179) * t);
      const b = Math.round(8 + (68 - 8) * t);
      return `rgb(${r}, ${g}, ${b})`;
    }
  }, [districtStats]);

  // Убираем пересечения подписей городов: приоритет у более важных и крупных городов
  const visibleCityLabels = useMemo(() => {
    const shouldShowByZoom = (importance: number, z: number) => {
      if (importance <= 3) return true;
      if (importance <= 8) return z >= 1.3;
      if (importance <= 15) return z >= 1.8;
      return z >= 2.5;
    };

    const baseFontSize = (importance: number) => {
      if (importance <= 1) return 11;
      if (importance <= 3) return 9;
      if (importance <= 8) return 8;
      return 7;
    };

    const projection = geoMercator().scale(mapScale).center(center);
    if (mapRotate) projection.rotate(mapRotate);

    const candidates = cities
      .filter((city) => shouldShowByZoom(city.importance, currentZoom))
      .sort((a, b) => a.importance - b.importance || b.population - a.population);

    const placedBoxes: Array<{ left: number; right: number; top: number; bottom: number }> = [];
    const result: Array<{ city: City; fontSize: number }> = [];

    for (const city of candidates) {
      const projected = projection([city.lon, city.lat]);
      if (!projected) continue;

      const [px, py] = projected;
      const x = px * currentZoom;
      const y = py * currentZoom;
      const fontSize = baseFontSize(city.importance) / currentZoom;
      const markerOffsetY = 4 / currentZoom;
      const labelWidth = city.name.length * fontSize * 0.62;
      const labelHeight = fontSize * 1.2;
      const padding = 2;

      const box = {
        left: x - labelWidth / 2 - padding,
        right: x + labelWidth / 2 + padding,
        top: y - markerOffsetY - labelHeight - padding,
        bottom: y - markerOffsetY + padding,
      };

      const overlaps = placedBoxes.some(
        (b) =>
          !(box.right < b.left || box.left > b.right || box.bottom < b.top || box.top > b.bottom)
      );
      if (overlaps) continue;

      placedBoxes.push(box);
      result.push({ city, fontSize });
    }

    return result;
  }, [cities, currentZoom, mapScale, center, mapRotate]);

  // Обработчик клика по району
  const handleDistrictClick = (districtName: string) => {
    setSelectedDistrict(districtName);
    setPanelOpen(true);
    setSelectedEvent(null);
    setPanelLayerFilter("all");
  };

  // Закрыть панель
  const closePanel = () => {
    setPanelOpen(false);
    setSelectedDistrict(null);
    setSelectedEvent(null);
  };

  // Получить ответственное подразделение
  const getResponsibleZone = (districtName: string) => {
    return zones.find(z => z.district_names.includes(districtName));
  };

  // События выбранного района
  const districtEvents = useMemo(() => {
    if (!selectedDistrict) return [];
    
    let evs = events.filter(ev => ev.district_name === selectedDistrict);
    
    // Фильтр по слою в панели
    if (panelLayerFilter !== "all") {
      const [type, id] = panelLayerFilter.split("_");
      const layerId = parseInt(id);
      
      evs = evs.filter(ev => {
        if (type === "layer") return ev.layer_id === layerId;
        if (type === "sub") return ev.sub_layer_id === layerId;
        if (type === "subsub") return ev.sub_sub_layer_id === layerId;
        return true;
      });
    }
    
    return evs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [events, selectedDistrict, panelLayerFilter]);

  // Загрузить детали события
  const loadEventDetails = async (eventId: number) => {
    try {
      setLoadingEvent(true);
      setNewComment("");
      const detail = await getEvent(eventId);
      setSelectedEvent(detail);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingEvent(false);
    }
  };

  // Добавить комментарий
  const handleAddComment = async () => {
    if (!selectedEvent || !newComment.trim()) return;
    
    setSavingComment(true);
    try {
      await addEventComment(selectedEvent.id, newComment.trim());
      // Перезагружаем событие чтобы получить обновлённый список комментариев
      const updated = await getEvent(selectedEvent.id);
      setSelectedEvent(updated);
      setNewComment("");
    } catch (e) {
      console.error(e);
    } finally {
      setSavingComment(false);
    }
  };

  // Удалить комментарий
  const handleDeleteComment = async (commentId: number) => {
    if (!selectedEvent) return;
    
    setDeletingCommentId(commentId);
    try {
      await deleteEventComment(selectedEvent.id, commentId);
      // Перезагружаем событие чтобы получить обновлённый список комментариев
      const updated = await getEvent(selectedEvent.id);
      setSelectedEvent(updated);
    } catch (e) {
      console.error(e);
    } finally {
      setDeletingCommentId(null);
    }
  };

  // Отметить как не актуально / актуально
  const handleToggleArchive = async () => {
    if (!selectedEvent) return;
    
    setSavingArchive(true);
    try {
      const updated = await updateEvent(selectedEvent.id, { is_archived: !selectedEvent.is_archived });
      setSelectedEvent(updated);
      // Обновляем список событий
      const updatedEvents = await getEvents();
      setEvents(updatedEvents);
    } catch (e) {
      console.error(e);
    } finally {
      setSavingArchive(false);
    }
  };

  // Связанные события (по той же теме/слою, независимо от района)
  const relatedEvents = useMemo(() => {
    if (!selectedEvent) return [];
    
    // Ищем события с такой же привязкой к слою (тема)
    const hasLayer = selectedEvent.layer_id || selectedEvent.sub_layer_id || selectedEvent.sub_sub_layer_id;
    
    if (!hasLayer) return []; // Нет слоя — нет связанных
    
    return events
      .filter(ev => {
        if (ev.id === selectedEvent.id) return false;
        
        // Совпадение по самому глубокому уровню слоя
        if (selectedEvent.sub_sub_layer_id && ev.sub_sub_layer_id === selectedEvent.sub_sub_layer_id) {
          return true;
        }
        if (selectedEvent.sub_layer_id && ev.sub_layer_id === selectedEvent.sub_layer_id) {
          return true;
        }
        if (selectedEvent.layer_id && ev.layer_id === selectedEvent.layer_id) {
          return true;
        }
        
        return false;
      })
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 10);
  }, [events, selectedEvent]);

  // Цвета важности
  const getImportanceColor = (value: number) => {
    if (value <= 3) return "text-green-400";
    if (value <= 6) return "text-yellow-400";
    return "text-red-400";
  };

  const getImportanceBg = (value: number) => {
    if (value <= 3) return "bg-green-500/20 border-green-500/40";
    if (value <= 6) return "bg-yellow-500/20 border-yellow-500/40";
    return "bg-red-500/20 border-red-500/40";
  };


  if (loading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-900">
        <div className="animate-spin w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (noRegion) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 p-4">
        <div className="rounded-2xl border border-sky-700/50 bg-sky-950/40 px-6 py-8 max-w-md text-center">
          <p className="text-slate-200 text-lg font-medium mb-2">Регион не выбран</p>
          <p className="text-slate-400 text-sm mb-4">Для отображения обстановки необходимо выбрать регион мониторинга в настройках системы.</p>
          {isAdmin() ? (
            <button
              onClick={() => window.location.href = "/admin"}
              className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/30 text-sm font-medium transition-colors"
            >
              Перейти в настройки
            </button>
          ) : (
            <p className="text-sm text-slate-500">
              Обратитесь к администратору для настройки системы.
            </p>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-900 p-4">
        <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-6 py-4 text-red-100 max-w-md text-center">
          {error}
          {isAdmin() ? (
            <button
              onClick={() => window.location.href = "/admin"}
              className="mt-4 block w-full px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600"
            >
              Перейти в настройки
            </button>
          ) : (
            <p className="mt-4 text-sm text-slate-400">
              Обратитесь к администратору для настройки системы
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 overflow-hidden">
      {/* Карта на весь экран */}
      {mergedGeoJson && (
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: mapScale,
            center: center,
            ...(mapRotate ? { rotate: mapRotate } : {}),
          }}
          style={{ 
            width: "100vw", 
            height: "100vh",
          }}
        >
          <ZoomableGroup
            center={[0, 0]}
            zoom={zoom}
            minZoom={0.5}
            maxZoom={4}
            onMoveEnd={({ zoom: z }) => setCurrentZoom(z)}
          >
              <Geographies geography={mergedGeoJson}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const name = geo.properties?.name || geo.properties?.NAME || "";
                    
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={() => name && handleDistrictClick(name)}
                        style={{
                          default: {
                            fill: getDistrictColor(name),
                            stroke: "#1e293b",
                            strokeWidth: 0.5,
                            outline: "none",
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                          },
                          hover: {
                            fill: getDistrictColor(name),
                            stroke: "#60a5fa",
                            strokeWidth: 1.5,
                            outline: "none",
                            cursor: "pointer",
                            filter: "brightness(1.2)",
                          },
                          pressed: {
                            fill: getDistrictColor(name),
                            stroke: "#3b82f6",
                            strokeWidth: 2,
                            outline: "none",
                          },
                        }}
                      />
                    );
                  })
                }
              </Geographies>
              {visibleCityLabels.map(({ city, fontSize }) => (
                <Marker key={`${city.name}-${city.lat}-${city.lon}`} coordinates={[city.lon, city.lat]}>
                  <circle
                    r={Math.max(1, 2.5 - city.importance * 0.05) / currentZoom}
                    fill="#fafafa"
                    stroke="#334155"
                    strokeWidth={0.3 / currentZoom}
                  />
                  <text
                    textAnchor="middle"
                    y={-(4 / currentZoom)}
                    style={{
                      fontFamily: "system-ui, sans-serif",
                      fontSize: `${fontSize}px`,
                      fill: "#e2e8f0",
                      stroke: "#0f172a",
                      strokeWidth: 3 / currentZoom,
                      paintOrder: "stroke",
                      pointerEvents: "none",
                    }}
                  >
                    {city.name}
                  </text>
                </Marker>
              ))}
            </ZoomableGroup>
          </ComposableMap>
      )}

      {/* Навигационная панель сверху */}
      <div className="absolute top-0 left-0 right-0 z-10 px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* Левая часть: фильтр по слоям */}
          <div className="flex items-center gap-3">
            <select
              value={selectedLayerFilter}
              onChange={(e) => setSelectedLayerFilter(e.target.value)}
              className="w-36 rounded-lg border border-slate-700/70 bg-slate-800/90 backdrop-blur px-3 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
            >
              <option value="all">Все слои</option>
              {layers.map((layer) => (
                <React.Fragment key={layer.id}>
                  <option value={`layer_${layer.id}`}>{layer.name}</option>
                  {(layer.sub_layers || []).map((sub) => (
                    <React.Fragment key={sub.id}>
                      <option value={`sub_${sub.id}`}>&nbsp;&nbsp;↳ {sub.name}</option>
                      {(sub.sub_sub_layers || []).map((subSub) => (
                        <option key={subSub.id} value={`subsub_${subSub.id}`}>
                          &nbsp;&nbsp;&nbsp;&nbsp;↳↳ {subSub.name}
                        </option>
                      ))}
                    </React.Fragment>
                  ))}
                </React.Fragment>
              ))}
            </select>
          </div>
          
          {/* Центр: название управления */}
          {departmentName && (
            <h1 className="text-xl font-semibold text-white tracking-tight">{departmentName}</h1>
          )}
          
          {/* Правая часть: кнопки */}
          <div className="flex items-center gap-2">
            {/* Кнопка возврата - для админов в /admin, для редакторов в /editor/events */}
            {canEdit() && (
              <button
                type="button"
                onClick={() => { window.location.href = isAdmin() ? "/admin" : "/editor/events"; }}
                title={isAdmin() ? "Панель управления" : "Редактор событий"}
                className="shrink-0 p-2 rounded-lg bg-sky-600 text-white hover:bg-sky-500 transition-colors shadow-md"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
              </button>
            )}
            <button
              type="button"
              onClick={logout}
              className="shrink-0 px-3 py-1.5 rounded-lg text-sm bg-slate-800/90 text-slate-300 hover:text-red-300 hover:bg-red-500/20 border border-slate-600/50 hover:border-red-500/50 transition-colors"
            >
              Выход
            </button>
          </div>
        </div>
      </div>

      {/* Левый нижний угол: легенда и имя пользователя */}
      <div className="absolute bottom-4 left-4 flex items-end gap-3 z-10">
        {/* Легенда */}
        <div className="rounded-lg bg-slate-800/90 backdrop-blur border border-slate-700/50 p-3">
          <div className="text-xs text-slate-400 mb-2">Важность событий</div>
          <div className="w-24 h-3 rounded-full overflow-hidden" style={{ background: "linear-gradient(to right, #22c55e 0%, #eab308 50%, #ef4444 100%)" }}></div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1 w-24">
            <span>Низкий</span>
            <span>Высокий</span>
          </div>
        </div>
        {/* Имя пользователя */}
        {currentUserName && (
          <div className="rounded-lg bg-slate-800/90 backdrop-blur border border-slate-700/50 px-3 py-2">
            <div className="text-xs text-slate-400">Пользователь</div>
            <div className="text-sm text-white font-medium">{currentUserName}</div>
          </div>
        )}
      </div>

      {/* Боковая панель справа */}
      <div
        className={`absolute top-0 right-0 bottom-0 w-96 bg-slate-900/95 backdrop-blur border-l border-slate-700/50 transform transition-transform duration-300 z-30 ${
          panelOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {panelOpen && selectedDistrict && (
          <div className="h-full flex flex-col">
            {/* Заголовок панели */}
            <div className="p-4 border-b border-slate-700/50 shrink-0">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">{selectedDistrict}</h2>
                  <p className="text-sm text-slate-400 mt-1">
                    {getResponsibleZone(selectedDistrict)?.department_name || "Подразделение не назначено"}
                  </p>
                </div>
                <button
                  onClick={closePanel}
                  className="text-slate-400 hover:text-white text-2xl leading-none"
                >
                  ×
                </button>
              </div>
              
              {/* Статистика района */}
              {districtStats[selectedDistrict] && (
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-slate-800/50 p-2">
                    <div className="text-lg font-semibold text-sky-400">
                      {districtStats[selectedDistrict].eventCount}
                    </div>
                    <div className="text-[10px] text-slate-500">Событий</div>
                  </div>
                  <div className="rounded-lg bg-slate-800/50 p-2">
                    <div className={`text-lg font-semibold ${getImportanceColor(districtStats[selectedDistrict].maxImportance)}`}>
                      {districtStats[selectedDistrict].maxImportance}
                    </div>
                    <div className="text-[10px] text-slate-500">Макс.</div>
                  </div>
                  <div className="rounded-lg bg-slate-800/50 p-2">
                    <div className={`text-lg font-semibold ${getImportanceColor(Math.round(districtStats[selectedDistrict].integralScore))}`}>
                      {districtStats[selectedDistrict].integralScore.toFixed(1)}
                    </div>
                    <div className="text-[10px] text-slate-500">Интегр.</div>
                  </div>
                </div>
              )}
              
              {/* Фильтр по слоям */}
              <div className="mt-3">
                <select
                  value={panelLayerFilter}
                  onChange={(e) => setPanelLayerFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  <option value="all">Все слои</option>
                  {layers.map((layer) => (
                    <React.Fragment key={layer.id}>
                      <option value={`layer_${layer.id}`}>{layer.name}</option>
                      {(layer.sub_layers || []).map((sub) => (
                        <React.Fragment key={sub.id}>
                          <option value={`sub_${sub.id}`}>&nbsp;&nbsp;↳ {sub.name}</option>
                          {(sub.sub_sub_layers || []).map((subSub) => (
                            <option key={subSub.id} value={`subsub_${subSub.id}`}>
                              &nbsp;&nbsp;&nbsp;&nbsp;↳↳ {subSub.name}
                            </option>
                          ))}
                        </React.Fragment>
                      ))}
                    </React.Fragment>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Контент панели - список событий */}
            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="text-sm text-slate-400 mb-3">
                События ({districtEvents.length})
              </h3>
              
              {districtEvents.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  Нет событий в этом районе
                </div>
              ) : (
                <div className="space-y-2">
                  {districtEvents.map(ev => (
                    <button
                      key={ev.id}
                      onClick={() => loadEventDetails(ev.id)}
                      disabled={loadingEvent}
                      className={`w-full text-left rounded-xl border p-3 transition-colors disabled:opacity-50 ${
                        ev.is_archived 
                          ? "bg-slate-800/30 border-slate-700/30 opacity-60" 
                          : "bg-slate-800/50 border-slate-700/50 hover:bg-slate-800/70"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium border ${ev.is_archived ? "bg-slate-700 text-slate-400 border-slate-600" : getImportanceBg(ev.importance)}`}>
                          {ev.importance}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className={`text-sm font-medium truncate ${ev.is_archived ? "text-slate-400" : "text-white"}`}>{ev.title}</h4>
                            {ev.is_archived && (
                              <span className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-700 text-slate-400 border border-slate-600">
                                не актуально
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                            <span>
                              {new Date(ev.created_at).toLocaleDateString("ru-RU")}{" "}
                              {new Date(ev.created_at).toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {ev.images_count > 0 && <span>📷 {ev.images_count}</span>}
                            {ev.documents_count > 0 && <span>📄 {ev.documents_count}</span>}
                          </div>
                          {ev.created_by_name && (
                            <div className="text-[10px] text-emerald-400 mt-0.5">
                              {ev.created_by_name}
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Индикатор загрузки события */}
      <Modal open={loadingEvent} onClose={() => {}} className="bg-transparent border-0 shadow-none p-0">
        <div className="animate-spin w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full"></div>
      </Modal>

      {/* Модальное окно с деталями события */}
      <Modal
        open={selectedEvent !== null && !loadingEvent}
        onClose={() => setSelectedEvent(null)}
        closeOnEnter={false}
        className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
      >
        {selectedEvent && (
          <>
            {/* Заголовок */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded text-sm font-medium border ${getImportanceBg(selectedEvent.importance)}`}>
                  Важность: {selectedEvent.importance}
                </span>
                <h3 className="text-xl font-semibold text-white">{selectedEvent.title}</h3>
                {selectedEvent.is_archived && (
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-700 text-slate-400 border border-slate-600">
                    Не актуально
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-200 text-2xl leading-none shrink-0"
              >
                ×
              </button>
            </div>
            
            {/* Информация */}
            <div className="grid grid-cols-2 gap-4 text-sm mb-4">
              <div>
                <span className="text-slate-500">Район:</span>
                <p className="text-slate-200">{selectedEvent.district_name || "—"}</p>
              </div>
              <div>
                <span className="text-slate-500">Подразделение:</span>
                <p className="text-slate-200">{selectedEvent.department_name || "Не назначено"}</p>
              </div>
              <div>
                <span className="text-slate-500">Дата создания:</span>
                <p className="text-slate-200">{new Date(selectedEvent.created_at).toLocaleString("ru-RU")}</p>
              </div>
              <div>
                <span className="text-slate-500">Статус:</span>
                <p className="text-slate-200">{STATUS_LABELS[selectedEvent.status] || selectedEvent.status}</p>
              </div>
              {selectedEvent.created_by_name && (
                <div>
                  <span className="text-slate-500">Создал:</span>
                  <p className="text-slate-200">{selectedEvent.created_by_name}</p>
                </div>
              )}
              <div>
                <span className="text-slate-500">Слой:</span>
                <p className="text-slate-200">{getLayerName(selectedEvent.layer_id, selectedEvent.sub_layer_id, selectedEvent.sub_sub_layer_id)}</p>
              </div>
            </div>
            
            {/* Описание */}
            {selectedEvent.description && (
              <div className="mb-4">
                <span className="text-slate-500 text-sm">Описание:</span>
                <p className="text-slate-200 mt-1 whitespace-pre-wrap bg-slate-800/50 rounded-lg p-3 text-sm">
                  {selectedEvent.description}
                </p>
              </div>
            )}
            
            {/* Изображения */}
            {selectedEvent.images && selectedEvent.images.length > 0 && (
              <div className="mb-4">
                <span className="text-slate-500 text-sm">Изображения ({selectedEvent.images.length}):</span>
                <div className="mt-2 grid grid-cols-4 gap-2">
                  {selectedEvent.images.map(img => (
                    <a
                      key={img.id}
                      href={`http://localhost:8000${img.file_path}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block aspect-square rounded-lg overflow-hidden border border-slate-700 hover:border-sky-500 transition-colors"
                    >
                      <img
                        src={`http://localhost:8000${img.file_path}`}
                        alt={img.name}
                        className="w-full h-full object-cover"
                      />
                    </a>
                  ))}
                </div>
              </div>
            )}
            
            {/* Документы */}
            {selectedEvent.documents && selectedEvent.documents.length > 0 && (
              <div className="mb-4">
                <span className="text-slate-500 text-sm">Документы ({selectedEvent.documents.length}):</span>
                <div className="mt-2 space-y-1">
                  {selectedEvent.documents.map(doc => (
                    <a
                      key={doc.id}
                      href={`http://localhost:8000${doc.file_path}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 transition-colors text-sm text-sky-300 hover:text-sky-200"
                    >
                      📄 {doc.name}
                    </a>
                  ))}
                </div>
              </div>
            )}
            
            {/* Комментарии */}
            <div className="mb-4">
              <span className="text-slate-500 text-sm">Комментарии ({selectedEvent.comments?.length || 0}):</span>
              
              {/* Список комментариев */}
              {selectedEvent.comments && selectedEvent.comments.length > 0 && (
                <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                  {selectedEvent.comments.map(comment => (
                    <div key={comment.id} className="bg-slate-800/50 rounded-lg p-2 text-sm">
                      <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
                        <span className="text-emerald-400">{comment.user_name || "Аноним"}</span>
                        <span>•</span>
                        <span>{new Date(comment.created_at).toLocaleString("ru-RU")}</span>
                        <button
                          onClick={() => handleDeleteComment(comment.id)}
                          disabled={deletingCommentId === comment.id}
                          className="ml-auto text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                          title="Удалить комментарий"
                        >
                          {deletingCommentId === comment.id ? "..." : "✕"}
                        </button>
                      </div>
                      <p className="text-slate-300 whitespace-pre-wrap">{comment.text}</p>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Форма добавления комментария */}
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Напишите комментарий..."
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                  onKeyDown={(e) => e.key === 'Enter' && !savingComment && handleAddComment()}
                />
                <button
                  onClick={handleAddComment}
                  disabled={savingComment || !newComment.trim()}
                  className="px-3 py-2 rounded-lg text-sm bg-sky-500 text-white hover:bg-sky-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {savingComment ? "..." : "Отправить"}
                </button>
              </div>
            </div>
            
            {/* Связанные события (по той же теме) */}
            {relatedEvents.length > 0 && (
              <div className="mb-4">
                <span className="text-slate-500 text-sm">События по этой же теме ({relatedEvents.length}):</span>
                <div className="mt-2 space-y-2">
                  {relatedEvents.map(ev => (
                    <button
                      key={ev.id}
                      onClick={() => loadEventDetails(ev.id)}
                      className="w-full text-left rounded-lg bg-slate-800/30 border border-slate-700/30 p-2 hover:bg-slate-800/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${getImportanceBg(ev.importance)}`}>
                          {ev.importance}
                        </span>
                        <span className="text-sm text-slate-300">{ev.title}</span>
                        <span className="text-[10px] text-slate-500 ml-auto">
                          {new Date(ev.created_at).toLocaleDateString("ru-RU")}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Кнопки действий */}
            <div className="mt-6 flex justify-between items-center border-t border-slate-700 pt-4">
              <button
                onClick={handleToggleArchive}
                disabled={savingArchive}
                className={`px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50 ${
                  selectedEvent.is_archived 
                    ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/50" 
                    : "bg-slate-700/50 text-slate-300 hover:bg-slate-700 border border-slate-600"
                }`}
              >
                {savingArchive ? "..." : selectedEvent.is_archived ? "Отметить как актуальное" : "Отметить как не актуально"}
              </button>
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-lg text-sm bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
              >
                Закрыть
              </button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
