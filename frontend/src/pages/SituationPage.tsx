import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import { requireAuth, handleAuthError, logout } from "../utils/auth";
import { fetchSystemSettings } from "../api/admin";
import { getAdministrativeZones, type AdministrativeZone } from "../api/administrative-zones";
import { getEvents, getEvent, type EventListItem, type EventDetail } from "../api/events";
import { getLayers, type Layer } from "../api/layers";

type District = {
  name: string;
};

type DistrictStats = {
  totalImportance: number;
  eventCount: number;
  maxImportance: number;
  avgImportance: number;
};

export function SituationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Данные карты
  const [geoUrl, setGeoUrl] = useState<string | null>(null);
  const [regionName, setRegionName] = useState<string>("");
  const [departmentName, setDepartmentName] = useState<string>("");
  const [mapConfig, setMapConfig] = useState<{ center: [number, number]; scale: number } | null>(null);
  
  // Данные
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [layers, setLayers] = useState<Layer[]>([]);
  
  // Фильтр по слоям
  const [selectedLayerFilter, setSelectedLayerFilter] = useState<string>("all");
  
  // Зум карты
  const [zoom] = useState(1);
  const [center] = useState<[number, number]>([60.5, 59.5]);
  const [mapScale] = useState(2200);
  
  // Боковая панель
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  
  // Просмотр события
  const [selectedEvent, setSelectedEvent] = useState<EventDetail | null>(null);
  const [loadingEvent, setLoadingEvent] = useState(false);
  
  // Фильтр слоя в панели
  const [panelLayerFilter, setPanelLayerFilter] = useState<string>("all");

  // Словарь статусов
  const STATUS_LABELS: Record<string, string> = {
    ok: "В норме",
    warning: "Внимание",
    alert: "Тревога",
  };

  useEffect(() => {
    if (!requireAuth()) return;
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Загружаем настройки
      const settings = await fetchSystemSettings();
      if (!settings || !settings.region_ids || settings.region_ids.length === 0) {
        setError("Регион не выбран в настройках системы");
        setLoading(false);
        return;
      }

      // Название управления
      if (settings.department_name) {
        setDepartmentName(settings.department_name);
      }

      const regionId = settings.region_ids[0];
      
      // Загружаем информацию о регионе
      const regionsResp = await fetch("/api/regions");
      if (regionsResp.ok) {
        const regions = await regionsResp.json();
        const region = regions.find((r: any) => r.id === regionId);
        if (region) {
          setRegionName(region.name);
        }
      }
      
      // Загружаем GeoJSON
      const geoUrl = `/maps/ru/region/${regionId}/districts.geojson`;
      setGeoUrl(geoUrl);
      
      // Загружаем конфигурацию карты
      try {
        const configResp = await fetch(`/maps/ru/region/${regionId}/config.json`);
        if (configResp.ok) {
          const config = await configResp.json();
          setMapConfig(config);
          if (config.center) {
            setCenter(config.center);
          }
        }
      } catch (e) {
        console.log("Config not found, using defaults");
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

  // Статистика по районам
  const districtStats = useMemo(() => {
    const stats: Record<string, DistrictStats> = {};
    
    filteredEvents.forEach(ev => {
      if (!ev.district_name) return;
      
      if (!stats[ev.district_name]) {
        stats[ev.district_name] = {
          totalImportance: 0,
          eventCount: 0,
          maxImportance: 0,
          avgImportance: 0,
        };
      }
      
      stats[ev.district_name].totalImportance += ev.importance;
      stats[ev.district_name].eventCount += 1;
      stats[ev.district_name].maxImportance = Math.max(
        stats[ev.district_name].maxImportance,
        ev.importance
      );
    });
    
    // Вычисляем средние значения
    Object.keys(stats).forEach(name => {
      if (stats[name].eventCount > 0) {
        stats[name].avgImportance = stats[name].totalImportance / stats[name].eventCount;
      }
    });
    
    return stats;
  }, [filteredEvents]);

  // Максимальное значение для нормализации
  const maxTotalImportance = useMemo(() => {
    let max = 0;
    Object.values(districtStats).forEach(s => {
      max = Math.max(max, s.totalImportance);
    });
    return max || 1;
  }, [districtStats]);

  // Цвет района по важности
  const getDistrictColor = useCallback((districtName: string) => {
    const stats = districtStats[districtName];
    if (!stats || stats.eventCount === 0) {
      return "#22c55e"; // Зелёный - нет событий (минимальный уровень)
    }
    
    // Нормализуем от 0 до 1 (по сумме важности)
    const normalized = Math.min(stats.totalImportance / maxTotalImportance, 1);
    
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
  }, [districtStats, maxTotalImportance]);

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
      const detail = await getEvent(eventId);
      setSelectedEvent(detail);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingEvent(false);
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

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-900 p-4">
        <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-6 py-4 text-red-100 max-w-md text-center">
          {error}
          <button
            onClick={() => window.location.href = "/admin"}
            className="mt-4 block w-full px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600"
          >
            Перейти в настройки
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 overflow-hidden">
      {/* Карта на весь экран */}
      {geoUrl && (
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: mapScale,
            center: center,
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
          >
              <Geographies geography={geoUrl}>
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
            </ZoomableGroup>
          </ComposableMap>
      )}

      {/* Навигационная панель сверху */}
      <div className="absolute top-0 left-0 right-0 z-10 px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex gap-2 rounded-full bg-slate-800/80 p-1 text-sm">
            <button
              type="button"
              onClick={() => { window.location.href = "/admin"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Регион и управление
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/zones"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Зоны и устройства
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/layers"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Слои
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/events"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              События
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/users"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Пользователи
            </button>
            <button
              type="button"
              className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
            >
              Обстановка
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={logout}
              className="shrink-0 px-3 py-1.5 rounded-lg text-sm text-slate-300 hover:text-red-300 hover:bg-red-500/10 border border-slate-600/50 hover:border-red-500/50 transition-colors"
            >
              Выход
            </button>
          </div>
        </div>
      </div>

      {/* Фильтр по слоям - слева под навигацией */}
      <div className="absolute top-16 left-4 z-10">
        <select
          value={selectedLayerFilter}
          onChange={(e) => setSelectedLayerFilter(e.target.value)}
          className="w-32 rounded-lg border border-slate-700/70 bg-slate-800/90 backdrop-blur px-3 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
        >
          <option value="all">Все слои</option>
          {layers.map((layer) => (
            <optgroup key={layer.id} label={layer.name}>
              <option value={`layer_${layer.id}`}>{layer.name}</option>
              {layer.sub_layers.map((sub) => (
                <>
                  <option key={`sub_${sub.id}`} value={`sub_${sub.id}`}>
                    ↳ {sub.name}
                  </option>
                  {(sub.sub_sub_layers || []).map((subSub) => (
                    <option key={`subsub_${subSub.id}`} value={`subsub_${subSub.id}`}>
                      ↳↳ {subSub.name}
                    </option>
                  ))}
                </>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* Название управления - по центру под навигацией */}
      {departmentName && (
        <div className="absolute top-16 left-1/2 transform -translate-x-1/2 z-10">
          <h1 className="text-xl font-semibold text-white tracking-tight">{departmentName}</h1>
        </div>
      )}

      {/* Легенда - левый нижний угол */}
      <div className="absolute bottom-4 left-4 rounded-lg bg-slate-800/90 backdrop-blur border border-slate-700/50 p-3 z-10">
        <div className="text-xs text-slate-400 mb-2">Важность событий</div>
        <div className="w-24 h-3 rounded-full overflow-hidden" style={{ background: "linear-gradient(to right, #22c55e 0%, #eab308 50%, #ef4444 100%)" }}></div>
        <div className="flex justify-between text-[10px] text-slate-500 mt-1 w-24">
          <span>Низкий</span>
          <span>Высокий</span>
        </div>
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
                    <div className="text-lg font-semibold text-slate-300">
                      {districtStats[selectedDistrict].avgImportance.toFixed(1)}
                    </div>
                    <div className="text-[10px] text-slate-500">Средн.</div>
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
                    <optgroup key={layer.id} label={layer.name}>
                      <option value={`layer_${layer.id}`}>{layer.name}</option>
                      {layer.sub_layers.map((sub) => (
                        <>
                          <option key={`sub_${sub.id}`} value={`sub_${sub.id}`}>
                            &nbsp;&nbsp;↳ {sub.name}
                          </option>
                          {(sub.sub_sub_layers || []).map((subSub) => (
                            <option key={`subsub_${subSub.id}`} value={`subsub_${subSub.id}`}>
                              &nbsp;&nbsp;&nbsp;&nbsp;↳ {subSub.name}
                            </option>
                          ))}
                        </>
                      ))}
                    </optgroup>
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
                      className="w-full text-left rounded-xl bg-slate-800/50 border border-slate-700/50 p-3 hover:bg-slate-800/70 transition-colors disabled:opacity-50"
                    >
                      <div className="flex items-start gap-2">
                        <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium border ${getImportanceBg(ev.importance)}`}>
                          {ev.importance}
                        </span>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-white truncate">{ev.title}</h4>
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
      {loadingEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="animate-spin w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full"></div>
        </div>
      )}

      {/* Модальное окно с деталями события */}
      {selectedEvent && !loadingEvent && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setSelectedEvent(null)}
        >
          <div 
            className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Заголовок */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded text-sm font-medium border ${getImportanceBg(selectedEvent.importance)}`}>
                  Важность: {selectedEvent.importance}
                </span>
                <h3 className="text-xl font-semibold text-white">{selectedEvent.title}</h3>
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
            
            {/* Связанные события (по той же теме) */}
            {relatedEvents.length > 0 && (
              <div>
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
            
            {/* Кнопка закрытия */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-lg text-sm bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
