import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import { useEscapeKey } from "../hooks/useEscapeKey";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import {
  getAdministrativeZones,
  createAdministrativeZone,
  updateAdministrativeZone,
  deleteAdministrativeZone,
  type AdministrativeZone,
} from "../api/administrative-zones";
import {
  getDistrictDescriptions,
  updateDistrictDescription,
  type DistrictDescription,
} from "../api/district-descriptions";
import { requireAdmin, handleAuthError, logout } from "../utils/auth";
import { fetchSystemSettings } from "../api/admin";

type Region = {
  id: string;
  name: string;
};

type District = {
  name: string;
};

export function ZonesAndDevicesPage() {
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Информация о выбранном регионе из настроек
  const [geoUrl, setGeoUrl] = useState<string | null>(null);
  const [regionName, setRegionName] = useState<string>("");
  
  // Список всех районов из GeoJSON
  const [allDistricts, setAllDistricts] = useState<District[]>([]);
  
  // Состояние для настроек карты
  const [mapConfig, setMapConfig] = useState<{ center: [number, number]; scale: number } | null>(null);
  
  // Состояние для отображения названия района при наведении
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  
  // Форма добавления зоны
  const [departmentName, setDepartmentName] = useState("");
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Поиск по районам
  const [districtSearch, setDistrictSearch] = useState("");
  
  // Сортировка таблицы подразделений
  const [sortField, setSortField] = useState<'name' | 'districts'>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  
  // Модальное окно удаления
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; zoneId: number | null; zoneName: string }>({ open: false, zoneId: null, zoneName: '' });
  
  // Модальное окно редактирования
  const [editModal, setEditModal] = useState<{ 
    open: boolean; 
    zone: AdministrativeZone | null;
    name: string;
    description: string;
    selectedDistricts: Set<string>;
  }>({ open: false, zone: null, name: '', description: '', selectedDistricts: new Set() });
  const [editSaving, setEditSaving] = useState(false);
  
  // Модальное окно описания района
  const [districtModal, setDistrictModal] = useState<{
    open: boolean;
    districtName: string;
    description: string;
  }>({ open: false, districtName: '', description: '' });
  const [districtDescriptions, setDistrictDescriptions] = useState<Map<string, string>>(new Map());
  const [districtSaving, setDistrictSaving] = useState(false);
  
  // Уведомление об успешном удалении
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Ошибка валидации имени
  const [nameError, setNameError] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Закрытие модальных окон по Escape
  const closeDeleteModalEsc = useCallback(() => setDeleteModal({ open: false, zoneId: null, zoneName: '' }), []);
  const closeEditModalEsc = useCallback(() => setEditModal({ open: false, zone: null, name: '', description: '', selectedDistricts: new Set() }), []);
  const closeDistrictModalEsc = useCallback(() => setDistrictModal({ open: false, districtName: '', description: '' }), []);
  const closeSuccessMessage = useCallback(() => setSuccessMessage(null), []);

  useEscapeKey(deleteModal.open, closeDeleteModalEsc);
  useEscapeKey(editModal.open, closeEditModalEsc);
  useEscapeKey(districtModal.open, closeDistrictModalEsc);
  useEscapeKey(successMessage !== null, closeSuccessMessage);

  // Состояние для размеров контейнера карты
  const [mapSize, setMapSize] = useState({ width: 800, height: 600 });
  const mapContainerRef = useRef<HTMLDivElement>(null);
  
  // Состояние для зума карты
  const [zoomLevel, setZoomLevel] = useState(1);
  const baseScaleRef = useRef<number | null>(null);
  
  // Состояние для сдвига карты (pan)
  const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef<{ x: number; y: number } | null>(null);

  // Собираем все назначенные районы из существующих зон
  const assignedDistricts = useMemo(() => {
    const assigned = new Set<string>();
    zones.forEach(zone => {
      zone.district_names.forEach(name => assigned.add(name));
    });
    return assigned;
  }, [zones]);

  // Фильтрация районов по поиску
  const filteredDistricts = useMemo(() => {
    if (!districtSearch.trim()) return allDistricts;
    const search = districtSearch.toLowerCase();
    return allDistricts.filter(d => d.name.toLowerCase().includes(search));
  }, [allDistricts, districtSearch]);

  // Доступные для выбора районы (не назначенные другим отделам)
  const availableDistricts = useMemo(() => {
    return filteredDistricts.filter(d => !assignedDistricts.has(d.name));
  }, [filteredDistricts, assignedDistricts]);

  // Сортированные зоны
  const sortedZones = useMemo(() => {
    const sorted = [...zones];
    sorted.sort((a, b) => {
      if (sortField === 'name') {
        const cmp = a.department_name.localeCompare(b.department_name, 'ru');
        return sortDir === 'asc' ? cmp : -cmp;
      } else {
        const cmp = a.district_names.length - b.district_names.length;
        return sortDir === 'asc' ? cmp : -cmp;
      }
    });
    return sorted;
  }, [zones, sortField, sortDir]);

  const handleSort = (field: 'name' | 'districts') => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  useEffect(() => {
    if (!requireAdmin()) return;
    loadInitialData();
  }, []);

  // Отслеживаем изменение размеров контейнера карты
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;

    // Устанавливаем размер сразу
    const rect = container.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      setMapSize({ width: rect.width, height: rect.height });
    }

    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setMapSize({ width, height });
      }
    });

    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Обработчик зума колесиком и перетаскивания - добавляем напрямую к DOM
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container || !geoUrl) return;

    const handleWheelEvent = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoomLevel(prev => Math.max(0.5, Math.min(3, prev + delta)));
    };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return; // только левая кнопка
      isDraggingRef.current = true;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      container.style.cursor = 'grabbing';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current || !lastMousePosRef.current) return;
      
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      
      // Более точная конвертация пикселей в градусы для проекции Меркатора
      const currentScaleValue = (baseScaleRef.current || 3000) * zoomLevel;
      // Коэффициент зависит от масштаба: чем больше scale, тем меньше градусов на пиксель
      const degreesPerPx = 100 / currentScaleValue;
      
      setMapCenter(prev => {
        const current = prev || mapConfig?.center || [61.85, 58.18];
        return [
          current[0] - dx * degreesPerPx,
          current[1] + dy * degreesPerPx * 0.7 // корректировка для широты
        ];
      });
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
      lastMousePosRef.current = null;
      container.style.cursor = 'grab';
    };

    const handleMouseLeave = () => {
      isDraggingRef.current = false;
      lastMousePosRef.current = null;
      container.style.cursor = 'grab';
    };

    container.addEventListener('wheel', handleWheelEvent, { passive: false });
    container.addEventListener('mousedown', handleMouseDown);
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('mouseleave', handleMouseLeave);
    
    return () => {
      container.removeEventListener('wheel', handleWheelEvent);
      container.removeEventListener('mousedown', handleMouseDown);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [geoUrl, mapConfig, zoomLevel]);

  // Сохраняем базовый scale и center при первой загрузке
  useEffect(() => {
    if (mapConfig && baseScaleRef.current === null) {
      baseScaleRef.current = mapConfig.scale;
      setMapCenter(mapConfig.center);
    }
  }, [mapConfig]);

  // Вычисляем текущий scale с учетом зума
  const currentScale = useMemo(() => {
    if (!mapConfig) return 3000;
    const base = baseScaleRef.current || mapConfig.scale;
    return Math.round(base * zoomLevel);
  }, [mapConfig, zoomLevel]);

  // Функция для загрузки списка районов и вычисления bounds
  const loadDistrictsAndBounds = async (url: string) => {
    try {
      const response = await fetch(url);
      const geojson = await response.json();
      
      if (!geojson.features || geojson.features.length === 0) {
        return;
      }

      // Извлекаем названия районов (исключаем пустые и "неизвестная территория")
      const excludeNames = ['неизвестная территория', 'unknown'];
      const districts: District[] = geojson.features
        .map((f: any) => ({
          name: f.properties?.name || f.properties?.NAME || ''
        }))
        .filter((d: District) => d.name && !excludeNames.includes(d.name.toLowerCase()))
        .sort((a: District, b: District) => a.name.localeCompare(b.name, 'ru'));
      
      setAllDistricts(districts);

      // Вычисляем bounds
      let minLon = Infinity, minLat = Infinity;
      let maxLon = -Infinity, maxLat = -Infinity;

      geojson.features.forEach((feature: any) => {
        const geometry = feature.geometry;
        const coords = geometry.coordinates;
        
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
        
        if (geometry.type === 'MultiPolygon') {
          coords.forEach((polygon: any[]) => {
            polygon.forEach((ring: any[]) => {
              ring.forEach((coord: any[]) => processCoords(coord));
            });
          });
        } else if (geometry.type === 'Polygon') {
          coords.forEach((ring: any[]) => {
            ring.forEach((coord: any[]) => processCoords(coord));
          });
        } else {
          processCoords(coords);
        }
      });

      if (minLon === Infinity || minLat === Infinity) {
        return;
      }

      const centerLon = (minLon + maxLon) / 2;
      const centerLat = (minLat + maxLat) / 2;
      const width = maxLon - minLon;
      const height = maxLat - minLat;
      
      const mapWidth = 800;
      const mapHeight = 400;
      const paddingFactor = 0.7;
      const scaleX = (mapWidth / width) * paddingFactor;
      const scaleY = (mapHeight / height) * paddingFactor;
      const baseScale = Math.min(scaleX, scaleY);
      const finalScale = Math.round(baseScale * 40);
      const clampedScale = Math.max(500, Math.min(8000, finalScale));
      
      setMapConfig({
        center: [centerLon, centerLat],
        scale: clampedScale,
      });
    } catch (error) {
      console.error('Error loading districts:', error);
    }
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      const settings = await fetchSystemSettings();
      
      if (settings && settings.region_ids && settings.region_ids.length > 0) {
        const primaryRegionId = settings.region_ids[0];
        
        const regionsResp = await fetch("/api/regions");
        if (regionsResp.ok) {
          const regions = (await regionsResp.json()) as Region[];
          const region = regions.find((r) => r.id === primaryRegionId);
          if (region) {
            setRegionName(region.name);
            const url = `/maps/ru/region/${primaryRegionId}/districts.geojson`;
            setGeoUrl(url);
            await loadDistrictsAndBounds(url);
          } else {
            setError(`Информация о регионе с ID ${primaryRegionId} не найдена`);
          }
        } else {
          setError("Не удалось загрузить список регионов");
        }
      } else {
        setError("Регион не выбран в настройках системы");
      }

      const data = await getAdministrativeZones(1);
      setZones(data);
      
      // Загружаем описания районов
      await loadDistrictDescriptions();
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

  const loadDistrictDescriptions = async () => {
    try {
      const data = await getDistrictDescriptions();
      const map = new Map<string, string>();
      data.forEach(d => {
        if (d.description) {
          map.set(d.district_name, d.description);
        }
      });
      setDistrictDescriptions(map);
    } catch (e: any) {
      console.error("Ошибка загрузки описаний районов:", e);
    }
  };

  // Функции модального окна описания района
  const openDistrictModal = (districtName: string) => {
    setDistrictModal({
      open: true,
      districtName,
      description: districtDescriptions.get(districtName) || '',
    });
  };

  const closeDistrictModal = () => {
    setDistrictModal({ open: false, districtName: '', description: '' });
  };

  const saveDistrictDescription = async () => {
    if (!districtModal.districtName) return;
    
    setDistrictSaving(true);
    try {
      await updateDistrictDescription(districtModal.districtName, {
        description: districtModal.description.trim() || null,
      });
      
      // Обновляем локальное состояние
      setDistrictDescriptions(prev => {
        const newMap = new Map(prev);
        if (districtModal.description.trim()) {
          newMap.set(districtModal.districtName, districtModal.description.trim());
        } else {
          newMap.delete(districtModal.districtName);
        }
        return newMap;
      });
      
      closeDistrictModal();
      setSuccessMessage(`Описание района "${districtModal.districtName}" сохранено`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка при сохранении описания");
    } finally {
      setDistrictSaving(false);
    }
  };

  const handleToggleDistrict = (districtName: string) => {
    setSelectedDistricts(prev => 
      prev.includes(districtName)
        ? prev.filter(d => d !== districtName)
        : [...prev, districtName]
    );
  };

  const handleSelectAll = () => {
    const availableNames = availableDistricts.map(d => d.name);
    setSelectedDistricts(prev => {
      const newSelected = [...prev];
      availableNames.forEach(name => {
        if (!newSelected.includes(name)) {
          newSelected.push(name);
        }
      });
      return newSelected;
    });
  };

  const handleDeselectAll = () => {
    setSelectedDistricts([]);
  };

  const handleAddZone = async () => {
    setFormError(null);
    setNameError(false);

    if (!departmentName.trim()) {
      setNameError(true);
      nameInputRef.current?.focus();
      return;
    }

    // Проверка на дублирование названия
    const nameExists = zones.some(
      z => z.department_name.toLowerCase().trim() === departmentName.toLowerCase().trim()
    );
    if (nameExists) {
      setFormError("Подразделение с таким названием уже существует");
      setNameError(true);
      nameInputRef.current?.focus();
      return;
    }

    if (selectedDistricts.length === 0) {
      setFormError("Выберите хотя бы один район");
      return;
    }

    try {
      setSaving(true);
      const savedName = departmentName.trim();
      
      await createAdministrativeZone({
        map_id: 1,
        department_name: departmentName,
        district_names: selectedDistricts,
      });

      // Очистка формы
      setDepartmentName("");
      setSelectedDistricts([]);
      
      // Перезагрузка списка
      await loadZones();
      setFormError(null);
      
      // Показываем модальное окно успеха
      setSuccessMessage(`Подразделение "${savedName}" успешно добавлено`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setFormError(e.message || "Ошибка при добавлении");
    } finally {
      setSaving(false);
    }
  };

  const openDeleteModal = (zone: AdministrativeZone) => {
    setDeleteModal({ open: true, zoneId: zone.id, zoneName: zone.department_name });
  };

  const closeDeleteModal = () => {
    setDeleteModal({ open: false, zoneId: null, zoneName: '' });
  };

  const confirmDelete = async () => {
    if (!deleteModal.zoneId) return;
    
    const zoneName = deleteModal.zoneName;
    
    try {
      await deleteAdministrativeZone(deleteModal.zoneId);
      await loadZones();
      closeDeleteModal();
      setSuccessMessage(`Подразделение "${zoneName}" успешно удалено`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка при удалении");
      closeDeleteModal();
    }
  };

  // Функции модального окна редактирования
  const openEditModal = (zone: AdministrativeZone) => {
    setEditModal({
      open: true,
      zone,
      name: zone.department_name,
      description: zone.description || '',
      selectedDistricts: new Set(zone.district_names),
    });
  };

  const closeEditModal = () => {
    setEditModal({ open: false, zone: null, name: '', description: '', selectedDistricts: new Set() });
  };

  const toggleEditDistrict = (districtName: string) => {
    setEditModal(prev => {
      const newSet = new Set(prev.selectedDistricts);
      if (newSet.has(districtName)) {
        newSet.delete(districtName);
      } else {
        newSet.add(districtName);
      }
      return { ...prev, selectedDistricts: newSet };
    });
  };

  const saveEdit = async () => {
    if (!editModal.zone) return;
    
    const trimmedName = editModal.name.trim();
    if (!trimmedName) {
      setError("Введите название подразделения");
      return;
    }

    if (editModal.selectedDistricts.size === 0) {
      setError("Выберите хотя бы один район");
      return;
    }
    
    setEditSaving(true);
    try {
      await updateAdministrativeZone(editModal.zone.id, {
        department_name: trimmedName,
        description: editModal.description.trim() || null,
        district_names: Array.from(editModal.selectedDistricts),
      });
      await loadZones();
      closeEditModal();
      setSuccessMessage(`Подразделение "${trimmedName}" успешно обновлено`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка при сохранении");
    } finally {
      setEditSaving(false);
    }
  };

  // Получаем цвет для района на основе назначения
  const getDistrictColor = (districtName: string) => {
    // Проверяем, выбран ли район в форме
    if (selectedDistricts.includes(districtName)) {
      return { fill: "rgba(14, 165, 233, 0.5)", stroke: "rgba(14, 165, 233, 0.8)" }; // sky-500
    }
    
    // Проверяем, назначен ли район какому-то отделу
    for (const zone of zones) {
      if (zone.district_names.includes(districtName)) {
        return { fill: "rgba(34, 197, 94, 0.4)", stroke: "rgba(34, 197, 94, 0.7)" }; // green-500
      }
    }
    
    // Район не назначен - серый контур
    return { fill: "rgba(148, 163, 184, 0.1)", stroke: "rgba(148, 163, 184, 0.5)" };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white px-4 py-4">
      <div className="max-w-7xl mx-auto">
        {/* Навигация */}
        <div className="mb-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-sm">
            {/* Группа 1: Регион, Зоны, Пользователи, Журналирование */}
            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
              <button
                type="button"
                onClick={() => { window.location.href = "/admin"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Регион и управление
              </button>
              <button
                type="button"
                className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
              >
                Зоны и устройства
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
                onClick={() => { window.location.href = "/admin/journal"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Журналирование
              </button>
            </div>
            {/* Группа 2: Слои, События */}
            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
              <button
                type="button"
                onClick={() => { window.location.href = "/editor/layers"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Слои
              </button>
              <button
                type="button"
                onClick={() => { window.location.href = "/editor/events"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                События
              </button>
              <button
                type="button"
                onClick={() => { window.location.href = "/editor/reports"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Отчёты
              </button>
            </div>
            {/* Группа 3: Обстановка */}
            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
              <button
                type="button"
                onClick={() => { window.location.href = "/situation"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Обстановка
              </button>
            </div>
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

        {/* Заголовок */}
        <h1 className="text-2xl font-semibold tracking-tight mb-3">Зоны и устройства</h1>


        {/* Ошибка */}
        {error && (
          <div className="mb-6 rounded-2xl border border-red-500/60 bg-red-500/10 p-4 text-red-100">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Легенда */}
        <div className="mb-3 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-slate-400/20 border border-slate-400/50"></div>
            <span className="text-slate-400">Свободный</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-sky-500/50 border border-sky-500/80"></div>
            <span className="text-slate-300">Выбран</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-green-500/40 border border-green-500/70"></div>
            <span className="text-slate-300">Назначен</span>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Карта */}
          <div className="xl:col-span-2 rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold">Карта: {regionName}</h2>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span>{Math.round(zoomLevel * 100)}%</span>
                <button
                  onClick={() => { setZoomLevel(1); setMapCenter(mapConfig?.center || null); }}
                  className="px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
                >
                  Сброс
                </button>
                </div>
            </div>
            
            {geoUrl ? (
              <div className="relative">
                <div 
                  ref={mapContainerRef}
                  className="w-full h-[calc(100vh-240px)] min-h-[400px] rounded-xl overflow-hidden bg-slate-800/50 relative cursor-grab active:cursor-grabbing"
                >
                  <ComposableMap
                    projection="geoMercator"
                    projectionConfig={{ 
                      scale: currentScale, 
                      center: mapCenter || mapConfig?.center || [61.85, 58.18] 
                    }}
                    width={mapSize.width || 800}
                    height={mapSize.height || 400}
                    style={{ width: "100%", height: "100%", display: "block" }}
                  >
                    <Geographies geography={geoUrl}>
                    {({ geographies }) => {
                      const validGeographies = geographies.filter((geo) => {
                          if (!geo.geometry || !geo.geometry.coordinates) return false;
                        const coords = geo.geometry.coordinates;
                        const geomType = geo.geometry.type;
                          return (geomType === 'MultiPolygon' || geomType === 'Polygon') && Array.isArray(coords) && coords.length > 0;
                      });
                      
                      return validGeographies.map((geo, index) => {
                        const props = geo.properties as any;
                        const districtName = props?.name || props?.NAME || `Район ${index + 1}`;
                          const colors = getDistrictColor(districtName);
                          
                          return (
                            <Geography
                              key={geo.rsmKey || `district-${index}`}
                              geography={geo}
                              onMouseEnter={() => setHoveredDistrict(districtName)}
                              onMouseLeave={() => setHoveredDistrict(null)}
                              onClick={() => {
                                if (!assignedDistricts.has(districtName)) {
                                  handleToggleDistrict(districtName);
                                }
                              }}
                              stroke={colors.stroke}
                              strokeWidth={0.5 / zoomLevel}
                              style={{
                                default: { fill: colors.fill, outline: "none" },
                                hover: {
                                  fill: assignedDistricts.has(districtName) ? colors.fill : "rgba(14, 165, 233, 0.3)",
                                  outline: "none",
                                  cursor: assignedDistricts.has(districtName) ? "default" : "pointer" 
                                },
                                pressed: { fill: colors.fill, outline: "none" },
                              }}
                            />
                          );
                        });
                    }}
                  </Geographies>
                </ComposableMap>
                </div>
                
                {hoveredDistrict && (
                  <div className="absolute top-4 left-4 bg-slate-900/95 px-4 py-2 rounded-lg text-sm font-semibold text-sky-400 border border-sky-500/30 shadow-lg pointer-events-none z-10">
                    {hoveredDistrict}
                    {assignedDistricts.has(hoveredDistrict) && (
                      <span className="ml-2 text-green-400 font-normal">(назначен)</span>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="h-[calc(100vh-240px)] min-h-[400px] rounded-xl bg-slate-800/50 flex items-center justify-center text-slate-400">
                {loading ? "Загрузка карты..." : "Карта не загружена. Проверьте настройки региона."}
              </div>
            )}
            </div>
            
          {/* Районы и форма добавления */}
          <div className="space-y-4">
            {/* Список районов */}
            <div className="rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4 h-[calc(100vh-420px)] min-h-[250px] max-h-[350px] flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-base font-semibold">Районы ({availableDistricts.length})</h2>
                <div className="flex gap-2">
                  <button
                    onClick={handleSelectAll}
                    className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
                  >
                    Все
                  </button>
                  <button
                    onClick={handleDeselectAll}
                    className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
                  >
                    Сбросить
                  </button>
                </div>
                    </div>
              
              <input
                type="text"
                value={districtSearch}
                onChange={(e) => setDistrictSearch(e.target.value)}
                placeholder="Поиск района..."
                className="w-full mb-2 rounded-lg border border-slate-700/70 bg-slate-900/80 px-3 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              />
              
              <div className="flex-1 overflow-y-auto space-y-0.5">
                {availableDistricts.map(district => (
                  <label
                    key={district.name}
                    className={`flex items-center gap-2 px-2 py-1 rounded cursor-pointer transition-colors ${
                      selectedDistricts.includes(district.name)
                        ? 'bg-sky-500/20 border border-sky-500/40'
                        : 'hover:bg-slate-800/60 border border-transparent'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedDistricts.includes(district.name)}
                      onChange={() => handleToggleDistrict(district.name)}
                      className="w-3 h-3 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500/50"
                    />
                    <span className="text-xs text-slate-200">{district.name}</span>
                  </label>
                ))}
                {availableDistricts.length === 0 && (
                  <div className="text-center py-2 text-slate-500 text-xs">
                    {districtSearch ? "Не найдено" : "Все назначены"}
                    </div>
                  )}
                </div>
          </div>

            {/* Форма добавления */}
            <div className="rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4">
              <h2 className="text-base font-semibold mb-3">Добавить подразделение</h2>

              {formError && (
                <div className="mb-3 rounded-lg border border-red-500/60 bg-red-500/10 p-2 text-red-100 text-xs">
                  {formError}
                </div>
              )}

              <div className="mb-3">
                <input
                  ref={nameInputRef}
                  type="text"
                  value={departmentName}
                  onChange={(e) => { setDepartmentName(e.target.value); setNameError(false); }}
                  placeholder="Название подразделения"
                  className={`w-full rounded-lg border bg-slate-900/80 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                    nameError 
                      ? 'border-red-500 focus:ring-red-500/50' 
                      : 'border-slate-700/70 focus:ring-sky-500/50'
                  }`}
                />
                {nameError && (
                  <p className="mt-1 text-xs text-red-400">Введите название подразделения</p>
                )}
              </div>

              {/* Выбранные районы */}
              <div className="mb-3">
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Выбрано: {selectedDistricts.length}
                </label>
                {selectedDistricts.length > 0 ? (
                  <div className="flex flex-wrap gap-1 p-2 rounded-lg border border-slate-700/70 bg-slate-900/80 max-h-16 overflow-y-auto">
                    {selectedDistricts.map(name => (
                      <span 
                        key={name}
                        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-sky-500/20 border border-sky-500/40 text-xs text-sky-300"
                      >
                        {name}
                        <button
                          onClick={() => handleToggleDistrict(name)}
                          className="ml-0.5 hover:text-red-400"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="p-2 rounded-lg border border-slate-700/70 bg-slate-900/80 text-xs text-slate-500">
                    Выберите районы на карте или из списка
                  </div>
                )}
              </div>

              <button
                onClick={handleAddZone}
                disabled={saving}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {saving ? "..." : "Добавить"}
              </button>
            </div>
          </div>
            </div>

            {/* Таблица зон */}
        <div className="mt-4 rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700/60">
            <h2 className="text-base font-semibold">Назначенные подразделения</h2>
          </div>

              {loading ? (
            <div className="p-4 text-center text-slate-300 text-sm">Загрузка...</div>
              ) : zones.length === 0 ? (
            <div className="p-4 text-center text-slate-400 text-sm">
              Нет созданных подразделений
                </div>
              ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-800/60">
                  <tr>
                    <th 
                      className="px-4 py-2 text-left text-xs font-semibold text-slate-300 uppercase cursor-pointer hover:text-sky-400 transition-colors"
                      onClick={() => handleSort('name')}
                    >
                      Подразделение {sortField === 'name' && (sortDir === 'asc' ? '↑' : '↓')}
                        </th>
                        <th
                      className="px-4 py-2 text-left text-xs font-semibold text-slate-300 uppercase cursor-pointer hover:text-sky-400 transition-colors"
                      onClick={() => handleSort('districts')}
                    >
                      Районы {sortField === 'districts' && (sortDir === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-slate-300 uppercase">
                      
                        </th>
                      </tr>
                    </thead>
                <tbody className="divide-y divide-slate-800">
                  {sortedZones.map((zone) => (
                    <tr key={zone.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-2 whitespace-nowrap text-sm">
                        <button
                          onClick={() => openEditModal(zone)}
                          className="text-slate-100 font-medium hover:text-sky-400 transition-colors text-left"
                        >
                          {zone.department_name}
                        </button>
                        {zone.description && (
                          <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">{zone.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1 max-w-xl">
                          {zone.district_names.length > 0 ? (
                            zone.district_names.map(name => (
                            <button
                                key={name}
                                onClick={() => openDistrictModal(name)}
                                className="inline-block px-1.5 py-0.5 rounded bg-green-500/20 border border-green-500/40 text-xs text-green-300 hover:bg-green-500/30 hover:border-green-500/60 transition-colors cursor-pointer"
                                title={districtDescriptions.get(name) || "Нажмите, чтобы добавить описание"}
                              >
                                {name}
                                {districtDescriptions.has(name) && (
                                  <span className="ml-1 text-green-400">📝</span>
                                )}
                              </button>
                            ))
                          ) : (
                            <span className="text-slate-500 text-xs">—</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-right">
                        <button
                          onClick={() => openDeleteModal(zone)}
                          className="rounded bg-red-500/20 border border-red-500/40 px-3 py-1 text-xs font-medium text-red-300 hover:bg-red-500/30 hover:border-red-500/60 transition"
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

      {/* Модальное окно удаления */}
      {deleteModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeDeleteModal}></div>
          <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-2">Удалить подразделение?</h3>
            <p className="text-slate-400 text-sm mb-6">
              Вы уверены, что хотите удалить подразделение <span className="text-white font-medium">«{deleteModal.zoneName}»</span>? Это действие нельзя отменить.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={closeDeleteModal}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
              >
                Отмена
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition"
              >
                Удалить
              </button>
        </div>
      </div>
        </div>
      )}

      {/* Модальное окно успешного удаления */}
      {successMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSuccessMessage(null)}></div>
          <div className="relative bg-slate-900 border border-green-500/50 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="text-green-400 text-xl">✓</span>
              </div>
              <h3 className="text-lg font-semibold text-white">Успешно</h3>
            </div>
            <p className="text-slate-300 text-sm mb-6">{successMessage}</p>
            <div className="flex justify-end">
              <button
                onClick={() => setSuccessMessage(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-green-500 text-white hover:bg-green-600 transition"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно редактирования подразделения */}
      {editModal.open && editModal.zone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeEditModal}></div>
          <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Редактирование подразделения</h3>
              <button
                onClick={closeEditModal}
                className="text-slate-400 hover:text-slate-200 text-2xl leading-none"
              >
                ×
              </button>
            </div>
            
            {/* Название */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-1">Название подразделения</label>
              <input
                type="text"
                value={editModal.name}
                onChange={(e) => setEditModal(prev => ({ ...prev, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                placeholder="Введите название"
              />
            </div>
            
            {/* Описание */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-1">Описание</label>
              <textarea
                value={editModal.description}
                onChange={(e) => setEditModal(prev => ({ ...prev, description: e.target.value }))}
                rows={3}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 resize-none"
                placeholder="Введите описание подразделения (необязательно)"
              />
            </div>
            
            {/* Районы */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Районы ({editModal.selectedDistricts.size} выбрано)
              </label>
              <div className="rounded-lg border border-slate-700 bg-slate-800 p-2 max-h-48 overflow-y-auto">
                {allDistricts.length === 0 ? (
                  <div className="text-slate-500 text-sm text-center py-2">Нет районов</div>
                ) : (
                  <div className="space-y-1">
                    {allDistricts.map(district => {
                      const isSelected = editModal.selectedDistricts.has(district.name);
                      const isAssignedToOther = assignedDistricts.has(district.name) && !editModal.zone?.district_names.includes(district.name);
                      
                      return (
                        <label
                          key={district.name}
                          className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors ${
                            isSelected 
                              ? 'bg-sky-500/20 text-sky-300' 
                              : isAssignedToOther
                                ? 'bg-slate-700/30 text-slate-500 cursor-not-allowed'
                                : 'hover:bg-slate-700/50 text-slate-300'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            disabled={isAssignedToOther}
                            onChange={() => !isAssignedToOther && toggleEditDistrict(district.name)}
                            className="rounded border-slate-600 bg-slate-700 text-sky-500 focus:ring-sky-500/50"
                          />
                          <span className="text-sm">{district.name}</span>
                          {isAssignedToOther && (
                            <span className="text-xs text-slate-500 ml-auto">(назначен другому)</span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
            
            {/* Выбранные районы */}
            {editModal.selectedDistricts.size > 0 && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-300 mb-1">Выбранные районы:</label>
                <div className="flex flex-wrap gap-1">
                  {Array.from(editModal.selectedDistricts).map(name => (
                    <span
                      key={name}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-sky-500/20 border border-sky-500/40 text-xs text-sky-300"
                    >
                      {name}
                      <button
                        onClick={() => toggleEditDistrict(name)}
                        className="hover:text-sky-100"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* Кнопки */}
            <div className="flex gap-3 justify-end pt-2 border-t border-slate-700">
              <button
                onClick={closeEditModal}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
              >
                Отмена
              </button>
              <button
                onClick={saveEdit}
                disabled={editSaving || !editModal.name.trim() || editModal.selectedDistricts.size === 0}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-sky-500 text-white hover:bg-sky-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {editSaving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно описания района */}
      {districtModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeDistrictModal}></div>
          <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-lg w-full mx-4 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Описание района</h3>
              <button
                onClick={closeDistrictModal}
                className="text-slate-400 hover:text-slate-200 text-2xl leading-none"
              >
                ×
              </button>
            </div>
            
            {/* Название района */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-1">Район</label>
              <div className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white">
                {districtModal.districtName}
              </div>
            </div>
            
            {/* Описание */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-1">Описание</label>
              <textarea
                value={districtModal.description}
                onChange={(e) => setDistrictModal(prev => ({ ...prev, description: e.target.value }))}
                rows={5}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 resize-none"
                placeholder="Введите описание района (необязательно)"
              />
            </div>
            
            {/* Кнопки */}
            <div className="flex gap-3 justify-end pt-2 border-t border-slate-700">
              <button
                onClick={closeDistrictModal}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
              >
                Отмена
              </button>
              <button
                onClick={saveDistrictDescription}
                disabled={districtSaving}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-sky-500 text-white hover:bg-sky-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {districtSaving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
