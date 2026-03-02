import React, { useEffect, useState, useMemo } from "react";
import { requireEditor, handleAuthError, logout, isAdmin } from "../utils/auth";
import { fetchSystemSettings } from "../api/admin";
import { getAdministrativeZones, type AdministrativeZone } from "../api/administrative-zones";
import { getEvents, getEvent, type EventListItem, type EventDetail } from "../api/events";
import { getLayers, type Layer } from "../api/layers";
import * as XLSX from "xlsx";
import { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, BorderStyle } from "docx";
import { saveAs } from "file-saver";

type District = {
  name: string;
};

export function ReportsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noRegion, setNoRegion] = useState(false);
  
  // Данные
  const [allDistricts, setAllDistricts] = useState<District[]>([]);
  const [zones, setZones] = useState<AdministrativeZone[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [layers, setLayers] = useState<Layer[]>([]);
  
  // Фильтры
  const [filterDistrict, setFilterDistrict] = useState<string>("");
  const [filterLayer, setFilterLayer] = useState<string>("");
  const [filterImportanceMin, setFilterImportanceMin] = useState<number>(1);
  const [filterImportanceMax, setFilterImportanceMax] = useState<number>(10);
  const [filterDateFrom, setFilterDateFrom] = useState<string>("");
  const [filterDateTo, setFilterDateTo] = useState<string>("");
  const [filterArchived, setFilterArchived] = useState<string>("all");
  
  // Экспорт
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingWord, setExportingWord] = useState<number | null>(null);

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
    if (!requireEditor()) return;
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      const settings = await fetchSystemSettings();
      if (!settings || !settings.region_ids || settings.region_ids.length === 0) {
        setLoading(false);
        setNoRegion(true);
        return;
      }

      // Загружаем районы из ВСЕХ выбранных регионов
      await loadDistrictsFromAllRegions(settings.region_ids);
      
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

  // Фильтрованные события
  const filteredEvents = useMemo(() => {
    return events.filter(ev => {
      // Фильтр по району
      if (filterDistrict && ev.district_name !== filterDistrict) return false;
      
      // Фильтр по слою
      if (filterLayer) {
        const [type, id] = filterLayer.split("_");
        const layerId = parseInt(id);
        if (type === "layer" && ev.layer_id !== layerId) return false;
        if (type === "sub" && ev.sub_layer_id !== layerId) return false;
        if (type === "subsub" && ev.sub_sub_layer_id !== layerId) return false;
      }
      
      // Фильтр по важности
      if (ev.importance < filterImportanceMin || ev.importance > filterImportanceMax) return false;
      
      // Фильтр по дате
      if (filterDateFrom) {
        const eventDate = new Date(ev.created_at);
        const fromDate = new Date(filterDateFrom);
        if (eventDate < fromDate) return false;
      }
      if (filterDateTo) {
        const eventDate = new Date(ev.created_at);
        const toDate = new Date(filterDateTo);
        toDate.setHours(23, 59, 59, 999);
        if (eventDate > toDate) return false;
      }
      
      // Фильтр по архивности
      if (filterArchived === "active" && ev.is_archived) return false;
      if (filterArchived === "archived" && !ev.is_archived) return false;
      
      return true;
    });
  }, [events, filterDistrict, filterLayer, filterImportanceMin, filterImportanceMax, filterDateFrom, filterDateTo, filterArchived]);

  // Экспорт в Excel
  const exportToExcel = async () => {
    setExportingExcel(true);
    try {
      const data = filteredEvents.map(ev => ({
        "ID": ev.id,
        "Название": ev.title,
        "Район": ev.district_name || "",
        "Важность": ev.importance,
        "Статус": STATUS_LABELS[ev.status] || ev.status,
        "Слой": getLayerName(ev.layer_id, ev.sub_layer_id, ev.sub_sub_layer_id),
        "Дата создания": new Date(ev.created_at).toLocaleString("ru-RU"),
        "Создал": ev.created_by_name || "",
        "Актуальность": ev.is_archived ? "Не актуально" : "Актуально",
      }));

      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "События");
      
      // Устанавливаем ширину колонок
      ws["!cols"] = [
        { wch: 5 },  // ID
        { wch: 40 }, // Название
        { wch: 25 }, // Район
        { wch: 10 }, // Важность
        { wch: 12 }, // Статус
        { wch: 30 }, // Слой
        { wch: 20 }, // Дата создания
        { wch: 20 }, // Создал
        { wch: 15 }, // Актуальность
      ];
      
      const fileName = `события_${new Date().toISOString().split('T')[0]}.xlsx`;
      XLSX.writeFile(wb, fileName);
    } catch (e) {
      console.error("Ошибка экспорта:", e);
    } finally {
      setExportingExcel(false);
    }
  };

  // Экспорт в Word
  const exportToWord = async (eventId: number) => {
    setExportingWord(eventId);
    try {
      const event = await getEvent(eventId);
      
      const doc = new Document({
        sections: [{
          properties: {},
          children: [
            new Paragraph({
              text: event.title,
              heading: HeadingLevel.HEADING_1,
              spacing: { after: 300 },
            }),
            
            // Таблица с информацией
            new Table({
              width: { size: 100, type: WidthType.PERCENTAGE },
              rows: [
                createTableRow("Район", event.district_name || "—"),
                createTableRow("Подразделение", event.department_name || "Не назначено"),
                createTableRow("Важность", String(event.importance)),
                createTableRow("Статус", STATUS_LABELS[event.status] || event.status),
                createTableRow("Слой", getLayerName(event.layer_id, event.sub_layer_id, event.sub_sub_layer_id)),
                createTableRow("Дата создания", new Date(event.created_at).toLocaleString("ru-RU")),
                createTableRow("Создал", event.created_by_name || "—"),
                ...(event.updated_at ? [
                  createTableRow("Дата изменения", new Date(event.updated_at).toLocaleString("ru-RU")),
                  createTableRow("Изменил", event.updated_by_name || "—"),
                ] : []),
                createTableRow("Актуальность", event.is_archived ? "Не актуально" : "Актуально"),
              ],
            }),
            
            new Paragraph({ text: "", spacing: { after: 200 } }),
            
            // Описание
            ...(event.description ? [
              new Paragraph({
                text: "Описание",
                heading: HeadingLevel.HEADING_2,
                spacing: { after: 100 },
              }),
              new Paragraph({
                text: event.description,
                spacing: { after: 200 },
              }),
            ] : []),
            
            // Комментарии
            ...(event.comments && event.comments.length > 0 ? [
              new Paragraph({
                text: `Комментарии (${event.comments.length})`,
                heading: HeadingLevel.HEADING_2,
                spacing: { after: 100 },
              }),
              ...event.comments.map(c => new Paragraph({
                children: [
                  new TextRun({ text: `${c.user_name || "Аноним"} (${new Date(c.created_at).toLocaleString("ru-RU")}): `, bold: true }),
                  new TextRun({ text: c.text }),
                ],
                spacing: { after: 100 },
              })),
            ] : []),
            
            // Файлы
            ...(event.images && event.images.length > 0 ? [
              new Paragraph({
                text: `Изображения: ${event.images.length} шт.`,
                spacing: { before: 200 },
              }),
            ] : []),
            ...(event.documents && event.documents.length > 0 ? [
              new Paragraph({
                text: `Документы: ${event.documents.map(d => d.name).join(", ")}`,
                spacing: { before: 100 },
              }),
            ] : []),
          ],
        }],
      });

      const blob = await Packer.toBlob(doc);
      const fileName = `событие_${event.id}_${event.title.substring(0, 30).replace(/[^a-zA-Zа-яА-Я0-9]/g, '_')}.docx`;
      saveAs(blob, fileName);
    } catch (e) {
      console.error("Ошибка экспорта:", e);
    } finally {
      setExportingWord(null);
    }
  };

  // Вспомогательная функция для создания строки таблицы
  const createTableRow = (label: string, value: string) => {
    return new TableRow({
      children: [
        new TableCell({
          width: { size: 30, type: WidthType.PERCENTAGE },
          children: [new Paragraph({ 
            children: [new TextRun({ text: label, bold: true })],
          })],
          borders: {
            top: { style: BorderStyle.SINGLE, size: 1 },
            bottom: { style: BorderStyle.SINGLE, size: 1 },
            left: { style: BorderStyle.SINGLE, size: 1 },
            right: { style: BorderStyle.SINGLE, size: 1 },
          },
        }),
        new TableCell({
          width: { size: 70, type: WidthType.PERCENTAGE },
          children: [new Paragraph({ text: value })],
          borders: {
            top: { style: BorderStyle.SINGLE, size: 1 },
            bottom: { style: BorderStyle.SINGLE, size: 1 },
            left: { style: BorderStyle.SINGLE, size: 1 },
            right: { style: BorderStyle.SINGLE, size: 1 },
          },
        }),
      ],
    });
  };

  // Сбросить фильтры
  const resetFilters = () => {
    setFilterDistrict("");
    setFilterLayer("");
    setFilterImportanceMin(1);
    setFilterImportanceMax(10);
    setFilterDateFrom("");
    setFilterDateTo("");
    setFilterArchived("all");
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
            {/* Группа 2: Слои, События, Отчёты */}
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
                className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
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
        <h1 className="text-2xl font-semibold tracking-tight mb-3">Отчёты</h1>
      </div>

      {loading ? (
        <div className="max-w-7xl mx-auto py-10 text-center text-slate-300">Загрузка...</div>
      ) : noRegion ? (
        <div className="max-w-7xl mx-auto py-16 text-center">
          <div className="rounded-2xl border border-sky-700/50 bg-sky-950/40 px-6 py-8 max-w-md mx-auto">
            <p className="text-slate-200 text-lg font-medium mb-2">Регион не выбран</p>
            <p className="text-slate-400 text-sm mb-4">Для работы с отчётами необходимо выбрать регион мониторинга в настройках системы.</p>
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
        <div className="max-w-7xl mx-auto">
          {/* Фильтры */}
          <div className="rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold">Фильтры</h2>
              <button
                onClick={resetFilters}
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                Сбросить
              </button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              {/* Район */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Район</label>
                <select
                  value={filterDistrict}
                  onChange={(e) => setFilterDistrict(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  <option value="">Все районы</option>
                  {allDistricts.map(d => (
                    <option key={d.name} value={d.name}>{d.name}</option>
                  ))}
                </select>
              </div>
              
              {/* Слой */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Слой</label>
                <select
                  value={filterLayer}
                  onChange={(e) => setFilterLayer(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  <option value="">Все слои</option>
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
              
              {/* Важность мин */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Важность от</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={filterImportanceMin}
                  onChange={(e) => setFilterImportanceMin(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                />
              </div>
              
              {/* Важность макс */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Важность до</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={filterImportanceMax}
                  onChange={(e) => setFilterImportanceMax(Math.max(1, Math.min(10, parseInt(e.target.value) || 10)))}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                />
              </div>
              
              {/* Дата от */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Дата от</label>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                />
              </div>
              
              {/* Дата до */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Дата до</label>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                />
              </div>
              
              {/* Актуальность */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Актуальность</label>
                <select
                  value={filterArchived}
                  onChange={(e) => setFilterArchived(e.target.value)}
                  className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-2 py-1.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  <option value="all">Все</option>
                  <option value="active">Актуальные</option>
                  <option value="archived">Не актуальные</option>
                </select>
              </div>
            </div>
          </div>

          {/* Результаты и экспорт */}
          <div className="rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold">
                События ({filteredEvents.length} из {events.length})
              </h2>
              <button
                onClick={exportToExcel}
                disabled={exportingExcel || filteredEvents.length === 0}
                className="px-4 py-1.5 rounded-lg text-sm bg-green-600 text-white hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {exportingExcel ? (
                  <>Экспорт...</>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Выгрузить в Excel
                  </>
                )}
              </button>
            </div>
            
            {filteredEvents.length === 0 ? (
              <div className="text-center py-10 text-slate-400">
                <p>Нет событий по заданным фильтрам</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-400 border-b border-slate-700">
                      <th className="pb-2 pr-3">Важн.</th>
                      <th className="pb-2 pr-3">Название</th>
                      <th className="pb-2 pr-3">Район</th>
                      <th className="pb-2 pr-3">Слой</th>
                      <th className="pb-2 pr-3">Дата</th>
                      <th className="pb-2 pr-3">Статус</th>
                      <th className="pb-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEvents.map(ev => (
                      <tr key={ev.id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                        <td className="py-2 pr-3">
                          <span className={`inline-flex items-center justify-center w-7 h-7 rounded text-xs font-medium border ${getImportanceBg(ev.importance)}`}>
                            {ev.importance}
                          </span>
                        </td>
                        <td className="py-2 pr-3">
                          <div className="flex items-center gap-2">
                            <span className={ev.is_archived ? "text-slate-500" : "text-white"}>{ev.title}</span>
                            {ev.is_archived && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">не актуально</span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 pr-3 text-slate-400">{ev.district_name || "—"}</td>
                        <td className="py-2 pr-3 text-slate-400 text-xs">{getLayerName(ev.layer_id, ev.sub_layer_id, ev.sub_sub_layer_id)}</td>
                        <td className="py-2 pr-3 text-slate-400 text-xs whitespace-nowrap">
                          {new Date(ev.created_at).toLocaleDateString("ru-RU")}
                        </td>
                        <td className="py-2 pr-3 text-slate-400 text-xs">{STATUS_LABELS[ev.status] || ev.status}</td>
                        <td className="py-2">
                          <button
                            onClick={() => exportToWord(ev.id)}
                            disabled={exportingWord === ev.id}
                            className="px-2 py-1 rounded text-xs bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                            title="Выгрузить в Word"
                          >
                            {exportingWord === ev.id ? "..." : "Word"}
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
      )}
    </div>
  );
}
