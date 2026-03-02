import React, { useEffect, useState, useRef, useMemo, useCallback } from "react";
import { requireEditor, handleAuthError, logout, isAdmin, canEditEvent } from "../utils/auth";
import { Modal } from "../components/Modal";
import { fetchSystemSettings } from "../api/admin";
import { getAdministrativeZones, type AdministrativeZone } from "../api/administrative-zones";
import { getEvents, getEvent, createEvent, updateEvent, deleteEvent, type EventListItem, type EventDetail } from "../api/events";
import { getLayers, type Layer } from "../api/layers";

type District = {
  name: string;
};

export function EventsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noRegion, setNoRegion] = useState(false);
  
  // Список районов и подразделений
  const [allDistricts, setAllDistricts] = useState<District[]>([]);
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  
  // Список событий
  const [events, setEvents] = useState<EventListItem[]>([]);
  
  // Форма создания события
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [responsibleZone, setResponsibleZone] = useState<AdministrativeZone | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [importance, setImportance] = useState(5);
  const [images, setImages] = useState<File[]>([]);
  const [documents, setDocuments] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  
  // Слои для привязки события
  const [layers, setLayers] = useState<Layer[]>([]);
  const [selectedLayerId, setSelectedLayerId] = useState<number | null>(null);
  const [selectedSubLayerId, setSelectedSubLayerId] = useState<number | null>(null);
  const [selectedSubSubLayerId, setSelectedSubSubLayerId] = useState<number | null>(null);
  
  // Модальное окно успешного создания
  const [createSuccessModal, setCreateSuccessModal] = useState<{ open: boolean; eventTitle: string }>({
    open: false, eventTitle: ""
  });
  
  // Модальное окно удаления
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; eventId: number | null; eventTitle: string }>({ 
    open: false, eventId: null, eventTitle: "" 
  });
  
  // Модальное окно успешного удаления
  const [deleteSuccessModal, setDeleteSuccessModal] = useState<{ open: boolean; eventTitle: string }>({
    open: false, eventTitle: ""
  });
  
  // Модальное окно просмотра/редактирования события
  const [viewEvent, setViewEvent] = useState<EventDetail | null>(null);
  const [loadingEvent, setLoadingEvent] = useState(false);
  const [isEditingEvent, setIsEditingEvent] = useState(false);
  const [editEventData, setEditEventData] = useState<{
    title: string;
    description: string;
    importance: number;
    status: string;
    layerValue: string;
    districtName: string;
  }>({ title: '', description: '', importance: 5, status: 'warning', layerValue: '', districtName: '' });
  const [savingEvent, setSavingEvent] = useState(false);

  // Словарь статусов на русском
  const STATUS_LABELS: Record<string, string> = {
    ok: "В норме",
    warning: "Внимание",
    alert: "Тревога",
  };

  // Функции закрытия модальных окон
  const closeViewEvent = useCallback(() => {
    setViewEvent(null);
    setIsEditingEvent(false);
  }, []);

  const closeDeleteSuccessModal = useCallback(() => {
    setDeleteSuccessModal({ open: false, eventTitle: "" });
  }, []);

  const closeCreateSuccessModal = useCallback(() => {
    setCreateSuccessModal({ open: false, eventTitle: "" });
  }, []);

  // Загрузка деталей события
  const handleViewEvent = async (eventId: number) => {
    try {
      setLoadingEvent(true);
      setIsEditingEvent(false);
      const detail = await getEvent(eventId);
      setViewEvent(detail);
    } catch (e: any) {
      console.error(e);
      setFormError("Ошибка загрузки события");
    } finally {
      setLoadingEvent(false);
    }
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

  // Начать редактирование события
  const startEditingEvent = () => {
    if (!viewEvent) return;
    
    // Определяем текущее значение слоя
    let layerValue = '';
    if (viewEvent.sub_sub_layer_id) {
      layerValue = `subsub_${viewEvent.sub_sub_layer_id}`;
    } else if (viewEvent.sub_layer_id) {
      layerValue = `sub_${viewEvent.sub_layer_id}`;
    } else if (viewEvent.layer_id) {
      layerValue = `layer_${viewEvent.layer_id}`;
    }
    
    setEditEventData({
      title: viewEvent.title,
      description: viewEvent.description || '',
      importance: viewEvent.importance,
      status: viewEvent.status,
      layerValue,
      districtName: viewEvent.district_name || '',
    });
    setIsEditingEvent(true);
  };

  // Сохранить изменения события
  const saveEventChanges = async () => {
    if (!viewEvent) return;
    
    if (!editEventData.title.trim()) {
      setFormError("Введите название события");
      return;
    }
    
    if (!editEventData.districtName) {
      setFormError("Выберите район");
      return;
    }
    
    // Парсим значение слоя
    let layerId: number | null = null;
    let subLayerId: number | null = null;
    let subSubLayerId: number | null = null;
    
    if (editEventData.layerValue) {
      const [type, id] = editEventData.layerValue.split('_');
      const numId = parseInt(id);
      if (type === 'layer') layerId = numId;
      else if (type === 'sub') subLayerId = numId;
      else if (type === 'subsub') subSubLayerId = numId;
    }
    
    setSavingEvent(true);
    try {
      const updated = await updateEvent(viewEvent.id, {
        title: editEventData.title.trim(),
        description: editEventData.description.trim() || null,
        importance: editEventData.importance,
        status: editEventData.status,
        district_name: editEventData.districtName,
        layer_id: layerId,
        sub_layer_id: subLayerId,
        sub_sub_layer_id: subSubLayerId,
      });
      
      setViewEvent(updated);
      setIsEditingEvent(false);
      
      // Обновляем список событий
      const updatedEvents = await getEvents();
      setEvents(updatedEvents);
      
      setCreateSuccessModal({ open: true, eventTitle: updated.title });
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setFormError(e.message || "Ошибка при сохранении события");
    } finally {
      setSavingEvent(false);
    }
  };

  // Отменить редактирование
  const cancelEditingEvent = () => {
    setIsEditingEvent(false);
  };
  
  // Refs для файловых инпутов
  const imagesInputRef = useRef<HTMLInputElement>(null);
  const documentsInputRef = useRef<HTMLInputElement>(null);

  // Находим ответственное подразделение при выборе района
  useEffect(() => {
    if (selectedDistrict && zones.length > 0) {
      const zone = zones.find(z => z.district_names.includes(selectedDistrict));
      setResponsibleZone(zone || null);
    } else {
      setResponsibleZone(null);
    }
  }, [selectedDistrict, zones]);

  useEffect(() => {
    if (!requireEditor()) return;
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Загружаем настройки системы для получения выбранного региона
      const settings = await fetchSystemSettings();
      if (!settings || !settings.region_ids || settings.region_ids.length === 0) {
        // Регион не выбран — загружаем данные без карты районов
        setLoading(false);
        setNoRegion(true);
        return;
      }

      // Загружаем районы из ВСЕХ выбранных регионов
      await loadDistrictsFromAllRegions(settings.region_ids);
      
      // Загружаем административные зоны
      const zonesData = await getAdministrativeZones();
      setZones(zonesData);
      
      // Загружаем слои
      try {
        const layersData = await getLayers();
        setLayers(layersData);
      } catch (layerErr) {
        console.error("Ошибка загрузки слоёв:", layerErr);
      }
      
      // Загружаем события
      const eventsData = await getEvents();
      setEvents(eventsData);
      
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  };

  const loadDistrictsFromAllRegions = async (regionIds: string[]) => {
    try {
      const fetches = regionIds.map(async (id) => {
        const resp = await fetch(`/maps/ru/region/${id}/districts.geojson?v=2`);
        if (!resp.ok) return null;
        return resp.json();
      });
      const geoJsons = (await Promise.all(fetches)).filter(Boolean);

      const excludeNames = ['неизвестная территория', 'unknown'];
      const namesSet = new Set<string>();
      geoJsons.forEach((gj: any) => {
        gj.features?.forEach((f: any) => {
          const name = f.properties?.name || f.properties?.NAME || '';
          if (name && !excludeNames.includes(name.toLowerCase())) {
            namesSet.add(name);
          }
        });
      });

      const districts: District[] = Array.from(namesSet)
        .map(name => ({ name }))
        .sort((a, b) => a.name.localeCompare(b.name, 'ru'));

      setAllDistricts(districts);
    } catch (e) {
      console.error("Ошибка загрузки районов:", e);
    }
  };

  const handleSubmit = async () => {
    setFormError(null);
    
    if (!selectedDistrict) {
      setFormError("Выберите район");
      return;
    }
    
    if (!title.trim()) {
      setFormError("Введите название события");
      return;
    }
    
    try {
      setSaving(true);
      
      const eventTitle = title.trim();
      
      await createEvent({
        map_id: 1,
        district_name: selectedDistrict,
        title: eventTitle,
        description: description.trim() || undefined,
        importance,
        layer_id: selectedLayerId,
        sub_layer_id: selectedSubLayerId,
        sub_sub_layer_id: selectedSubSubLayerId,
        images: images.length > 0 ? images : undefined,
        documents: documents.length > 0 ? documents : undefined,
      });
      
      // Очищаем форму
      setSelectedDistrict("");
      setTitle("");
      setDescription("");
      setImportance(5);
      setSelectedLayerId(null);
      setSelectedSubLayerId(null);
      setSelectedSubSubLayerId(null);
      setImages([]);
      setDocuments([]);
      if (imagesInputRef.current) imagesInputRef.current.value = "";
      if (documentsInputRef.current) documentsInputRef.current.value = "";
      
      // Перезагружаем список событий
      const eventsData = await getEvents();
      setEvents(eventsData);
      
      // Показываем модальное окно успеха
      setCreateSuccessModal({ open: true, eventTitle });
      
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setFormError(e.response?.data?.detail || e.message || "Ошибка создания события");
    } finally {
      setSaving(false);
    }
  };

  const openDeleteModal = (eventId: number, eventTitle: string) => {
    setDeleteModal({ open: true, eventId, eventTitle });
  };

  const closeDeleteModal = () => {
    setDeleteModal({ open: false, eventId: null, eventTitle: "" });
  };

  const confirmDelete = async () => {
    if (!deleteModal.eventId) return;
    
    const eventTitle = deleteModal.eventTitle;
    
    try {
      await deleteEvent(deleteModal.eventId);
      const eventsData = await getEvents();
      setEvents(eventsData);
      closeDeleteModal();
      setDeleteSuccessModal({ open: true, eventTitle });
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setFormError(e.response?.data?.detail || "Ошибка удаления события");
      closeDeleteModal();
    }
  };

  const handleImagesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setImages(Array.from(e.target.files));
    }
  };

  const handleDocumentsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setDocuments(Array.from(e.target.files));
    }
  };

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white px-4 py-4">
      <div className="max-w-7xl mx-auto">
        {/* Навигация */}
        <div className="mb-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-sm">
            {/* Группа 1: Регион, Зоны, Пользователи, Журналирование (только для админов) */}
            {isAdmin() && (
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
                  onClick={() => { window.location.href = "/admin/zones"; }}
                  className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
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
            )}
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
                className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
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
        <h1 className="text-2xl font-semibold tracking-tight mb-3">События</h1>
      </div>

      {loading ? (
        <div className="max-w-7xl mx-auto py-10 text-center text-slate-300">Загрузка...</div>
      ) : noRegion ? (
        <div className="max-w-7xl mx-auto py-16 text-center">
          <div className="rounded-2xl border border-sky-700/50 bg-sky-950/40 px-6 py-8 max-w-md mx-auto">
            <p className="text-slate-200 text-lg font-medium mb-2">Регион не выбран</p>
            <p className="text-slate-400 text-sm mb-4">Для работы с событиями необходимо выбрать регион мониторинга в настройках системы.</p>
            {isAdmin() && (
              <button onClick={() => window.location.href = "/admin"} className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/30 text-sm font-medium transition-colors">
                Перейти в настройки
              </button>
            )}
          </div>
        </div>
      ) : error ? (
        <div className="max-w-7xl mx-auto">
          <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-4 py-3 text-red-100">
            {error}
          </div>
        </div>
      ) : (
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          {/* Форма создания события */}
          <div className="lg:col-span-2 rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4">
            <h2 className="text-base font-semibold mb-3">Новое событие</h2>
            
            {formError && (
              <div className="mb-3 rounded-lg border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                {formError}
              </div>
            )}
            
            
            <div className="space-y-3">
              {/* Район */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Район *</label>
                <select
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-900/80 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  <option value="">Выберите район</option>
                  {allDistricts.map(d => (
                    <option key={d.name} value={d.name}>{d.name}</option>
                  ))}
                </select>
              </div>
              
              {/* Ответственное подразделение */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Ответственное подразделение</label>
                <div className="rounded-lg border border-slate-700/70 bg-slate-800/50 px-3 py-2 text-sm">
                  {responsibleZone ? (
                    <span className="text-sky-300">{responsibleZone.department_name}</span>
                  ) : (
                    <span className="text-slate-500">
                      {selectedDistrict ? "Подразделение не назначено" : "Сначала выберите район"}
                    </span>
                  )}
                </div>
              </div>
              
              {/* Выбор слоя */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Привязка к слою (опционально)</label>
                <select
                  value={selectedSubSubLayerId ? `subsub_${selectedSubSubLayerId}` : selectedSubLayerId ? `sub_${selectedSubLayerId}` : selectedLayerId ? `layer_${selectedLayerId}` : ""}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (!value) {
                      setSelectedLayerId(null);
                      setSelectedSubLayerId(null);
                      setSelectedSubSubLayerId(null);
                    } else if (value.startsWith('layer_')) {
                      setSelectedLayerId(parseInt(value.replace('layer_', '')));
                      setSelectedSubLayerId(null);
                      setSelectedSubSubLayerId(null);
                    } else if (value.startsWith('sub_')) {
                      setSelectedSubLayerId(parseInt(value.replace('sub_', '')));
                      setSelectedSubSubLayerId(null);
                      // Найти родительский layer
                      const subId = parseInt(value.replace('sub_', ''));
                      for (const layer of layers) {
                        const sub = layer.sub_layers.find(s => s.id === subId);
                        if (sub) {
                          setSelectedLayerId(layer.id);
                          break;
                        }
                      }
                    } else if (value.startsWith('subsub_')) {
                      const subSubId = parseInt(value.replace('subsub_', ''));
                      setSelectedSubSubLayerId(subSubId);
                      // Найти родительские слои
                      for (const layer of layers) {
                        for (const sub of layer.sub_layers) {
                          const subSub = sub.sub_sub_layers?.find(ss => ss.id === subSubId);
                          if (subSub) {
                            setSelectedLayerId(layer.id);
                            setSelectedSubLayerId(sub.id);
                            break;
                          }
                        }
                      }
                    }
                  }}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                  disabled={layers.length === 0}
                >
                  <option value="" className="bg-slate-800">{layers.length === 0 ? "Слои не созданы" : "Без привязки к слою"}</option>
                  {layers.map((layer) => (
                    <React.Fragment key={layer.id}>
                      <option value={`layer_${layer.id}`} className="bg-slate-800">
                        {layer.name}
                      </option>
                      {(layer.sub_layers || []).map((sub) => (
                        <React.Fragment key={sub.id}>
                          <option value={`sub_${sub.id}`} className="bg-slate-800">
                            &nbsp;&nbsp;↳ {sub.name}
                          </option>
                          {(sub.sub_sub_layers || []).map((subSub) => (
                            <option key={subSub.id} value={`subsub_${subSub.id}`} className="bg-slate-800">
                              &nbsp;&nbsp;&nbsp;&nbsp;↳↳ {subSub.name}
                            </option>
                          ))}
                        </React.Fragment>
                      ))}
                    </React.Fragment>
                  ))}
                </select>
              </div>
              
              {/* Название события */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Название события *</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Введите название"
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-900/80 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                />
              </div>
              
              {/* Описание */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Описание</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Опишите событие подробно..."
                  rows={4}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-900/80 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50 resize-y min-h-[80px]"
                />
              </div>
              
              {/* Коэффициент важности */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Коэффициент важности: <span className={getImportanceColor(importance)}>{importance}</span>
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={importance}
                    onChange={(e) => setImportance(Number(e.target.value))}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sky-500"
                  />
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={importance}
                    onChange={(e) => {
                      const val = Math.max(1, Math.min(10, Number(e.target.value) || 1));
                      setImportance(val);
                    }}
                    className={`w-16 rounded-lg border border-slate-700/70 bg-slate-900/80 px-2 py-1 text-sm text-center focus:outline-none focus:ring-2 focus:ring-sky-500/50 ${getImportanceColor(importance)}`}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>1 (низкая)</span>
                  <span>10 (высокая)</span>
                </div>
              </div>
              
              {/* Изображения и Документы в одной строке */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Изображения</label>
                  <input
                    ref={imagesInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handleImagesChange}
                    className="w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-sky-500/20 file:text-sky-300 hover:file:bg-sky-500/30 cursor-pointer"
                  />
                  {images.length > 0 && (
                    <p className="mt-1 text-xs text-slate-400">Выбрано: {images.length}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Документы</label>
                  <input
                    ref={documentsInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.txt"
                    multiple
                    onChange={handleDocumentsChange}
                    className="w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-sky-500/20 file:text-sky-300 hover:file:bg-sky-500/30 cursor-pointer"
                  />
                  {documents.length > 0 && (
                    <p className="mt-1 text-xs text-slate-400">Выбрано: {documents.length}</p>
                  )}
                </div>
              </div>
              
              {/* Кнопка создания */}
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="w-full px-4 py-2 rounded-lg bg-sky-500 text-slate-950 font-medium text-sm hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? "Сохранение..." : "Создать событие"}
              </button>
            </div>
          </div>
          
          {/* Список событий */}
          <div className="lg:col-span-1 rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4 flex flex-col overflow-hidden max-h-[645px]">
            <h2 className="text-base font-semibold mb-3 shrink-0">Список событий ({events.length})</h2>
            
            {events.length === 0 ? (
              <div className="text-center py-10 text-slate-400 flex-1">
                <p>Событий пока нет</p>
                <p className="text-xs mt-1">Создайте первое событие с помощью формы слева</p>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto flex-1 min-h-0">
                {events.map(event => (
                  <div
                    key={event.id}
                    onClick={() => handleViewEvent(event.id)}
                    className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-3 hover:bg-slate-800/70 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getImportanceBg(event.importance)}`}>
                            {event.importance}
                          </span>
                          <h3 className="font-medium text-sm truncate">{event.title}</h3>
                        </div>
                        <div className="text-xs text-slate-400 space-y-0.5">
                          <p className="truncate">
                            <span className="text-slate-500">Район:</span> {event.district_name || "—"}
                          </p>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <span className="text-slate-500 text-[10px]">
                              Создано: {new Date(event.created_at).toLocaleDateString("ru-RU")} {new Date(event.created_at).toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {event.created_by_name && (
                              <span className="text-emerald-400 text-[10px]">
                                {event.created_by_name}
                              </span>
                            )}
                          </div>
                          {event.updated_at && (
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-orange-400/70 text-[10px]">
                                Изменено: {new Date(event.updated_at).toLocaleDateString("ru-RU")} {new Date(event.updated_at).toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })}
                              </span>
                              {event.updated_by_name && (
                                <span className="text-orange-400 text-[10px]">
                                  {event.updated_by_name}
                                </span>
                              )}
                            </div>
                          )}
                          <div className="flex items-center gap-2 flex-wrap">
                            {event.images_count > 0 && (
                              <span className="text-sky-400 text-[10px]">📷 {event.images_count}</span>
                            )}
                            {event.documents_count > 0 && (
                              <span className="text-sky-400 text-[10px]">📄 {event.documents_count}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      {canEditEvent(event.created_by_id) && (
                        <button
                          onClick={(e) => { e.stopPropagation(); openDeleteModal(event.id, event.title); }}
                          className="shrink-0 px-2 py-1 rounded text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Модальное окно подтверждения удаления */}
      <Modal open={deleteModal.open} onClose={closeDeleteModal} className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <h3 className="text-lg font-semibold mb-2">Подтверждение удаления</h3>
        <p className="text-sm text-slate-300 mb-4">
          Вы уверены, что хотите удалить событие "{deleteModal.eventTitle}"? 
          Это действие нельзя отменить.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={closeDeleteModal}
            className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            Отмена
          </button>
          <button
            onClick={confirmDelete}
            className="px-4 py-2 rounded-lg text-sm bg-red-500 text-white hover:bg-red-600 transition-colors"
          >
            Удалить
          </button>
        </div>
      </Modal>

      {/* Индикатор загрузки события */}
      {loadingEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="text-white">Загрузка...</div>
        </div>
      )}

      {/* Модальное окно просмотра/редактирования события */}
      {viewEvent && !loadingEvent && (
        <Modal open onClose={closeViewEvent} closeOnEnter={false} className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-3xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            {!isEditingEvent ? (
              /* Режим просмотра */
              <>
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className={`inline-flex items-center px-3 py-1 rounded text-sm font-medium border ${getImportanceBg(viewEvent.importance)}`}>
                      Важность: {viewEvent.importance}
                    </span>
                    <h3 className="text-xl font-semibold">{viewEvent.title}</h3>
                  </div>
                  <button
                    onClick={() => { setViewEvent(null); setIsEditingEvent(false); }}
                    className="text-slate-400 hover:text-slate-200 text-2xl leading-none shrink-0"
                  >
                    ×
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500">Район:</span>
                      <p className="text-slate-200">{viewEvent.district_name || "—"}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Подразделение:</span>
                      <p className="text-slate-200">{viewEvent.department_name || "Не назначено"}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Дата создания:</span>
                      <p className="text-slate-200">{new Date(viewEvent.created_at).toLocaleString("ru-RU")}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Статус:</span>
                      <p className="text-slate-200">{STATUS_LABELS[viewEvent.status] || viewEvent.status}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Создал:</span>
                      <p className="text-slate-200">{viewEvent.created_by_name || "—"}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Слой:</span>
                      <p className="text-slate-200">{getLayerName(viewEvent.layer_id, viewEvent.sub_layer_id, viewEvent.sub_sub_layer_id)}</p>
                    </div>
                    {viewEvent.updated_at && (
                      <>
                        <div>
                          <span className="text-slate-500">Изменил:</span>
                          <p className="text-slate-200">{viewEvent.updated_by_name || "—"}</p>
                        </div>
                        <div>
                          <span className="text-slate-500">Дата изменения:</span>
                          <p className="text-slate-200">{new Date(viewEvent.updated_at).toLocaleString("ru-RU")}</p>
                        </div>
                      </>
                    )}
                  </div>
                  
                  {viewEvent.description && (
                    <div>
                      <span className="text-slate-500 text-sm">Описание:</span>
                      <p className="text-slate-200 mt-1 whitespace-pre-wrap bg-slate-800/50 rounded-lg p-3 text-sm">
                        {viewEvent.description}
                      </p>
                    </div>
                  )}
                  
                  {/* Изображения */}
                  {viewEvent.images && viewEvent.images.length > 0 && (
                    <div>
                      <span className="text-slate-500 text-sm">Изображения ({viewEvent.images.length}):</span>
                      <div className="mt-2 grid grid-cols-3 sm:grid-cols-4 gap-2">
                        {viewEvent.images.map(img => (
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
                  {viewEvent.documents && viewEvent.documents.length > 0 && (
                    <div>
                      <span className="text-slate-500 text-sm">Документы ({viewEvent.documents.length}):</span>
                      <div className="mt-2 space-y-1">
                        {viewEvent.documents.map(doc => (
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
                </div>
                
                <div className="mt-6 flex justify-end gap-3">
                  {canEditEvent(viewEvent.created_by_id) && (
                    <>
                      <button
                        onClick={() => {
                          const id = viewEvent.id;
                          const title = viewEvent.title;
                          setViewEvent(null);
                          setIsEditingEvent(false);
                          openDeleteModal(id, title);
                        }}
                        className="px-4 py-2 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                      >
                        Удалить
                      </button>
                      <button
                        onClick={startEditingEvent}
                        className="px-4 py-2 rounded-lg text-sm bg-sky-500 text-white hover:bg-sky-600 transition-colors"
                      >
                        Редактировать
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => { setViewEvent(null); setIsEditingEvent(false); }}
                    className="px-4 py-2 rounded-lg text-sm bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
                  >
                    Закрыть
                  </button>
                </div>
              </>
            ) : (
              /* Режим редактирования */
              <>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Редактирование события</h3>
                  <button
                    onClick={() => { setViewEvent(null); setIsEditingEvent(false); }}
                    className="text-slate-400 hover:text-slate-200 text-2xl leading-none"
                  >
                    ×
                  </button>
                </div>
                
                <div className="space-y-4">
                  {/* Название */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Название события</label>
                    <input
                      type="text"
                      value={editEventData.title}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    />
                  </div>
                  
                  {/* Важность */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Важность: {editEventData.importance}</label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={editEventData.importance}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, importance: parseInt(e.target.value) }))}
                      className="w-full"
                    />
                  </div>
                  
                  {/* Статус */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Статус</label>
                    <select
                      value={editEventData.status}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, status: e.target.value }))}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    >
                      <option value="ok">В норме</option>
                      <option value="warning">Внимание</option>
                      <option value="alert">Тревога</option>
                    </select>
                  </div>
                  
                  {/* Район */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Район</label>
                    <select
                      value={editEventData.districtName}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, districtName: e.target.value }))}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    >
                      <option value="">Выберите район</option>
                      {allDistricts.map((d) => (
                        <option key={d.name} value={d.name}>{d.name}</option>
                      ))}
                    </select>
                    {editEventData.districtName && (
                      <p className="mt-1 text-xs text-slate-400">
                        Подразделение: {zones.find(z => (z.district_names || []).includes(editEventData.districtName))?.department_name || "Не назначено"}
                      </p>
                    )}
                  </div>
                  
                  {/* Слой */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Слой</label>
                    <select
                      value={editEventData.layerValue}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, layerValue: e.target.value }))}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    >
                      <option value="">Не указан</option>
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
                  
                  {/* Описание */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Описание</label>
                    <textarea
                      value={editEventData.description}
                      onChange={(e) => setEditEventData(prev => ({ ...prev, description: e.target.value }))}
                      rows={4}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 resize-none"
                      placeholder="Введите описание события"
                    />
                  </div>
                  
                  {/* Информация (только для чтения) */}
                  <div className="grid grid-cols-2 gap-4 text-sm p-3 bg-slate-800/50 rounded-lg">
                    <div>
                      <span className="text-slate-500">Создал:</span>
                      <p className="text-slate-300">{viewEvent.created_by_name || "—"}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">Дата создания:</span>
                      <p className="text-slate-300">{new Date(viewEvent.created_at).toLocaleString("ru-RU")}</p>
                    </div>
                    {viewEvent.updated_at && (
                      <>
                        <div>
                          <span className="text-slate-500">Изменил:</span>
                          <p className="text-slate-300">{viewEvent.updated_by_name || "—"}</p>
                        </div>
                        <div>
                          <span className="text-slate-500">Дата изменения:</span>
                          <p className="text-slate-300">{new Date(viewEvent.updated_at).toLocaleString("ru-RU")}</p>
                        </div>
                      </>
                    )}
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-slate-700">
                  <button
                    onClick={cancelEditingEvent}
                    className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={saveEventChanges}
                    disabled={savingEvent || !editEventData.title.trim()}
                    className="px-4 py-2 rounded-lg text-sm bg-sky-500 text-white hover:bg-sky-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {savingEvent ? 'Сохранение...' : 'Сохранить'}
                  </button>
                </div>
              </>
            )}
        </Modal>
      )}

      {/* Модальное окно успешного удаления */}
      <Modal open={deleteSuccessModal.open} onClose={closeDeleteSuccessModal} className="relative bg-slate-900 border border-green-500/50 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
            <span className="text-green-400 text-xl">✓</span>
          </div>
          <h3 className="text-lg font-semibold text-white">Успешно</h3>
        </div>
        <p className="text-slate-300 text-sm mb-6">Событие "{deleteSuccessModal.eventTitle}" успешно удалено</p>
        <div className="flex justify-end">
          <button
            onClick={closeDeleteSuccessModal}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-green-500 text-white hover:bg-green-600 transition"
          >
            OK
          </button>
        </div>
      </Modal>

      {/* Модальное окно успешного создания */}
      <Modal open={createSuccessModal.open} onClose={closeCreateSuccessModal} className="relative bg-slate-900 border border-green-500/50 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
            <span className="text-green-400 text-xl">✓</span>
          </div>
          <h3 className="text-lg font-semibold text-white">Успешно</h3>
        </div>
        <p className="text-slate-300 text-sm mb-6">Событие "{createSuccessModal.eventTitle}" успешно создано</p>
        <div className="flex justify-end">
          <button
            onClick={closeCreateSuccessModal}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-green-500 text-white hover:bg-green-600 transition"
          >
            OK
          </button>
        </div>
      </Modal>
    </div>
  );
}
