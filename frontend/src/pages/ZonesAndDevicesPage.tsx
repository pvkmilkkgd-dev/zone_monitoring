import { useEffect, useState, useRef } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import {
  getAdministrativeZones,
  createAdministrativeZone,
  deleteAdministrativeZone,
  type AdministrativeZone,
} from "../api/administrative-zones";
import { requireAuth, handleAuthError, logout } from "../utils/auth";
import { fetchSystemSettings } from "../api/admin";

type Region = {
  id: string;
  name: string;
};

// Настройки отображения карты для Свердловской области
// Реальный Bbox (из загруженных районов): lon 58.40-65.29, lat 56.19-60.17
// Размер области: 6.89° x 3.98°
// Центр должен быть в формате [lon, lat] для geoMercator
const DEFAULT_MAP_SETTINGS = {
  center: [61.85, 58.18] as [number, number], // [longitude, latitude]
  scale: 3000, // Масштаб для отображения всех районов
};

export function ZonesAndDevicesPage() {
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Информация о выбранном регионе из настроек
  const [geoUrl, setGeoUrl] = useState<string | null>(null);
  const [regionName, setRegionName] = useState<string>("");
  const [regionId, setRegionId] = useState<string | null>(null);
  
  // Состояние для настроек карты (вычисляются автоматически)
  const [mapConfig, setMapConfig] = useState<{ center: [number, number]; scale: number } | null>(null);
  
  // Состояние для отображения названия района при наведении
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  
  // Состояние для проблемных районов
  const [invalidDistricts, setInvalidDistricts] = useState<Array<{name: string; reason: string}>>([]);
  
  // Форма добавления зоны
  const [departmentName, setDepartmentName] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Состояние для размеров контейнера карты (responsive)
  const [mapSize, setMapSize] = useState({ width: 800, height: 600 });
  const mapContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!requireAuth()) return;
    loadInitialData();
  }, []);

  // Отслеживаем изменение размеров контейнера карты
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;

    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setMapSize({ width, height });
      }
    });

    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Функция для вычисления bounds из GeoJSON и установки правильного масштаба
  const calculateMapBounds = async (url: string) => {
    try {
      const response = await fetch(url);
      const geojson = await response.json();
      
      if (!geojson.features || geojson.features.length === 0) {
        return;
      }

      let minLon = Infinity, minLat = Infinity;
      let maxLon = -Infinity, maxLat = -Infinity;

      // Проходим по всем features и находим min/max координаты
      geojson.features.forEach((feature: any) => {
        const geometry = feature.geometry;
        const coords = geometry.coordinates;
        
        const processCoords = (coords: any[]): void => {
          if (typeof coords[0] === 'number') {
            // Это массив [lon, lat]
            const [lon, lat] = coords;
            minLon = Math.min(minLon, lon);
            maxLon = Math.max(maxLon, lon);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
          } else {
            // Это вложенный массив
            coords.forEach((item: any) => processCoords(item));
          }
        };
        
        // Обрабатываем в зависимости от типа геометрии
        if (geometry.type === 'MultiPolygon') {
          // MultiPolygon: [[[lon, lat], ...], ...]
          coords.forEach((polygon: any[]) => {
            polygon.forEach((ring: any[]) => {
              ring.forEach((coord: any[]) => processCoords(coord));
            });
          });
        } else if (geometry.type === 'Polygon') {
          // Polygon: [[lon, lat], ...]
          coords.forEach((ring: any[]) => {
            ring.forEach((coord: any[]) => processCoords(coord));
          });
        } else {
          // Другие типы
          processCoords(coords);
        }
      });

      // Проверяем, что bounds валидны
      if (minLon === Infinity || minLat === Infinity) {
        console.error('Invalid bounds calculated');
        return;
      }

      // Вычисляем центр
      const centerLon = (minLon + maxLon) / 2;
      const centerLat = (minLat + maxLat) / 2;
      
      // Вычисляем размеры области
      const width = maxLon - minLon;
      const height = maxLat - minLat;
      
      // Вычисляем scale на основе размера области и размера карты
      // Для карты 800x600 и области шириной width градусов
      const mapWidth = 800;
      const mapHeight = 600;
      const maxDimension = Math.max(width, height);
      
      // Формула для правильного масштаба в проекции Mercator:
      // Используем формулу, которая учитывает широту центра для правильного масштабирования
      // Базовый масштаб для широты ~58 градусов (Свердловская область)
      const latRad = (centerLat * Math.PI) / 180;
      const latScale = Math.cos(latRad);
      
      // Вычисляем масштаб с учетом широты и размера области
      // Увеличиваем коэффициент для лучшего заполнения карты (с padding ~10%)
      const paddingFactor = 1.1; // Добавляем 10% padding вокруг области
      const baseScale = (mapWidth / maxDimension) * paddingFactor;
      const scale = Math.round(baseScale / latScale);
      
      // Увеличиваем масштаб в 10 раз для более детального отображения
      const scaledUp = scale * 10;
      
      // Ограничиваем масштаб разумными пределами (от 5000 до 100000)
      const clampedScale = Math.max(5000, Math.min(100000, scaledUp));
      
      console.log('Scale calculation:', {
        mapWidth,
        maxDimension,
        centerLat,
        latScale: latScale.toFixed(4),
        baseScale: baseScale.toFixed(2),
        calculatedScale: scale,
        scaledUp,
        clampedScale,
        formula: `(800 / ${maxDimension.toFixed(2)}) * ${paddingFactor} / ${latScale.toFixed(4)} * 10 = ${scaledUp}`
      });
      
      console.log('Calculated bounds:', { minLon, minLat, maxLon, maxLat });
      console.log('Area size:', { width, height });
      console.log('Calculated center:', [centerLon, centerLat]);
      console.log('Calculated scale:', scale);
      
      setMapConfig({
        center: [centerLon, centerLat],
        scale: clampedScale,
      });
    } catch (error) {
      console.error('Error calculating bounds:', error);
    }
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Загружаем системные настройки для получения выбранного региона
      const settings = await fetchSystemSettings();
      
      if (settings && settings.region_ids && settings.region_ids.length > 0) {
        // Берем первый выбранный регион
        const primaryRegionId = settings.region_ids[0];
        setRegionId(primaryRegionId);
        
        // Загружаем информацию о регионах
        const regionsResp = await fetch("/api/regions");
        if (regionsResp.ok) {
          const regions = (await regionsResp.json()) as Region[];
          const region = regions.find((r) => r.id === primaryRegionId);
          if (region) {
            setRegionName(region.name);
            
            // Формируем URL для GeoJSON с районами региона
            const url = `/maps/ru/region/${primaryRegionId}/districts.geojson`;
            console.log('Loading GeoJSON from:', url);
            setGeoUrl(url);
            // Вычисляем bounds и настройки карты
            await calculateMapBounds(url);
          } else {
            setError(`Информация о регионе с ID ${primaryRegionId} не найдена`);
          }
        } else {
          setError("Не удалось загрузить список регионов");
        }
      } else {
        setError("Регион не выбран в настройках системы");
      }

      // Получаем зоны для карты с id=1 (можно изменить)
      const data = await getAdministrativeZones(1);
      setZones(data);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  };

  const loadZones = async () => {
    try {
      setError(null);
      const data = await getAdministrativeZones(1);
      setZones(data);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки административных зон");
    }
  };

  const handleAddZone = async () => {
    setFormError(null);

    if (!departmentName.trim()) {
      setFormError("Введите название отдела");
      return;
    }

    try {
      setSaving(true);
      await createAdministrativeZone({
        map_id: 1, // Можно изменить на динамический выбор карты
        department_name: departmentName,
        district_names: [], // Пустой массив, так как районы не используются
      });

      // Очистка формы
      setDepartmentName("");
      
      // Перезагрузка списка
      await loadZones();
      setFormError(null);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setFormError(e.message || "Ошибка при добавлении зоны");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteZone = async (zoneId: number) => {
    if (!confirm("Вы уверены, что хотите удалить эту запись?")) {
      return;
    }

    try {
      await deleteAdministrativeZone(zoneId);
      await loadZones();
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      alert(e.message || "Ошибка при удалении зоны");
    }
  };


  return (
    <div style={{ minHeight: "100vh", background: "#1e293b", color: "#fff", padding: "2rem" }}>
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h1 style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>
            Зоны и устройства
          </h1>
          <button
            type="button"
            onClick={logout}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem",
              fontSize: "0.875rem",
              color: "#cbd5e1",
              background: "transparent",
              border: "1px solid rgba(71, 85, 105, 0.5)",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#fca5a5";
              e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
              e.currentTarget.style.borderColor = "rgba(239, 68, 68, 0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#cbd5e1";
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.borderColor = "rgba(71, 85, 105, 0.5)";
            }}
          >
            Выход
          </button>
        </div>

        {/* Навигация */}
        <div
          style={{
            display: "flex",
            gap: "0.5rem",
            borderRadius: "9999px",
            background: "#1e293b",
            padding: "0.25rem",
            fontSize: "0.875rem",
            width: "fit-content",
            marginBottom: "2rem",
          }}
        >
          <button
            type="button"
            onClick={() => {
              window.location.href = "/admin";
            }}
            style={{
              padding: "0.375rem 1rem",
              borderRadius: "9999px",
              color: "#cbd5e1",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#f1f5f9";
              e.currentTarget.style.background = "rgba(51, 65, 85, 0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#cbd5e1";
              e.currentTarget.style.background = "transparent";
            }}
          >
            Регион и управление
          </button>
          <button
            type="button"
            onClick={() => {
              window.location.href = "/admin/users";
            }}
            style={{
              padding: "0.375rem 1rem",
              borderRadius: "9999px",
              color: "#cbd5e1",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#f1f5f9";
              e.currentTarget.style.background = "rgba(51, 65, 85, 0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#cbd5e1";
              e.currentTarget.style.background = "transparent";
            }}
          >
            Пользователи
          </button>
          <button
            type="button"
            style={{
              padding: "0.375rem 1rem",
              borderRadius: "9999px",
              background: "#0ea5e9",
              color: "#0f172a",
              fontWeight: "500",
              border: "none",
              cursor: "default",
              boxShadow: "0 1px 2px 0 rgba(14, 165, 233, 0.4)",
            }}
          >
            Зоны и устройства
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "#ef4444",
              padding: "1rem",
              borderRadius: "0.5rem",
              marginBottom: "1rem",
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
          {/* Карта */}
          <div
            style={{
              background: "#334155",
              borderRadius: "0.5rem",
              padding: "1.5rem",
            }}
          >
            {geoUrl ? (
              <div style={{ background: "#1e293b", borderRadius: "0.5rem", padding: "1rem", position: "relative" }}>
                <div style={{ marginBottom: "0.5rem", fontSize: "0.875rem", color: "#cbd5e1" }}>
                  Регион: <strong>{regionName || "Загрузка..."}</strong>
                </div>
                <div 
                  ref={mapContainerRef}
                  style={{ width: "100%", height: "600px", overflow: "hidden", borderRadius: "0.5rem" }}
                >
                  <ComposableMap
                    projection="geoMercator"
                    projectionConfig={mapConfig || {
                      scale: 3000,
                      center: [61.85, 58.18], // [longitude, latitude] - центр Свердловской области
                    }}
                    width={mapSize.width}
                    height={mapSize.height}
                    style={{ width: "100%", height: "100%" }}
                  >
                  <Geographies 
                    geography={geoUrl}
                  >
                    {({ geographies }) => {
                      console.log(`Rendering ${geographies.length} districts`);
                      
                      // Логируем структуру первого района для отладки
                      if (geographies.length > 0) {
                        const firstGeo = geographies[0];
                        const props = firstGeo.properties as any;
                        const districtName = props?.name || props?.NAME || 'Unknown';
                        console.log(`First district sample: ${districtName}`, {
                          type: firstGeo.geometry?.type,
                          coordsLength: firstGeo.geometry?.coordinates?.length,
                          firstCoordSample: firstGeo.geometry?.coordinates?.[0]?.[0]?.[0]?.slice(0, 2)
                        });
                      }
                      
                      const validGeographies = geographies.filter((geo) => {
                        if (!geo.geometry || !geo.geometry.coordinates) {
                          const props = geo.properties as any;
                          const districtName = props?.name || props?.NAME || 'Unknown';
                          console.warn(`District ${districtName} has no geometry`);
                          return false;
                        }
                        
                        // Проверяем, что координаты не пустые
                        const coords = geo.geometry.coordinates;
                        const geomType = geo.geometry.type;
                        
                        if (geomType === 'MultiPolygon') {
                          if (!Array.isArray(coords) || coords.length === 0) {
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            console.warn(`❌ District "${districtName}": empty MultiPolygon coordinates`);
                            return false;
                          }
                          
                          // Проверяем валидность структуры MultiPolygon: [[[lon, lat], ...], ...]
                          // Структура: MultiPolygon -> [Polygon -> [Ring -> [lon, lat]]]
                          try {
                            let hasValidCoords = false;
                            let minLon = Infinity, minLat = Infinity;
                            let maxLon = -Infinity, maxLat = -Infinity;
                            let coordCount = 0;
                            let invalidCoordCount = 0;
                            
                            const extractBounds = (arr: any, depth: number = 0): void => {
                              if (!Array.isArray(arr)) {
                                invalidCoordCount++;
                                return;
                              }
                              
                              // Проверяем, является ли это координатой [lon, lat]
                              if (arr.length >= 2 && typeof arr[0] === 'number' && typeof arr[1] === 'number') {
                                coordCount++;
                                const [lon, lat] = arr;
                                if (isFinite(lon) && isFinite(lat) && lon >= -180 && lon <= 180 && lat >= -90 && lat <= 90) {
                                  hasValidCoords = true;
                                  minLon = Math.min(minLon, lon);
                                  maxLon = Math.max(maxLon, lon);
                                  minLat = Math.min(minLat, lat);
                                  maxLat = Math.max(maxLat, lat);
                                } else {
                                  invalidCoordCount++;
                                }
                              } else {
                                // Рекурсивно обрабатываем вложенные массивы
                                arr.forEach((item: any) => extractBounds(item, depth + 1));
                              }
                            };
                            
                            extractBounds(coords);
                            
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            
                            if (!hasValidCoords) {
                              console.warn(`❌ District "${districtName}": no valid coordinates found (checked ${coordCount} coords, ${invalidCoordCount} invalid)`);
                              // Пытаемся найти проблему в структуре
                              if (coords.length > 0) {
                                const firstPoly = coords[0];
                                if (Array.isArray(firstPoly) && firstPoly.length > 0) {
                                  const firstRing = firstPoly[0];
                                  if (Array.isArray(firstRing)) {
                                    console.warn(`  Structure: MultiPolygon[${coords.length} polygons] -> Polygon[${firstPoly.length} rings] -> Ring[${firstRing.length} coords]`);
                                    if (firstRing.length > 0 && Array.isArray(firstRing[0])) {
                                      const sample = firstRing[0];
                                      console.warn(`  Sample coord: [${sample[0]}, ${sample[1]}] (types: ${typeof sample[0]}, ${typeof sample[1]})`);
                                    }
                                  }
                                }
                              }
                              return false;
                            }
                            
                            const width = maxLon - minLon;
                            const height = maxLat - minLat;
                            
                            // Проверяем, что bounds валидны (не все координаты одинаковые)
                            if (!isFinite(width) || !isFinite(height) || width <= 0 || height <= 0) {
                              console.warn(`❌ District "${districtName}": invalid bounds (width: ${width}, height: ${height})`);
                              return false;
                            }
                            
                            // Если район слишком маленький (меньше 0.0001 градуса - это примерно 11 метров), пропускаем
                            // Это очень маленький порог, чтобы не пропустить реальные маленькие районы
                            if (width < 0.0001 || height < 0.0001) {
                              console.warn(`⚠️ District "${districtName}": too small (${width.toFixed(8)}° x ${height.toFixed(8)}°)`);
                              return false;
                            }
                            
                            // Логируем успешную валидацию для отладки
                            if (invalidCoordCount > 0) {
                              console.log(`✓ District "${districtName}": valid (${coordCount} coords, ${invalidCoordCount} invalid filtered)`);
                            }
                          } catch (e) {
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            console.error(`❌ District "${districtName}": validation error:`, e);
                            return false;
                          }
                        } else if (geomType === 'Polygon') {
                          if (!Array.isArray(coords) || coords.length === 0) {
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            console.warn(`❌ District "${districtName}": empty Polygon coordinates`);
                            return false;
                          }
                          
                          // Проверяем валидность структуры Polygon: [[lon, lat], ...]
                          // Структура: Polygon -> [Ring -> [lon, lat]]
                          try {
                            let hasValidCoords = false;
                            let coordCount = 0;
                            
                            const extractBounds = (arr: any): void => {
                              if (!Array.isArray(arr)) return;
                              
                              // Проверяем, является ли это координатой [lon, lat]
                              if (arr.length >= 2 && typeof arr[0] === 'number' && typeof arr[1] === 'number') {
                                coordCount++;
                                const [lon, lat] = arr;
                                if (isFinite(lon) && isFinite(lat) && lon >= -180 && lon <= 180 && lat >= -90 && lat <= 90) {
                                  hasValidCoords = true;
                                }
                              } else {
                                // Рекурсивно обрабатываем вложенные массивы
                                arr.forEach((item: any) => extractBounds(item));
                              }
                            };
                            
                            extractBounds(coords);
                            
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            
                            if (!hasValidCoords) {
                              console.warn(`❌ District "${districtName}": no valid coordinates in Polygon (checked ${coordCount} coords)`);
                              return false;
                            }
                          } catch (e) {
                            const props = geo.properties as any;
                            const districtName = props?.name || props?.NAME || 'Unknown';
                            console.error(`❌ District "${districtName}": Polygon validation error:`, e);
                            return false;
                          }
                        } else {
                          // Неподдерживаемый тип геометрии
                          const props = geo.properties as any;
                          const districtName = props?.name || props?.NAME || 'Unknown';
                          console.warn(`❌ District "${districtName}": unsupported geometry type "${geomType}"`);
                          return false;
                        }
                        
                        return true;
                      });
                      
                      // Собираем информацию о проблемных районах
                      const invalidDistrictsList: Array<{name: string; reason: string}> = [];
                      
                      geographies.forEach((geo) => {
                        const props = geo.properties as any;
                        const districtName = props?.name || props?.NAME || 'Unknown';
                        
                        if (!geo.geometry || !geo.geometry.coordinates) {
                          invalidDistrictsList.push({ name: districtName, reason: 'Нет геометрии' });
                          return;
                        }
                        
                        if (!validGeographies.includes(geo)) {
                          const geomType = geo.geometry.type;
                          if (geomType === 'MultiPolygon' || geomType === 'Polygon') {
                            invalidDistrictsList.push({ name: districtName, reason: 'Некорректные координаты' });
                          } else {
                            invalidDistrictsList.push({ name: districtName, reason: `Неподдерживаемый тип: ${geomType}` });
                          }
                        }
                      });
                      
                      // Обновляем состояние проблемных районов
                      if (invalidDistrictsList.length > 0) {
                        setInvalidDistricts(invalidDistrictsList);
                      } else {
                        setInvalidDistricts([]);
                      }
                      
                      const invalidCount = geographies.length - validGeographies.length;
                      console.log(`Valid geographies: ${validGeographies.length} out of ${geographies.length}`);
                      if (invalidCount > 0) {
                        console.warn(`⚠️ ${invalidCount} districts have invalid geometry and were skipped`);
                      }
                      
                      // Вычисляем bounds для каждого района и проверяем, находятся ли они в видимой области
                      if (mapConfig) {
                        const visibleBounds = {
                          minLon: mapConfig.center[0] - 3.5,
                          maxLon: mapConfig.center[0] + 3.5,
                          minLat: mapConfig.center[1] - 2,
                          maxLat: mapConfig.center[1] + 2,
                        };
                        
                        const districtsInBounds = validGeographies.filter((geo) => {
                          const coords = geo.geometry.coordinates;
                          let minLon = Infinity, minLat = Infinity;
                          let maxLon = -Infinity, maxLat = -Infinity;
                          
                          const extractBounds = (arr: any) => {
                            if (Array.isArray(arr[0])) {
                              arr.forEach(extractBounds);
                            } else if (arr.length >= 2 && typeof arr[0] === 'number') {
                              const [lon, lat] = arr;
                              minLon = Math.min(minLon, lon);
                              maxLon = Math.max(maxLon, lon);
                              minLat = Math.min(minLat, lat);
                              maxLat = Math.max(maxLat, lat);
                            }
                          };
                          
                          extractBounds(coords);
                          
                          // Проверяем пересечение bounds
                          const intersects = !(maxLon < visibleBounds.minLon || 
                                              minLon > visibleBounds.maxLon ||
                                              maxLat < visibleBounds.minLat || 
                                              minLat > visibleBounds.maxLat);
                          
                          return intersects;
                        });
                        
                        console.log(`Districts in visible bounds: ${districtsInBounds.length} out of ${validGeographies.length}`);
                        
                        if (districtsInBounds.length < validGeographies.length) {
                          console.warn(`Some districts are outside visible bounds!`);
                        }
                      }
                      
                      // Логируем первые 5 районов для отладки
                      validGeographies.slice(0, 5).forEach((geo, idx) => {
                        const props = geo.properties as any;
                        const name = props?.name || props?.NAME || `Район ${idx + 1}`;
                        const geom = geo.geometry;
                        if (geom?.coordinates) {
                          console.log(`District ${idx + 1}: ${name}, type: ${geom.type}`);
                        }
                      });
                      
                      return validGeographies.map((geo, index) => {
                        const props = geo.properties as any;
                        const districtName = props?.name || props?.NAME || `Район ${index + 1}`;
                        
                        // Генерируем уникальный цвет для каждого района
                        // Используем золотое сечение для разнообразия цветов
                        const hue = (index * 137.5) % 360;
                        const fillColor = `hsl(${hue}, 60%, 50%)`;
                        
                        // Проверяем, что геометрия валидна перед рендерингом
                        try {
                          if (!geo.geometry || !geo.geometry.coordinates) {
                            console.warn(`Skipping district ${districtName}: invalid geometry`);
                            return null;
                          }
                          
                          return (
                            <Geography
                              key={geo.rsmKey || `district-${index}`}
                              geography={geo}
                              onMouseEnter={() => setHoveredDistrict(districtName)}
                              onMouseLeave={() => setHoveredDistrict(null)}
                              stroke="#ffffff"
                              strokeWidth={0.5}
                              style={{
                                default: {
                                  fill: fillColor,
                                  fillOpacity: 0.7,
                                  outline: "none",
                                },
                                hover: {
                                  fill: fillColor,
                                  fillOpacity: 0.9,
                                  outline: "none",
                                  cursor: "pointer",
                                },
                                pressed: {
                                  fill: fillColor,
                                  fillOpacity: 1,
                                  outline: "none",
                                },
                              }}
                            />
                          );
                        } catch (error) {
                          console.error(`Error rendering district ${districtName}:`, error);
                          return null;
                        }
                      }).filter(Boolean);
                    }}
                  </Geographies>
                </ComposableMap>
                </div>
                
                {hoveredDistrict && (
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      background: "rgba(15, 23, 42, 0.95)",
                      padding: "0.75rem 1.25rem",
                      borderRadius: "0.5rem",
                      fontSize: "0.875rem",
                      fontWeight: "600",
                      color: "#38bdf8",
                      border: "1px solid rgba(56, 189, 248, 0.3)",
                      boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
                      pointerEvents: "none",
                      whiteSpace: "nowrap",
                      zIndex: 10,
                    }}
                  >
                    {hoveredDistrict}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ background: "#1e293b", borderRadius: "0.5rem", padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
                {loading ? "Загрузка карты..." : "Карта не загружена. Проверьте настройки региона."}
              </div>
            )}

            <div style={{ marginTop: "1rem", fontSize: "0.875rem", color: "#94a3b8" }}>
              Отображаются муниципальные районы региона {regionName}
            </div>
            
            {invalidDistricts.length > 0 && (
              <div style={{ 
                marginTop: "1rem", 
                padding: "0.75rem", 
                background: "rgba(239, 68, 68, 0.1)", 
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "0.5rem",
                fontSize: "0.875rem",
                color: "#fca5a5"
              }}>
                <div style={{ fontWeight: "600", marginBottom: "0.5rem" }}>
                  ⚠️ Проблемы с геометрией ({invalidDistricts.length} {invalidDistricts.length === 1 ? 'район' : invalidDistricts.length < 5 ? 'района' : 'районов'}):
                </div>
                <div style={{ maxHeight: "150px", overflowY: "auto", fontSize: "0.8125rem" }}>
                  {invalidDistricts.slice(0, 10).map((district, idx) => (
                    <div key={idx} style={{ marginBottom: "0.25rem" }}>
                      • <strong>{district.name}</strong>: {district.reason}
                    </div>
                  ))}
                  {invalidDistricts.length > 10 && (
                    <div style={{ marginTop: "0.5rem", fontStyle: "italic" }}>
                      ... и еще {invalidDistricts.length - 10} {invalidDistricts.length - 10 === 1 ? 'район' : invalidDistricts.length - 10 < 5 ? 'района' : 'районов'}
                    </div>
                  )}
                </div>
                <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", opacity: 0.8 }}>
                  Эти районы не отображаются на карте. Проверьте геометрию в базе данных.
                </div>
              </div>
            )}
          </div>

          {/* Форма и таблица */}
          <div>
            {/* Форма добавления */}
            <div
              style={{
                background: "#334155",
                borderRadius: "0.5rem",
                padding: "1.5rem",
                marginBottom: "1.5rem",
              }}
            >
              <h2 style={{ fontSize: "1.25rem", fontWeight: "600", marginBottom: "1rem" }}>
                Добавить отдел
              </h2>

              {formError && (
                <div
                  style={{
                    background: "#ef4444",
                    padding: "0.75rem",
                    borderRadius: "0.375rem",
                    marginBottom: "1rem",
                    fontSize: "0.875rem",
                  }}
                >
                  {formError}
                </div>
              )}

              <div style={{ marginBottom: "1rem" }}>
                <label
                  style={{
                    display: "block",
                    marginBottom: "0.5rem",
                    fontSize: "0.875rem",
                    fontWeight: "500",
                  }}
                >
                  Название отдела:
                </label>
                <input
                  type="text"
                  value={departmentName}
                  onChange={(e) => setDepartmentName(e.target.value)}
                  placeholder="Например: Отдел №1"
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: "0.375rem",
                    background: "#1e293b",
                    color: "#fff",
                    border: "1px solid #475569",
                  }}
                />
              </div>


              <button
                onClick={handleAddZone}
                disabled={saving}
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  background: saving ? "#475569" : "#3b82f6",
                  color: "#fff",
                  borderRadius: "0.375rem",
                  fontWeight: "600",
                  cursor: saving ? "not-allowed" : "pointer",
                  border: "none",
                }}
              >
                {saving ? "Добавление..." : "Добавить"}
              </button>
            </div>

            {/* Таблица зон */}
            <div style={{ background: "#334155", borderRadius: "0.5rem", padding: "1.5rem" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: "600", marginBottom: "1rem" }}>
                Список отделов
              </h2>

              {loading ? (
                <div style={{ textAlign: "center", padding: "2rem" }}>Загрузка...</div>
              ) : zones.length === 0 ? (
                <div style={{ textAlign: "center", padding: "2rem", color: "#94a3b8" }}>
                  Нет созданных отделов
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid #475569" }}>
                        <th
                          style={{
                            padding: "0.75rem",
                            textAlign: "left",
                            fontSize: "0.875rem",
                            fontWeight: "600",
                          }}
                        >
                          Название отдела
                        </th>
                        <th
                          style={{
                            padding: "0.75rem",
                            textAlign: "right",
                            fontSize: "0.875rem",
                            fontWeight: "600",
                          }}
                        >
                          Действия
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {zones.map((zone) => (
                        <tr
                          key={zone.id}
                          style={{
                            borderBottom: "1px solid #475569",
                          }}
                        >
                          <td style={{ padding: "0.75rem" }}>{zone.department_name}</td>
                          <td style={{ padding: "0.75rem", textAlign: "right" }}>
                            <button
                              onClick={() => handleDeleteZone(zone.id)}
                              style={{
                                padding: "0.375rem 0.75rem",
                                background: "#ef4444",
                                color: "#fff",
                                borderRadius: "0.375rem",
                                fontSize: "0.875rem",
                                cursor: "pointer",
                                border: "none",
                              }}
                            >
                              Удалить
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
