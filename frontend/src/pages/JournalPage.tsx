import { useEffect, useState, useCallback } from "react";
import { getAuditLogs, getAuditActions, getAuditEntityTypes, exportAuditLogs, type AuditLogItem } from "../api/audit";
import { fetchUsers, type UserDto } from "../api/admin";
import { requireAdmin, handleAuthError, logout, isAdmin } from "../utils/auth";
import { useEscapeKey } from "../hooks/useEscapeKey";

// Русские названия действий
const ACTION_LABELS: Record<string, string> = {
  CREATE: "Создание",
  UPDATE: "Обновление",
  DELETE: "Удаление",
  LOGIN: "Вход",
  LOGOUT: "Выход",
};

// Русские названия сущностей
const ENTITY_LABELS: Record<string, string> = {
  event: "Событие",
  layer: "Слой",
  sub_layer: "Вложенный слой",
  sub_sub_layer: "Под-вложенный слой",
  user: "Пользователь",
  zone: "Подразделение",
  comment: "Комментарий",
  district_description: "Описание района",
  settings: "Настройки",
};

// Цвета для действий
const ACTION_COLORS: Record<string, string> = {
  CREATE: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  UPDATE: "bg-sky-500/20 text-sky-400 border-sky-500/50",
  DELETE: "bg-red-500/20 text-red-400 border-red-500/50",
  LOGIN: "bg-violet-500/20 text-violet-400 border-violet-500/50",
  LOGOUT: "bg-slate-500/20 text-slate-400 border-slate-500/50",
};

export function JournalPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Фильтры
  const [actions, setActions] = useState<string[]>([]);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [users, setUsers] = useState<UserDto[]>([]);
  
  const [filterAction, setFilterAction] = useState<string>("");
  const [filterEntityType, setFilterEntityType] = useState<string>("");
  const [filterUserId, setFilterUserId] = useState<string>("");
  const [filterDateFrom, setFilterDateFrom] = useState<string>("");
  const [filterDateTo, setFilterDateTo] = useState<string>("");
  const [filterSearch, setFilterSearch] = useState<string>("");
  
  // Пагинация
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 50;
  
  // Экспорт
  const [exporting, setExporting] = useState(false);
  
  // Детали записи
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  // Закрытие модального окна по Escape
  const closeLogModal = useCallback(() => setSelectedLog(null), []);
  useEscapeKey(selectedLog !== null, closeLogModal);

  useEffect(() => {
    if (!requireAdmin()) return;
    loadFilters();
    loadLogs(true);
  }, []);

  const loadFilters = async () => {
    try {
      const [actionsData, entityTypesData, usersData] = await Promise.all([
        getAuditActions(),
        getAuditEntityTypes(),
        fetchUsers(),
      ]);
      setActions(actionsData);
      setEntityTypes(entityTypesData);
      setUsers(usersData);
    } catch (e) {
      console.error("Ошибка загрузки фильтров:", e);
    }
  };

  const loadLogs = async (reset = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const currentOffset = reset ? 0 : offset;
      
      const params: Record<string, unknown> = {
        limit: LIMIT,
        offset: currentOffset,
      };
      
      if (filterAction) params.action = filterAction;
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterUserId) params.user_id = parseInt(filterUserId);
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;
      if (filterSearch) params.search = filterSearch;
      
      const data = await getAuditLogs(params);
      
      if (reset) {
        setLogs(data);
        setOffset(LIMIT);
      } else {
        setLogs(prev => [...prev, ...data]);
        setOffset(prev => prev + LIMIT);
      }
      
      setHasMore(data.length === LIMIT);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки журнала");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    setOffset(0);
    loadLogs(true);
  };

  const handleResetFilters = () => {
    setFilterAction("");
    setFilterEntityType("");
    setFilterUserId("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setFilterSearch("");
    setOffset(0);
    // После сброса загружаем без фильтров
    setTimeout(() => loadLogs(true), 0);
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      
      const params: Record<string, unknown> = {};
      if (filterAction) params.action = filterAction;
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterUserId) params.user_id = parseInt(filterUserId);
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;
      
      const blob = await exportAuditLogs(params);
      
      // Создаём ссылку для скачивания
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `journal_${new Date().toISOString().split("T")[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e: any) {
      console.error(e);
      setError("Ошибка экспорта журнала");
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
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
                  className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
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
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-semibold tracking-tight">Журнал операций</h1>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-2 rounded-lg text-sm bg-slate-700/50 text-slate-300 hover:bg-slate-700 border border-slate-600 transition-colors disabled:opacity-50"
          >
            {exporting ? "Экспорт..." : "Экспортировать"}
          </button>
        </div>

        {/* Фильтры */}
        <div className="mb-4 p-4 rounded-2xl bg-slate-800/30 border border-slate-700/50">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Действие */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Действие</label>
              <select
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              >
                <option value="">Все</option>
                {actions.map((action) => (
                  <option key={action} value={action}>
                    {ACTION_LABELS[action] || action}
                  </option>
                ))}
              </select>
            </div>

            {/* Тип сущности */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Тип сущности</label>
              <select
                value={filterEntityType}
                onChange={(e) => setFilterEntityType(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              >
                <option value="">Все</option>
                {entityTypes.map((type) => (
                  <option key={type} value={type}>
                    {ENTITY_LABELS[type] || type}
                  </option>
                ))}
              </select>
            </div>

            {/* Пользователь */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Пользователь</label>
              <select
                value={filterUserId}
                onChange={(e) => setFilterUserId(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              >
                <option value="">Все</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name || user.username}
                  </option>
                ))}
              </select>
            </div>

            {/* Дата от */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Дата от</label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              />
            </div>

            {/* Дата до */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Дата до</label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              />
            </div>

            {/* Поиск */}
            <div>
              <label className="block text-xs text-slate-400 mb-1">Поиск</label>
              <input
                type="text"
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                placeholder="Описание..."
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
              />
            </div>
          </div>

          {/* Кнопки фильтрации */}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleApplyFilters}
              className="px-4 py-2 rounded-lg text-sm bg-sky-500 text-white hover:bg-sky-600 transition-colors"
            >
              Применить
            </button>
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 rounded-lg text-sm bg-slate-700/50 text-slate-300 hover:bg-slate-700 border border-slate-600 transition-colors"
            >
              Сбросить
            </button>
          </div>
        </div>

        {/* Ошибка */}
        {error && (
          <div className="mb-4 rounded-2xl border border-red-500/60 bg-red-500/10 text-red-100 p-4">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Таблица журнала */}
        <div className="rounded-2xl bg-slate-800/30 border border-slate-700/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Дата/Время</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Действие</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Пользователь</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Сущность</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Описание</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {logs.map((log) => (
                  <tr 
                    key={log.id} 
                    className="hover:bg-slate-700/20 cursor-pointer transition-colors"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="px-4 py-3 text-sm text-slate-300 whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${ACTION_COLORS[log.action] || "bg-slate-500/20 text-slate-400 border-slate-500/50"}`}>
                        {ACTION_LABELS[log.action] || log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">
                      {log.user_name || "Система"}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">
                      {log.entity_type && (
                        <div>
                          <span className="text-slate-400">{ENTITY_LABELS[log.entity_type] || log.entity_type}</span>
                          {log.entity_name && (
                            <span className="text-slate-200 ml-1">"{log.entity_name}"</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400 max-w-xs truncate">
                      {log.description}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">
                      {log.ip_address || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Загрузка / Пустой список */}
          {loading && logs.length === 0 && (
            <div className="p-8 text-center text-slate-400">
              Загрузка...
            </div>
          )}
          {!loading && logs.length === 0 && (
            <div className="p-8 text-center text-slate-400">
              Записи не найдены
            </div>
          )}

          {/* Кнопка загрузить ещё */}
          {hasMore && logs.length > 0 && (
            <div className="p-4 text-center border-t border-slate-700/50">
              <button
                onClick={() => loadLogs(false)}
                disabled={loading}
                className="px-4 py-2 rounded-lg text-sm bg-slate-700/50 text-slate-300 hover:bg-slate-700 border border-slate-600 transition-colors disabled:opacity-50"
              >
                {loading ? "Загрузка..." : "Загрузить ещё"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Модальное окно с деталями записи */}
      {selectedLog && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={closeLogModal}
        >
          <div 
            className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-700 shadow-xl max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              {/* Заголовок */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Детали записи</h2>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-slate-400 hover:text-slate-200 transition-colors text-xl"
                >
                  ✕
                </button>
              </div>

              {/* Информация */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-500">Дата и время</span>
                    <p className="text-sm text-slate-200">{formatDate(selectedLog.created_at)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Действие</span>
                    <p>
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${ACTION_COLORS[selectedLog.action] || "bg-slate-500/20 text-slate-400 border-slate-500/50"}`}>
                        {ACTION_LABELS[selectedLog.action] || selectedLog.action}
                      </span>
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Пользователь</span>
                    <p className="text-sm text-slate-200">{selectedLog.user_name || "Система"}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">ID пользователя</span>
                    <p className="text-sm text-slate-200">{selectedLog.user_id || "-"}</p>
                  </div>
                </div>

                {selectedLog.entity_type && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-slate-500">Тип сущности</span>
                      <p className="text-sm text-slate-200">{ENTITY_LABELS[selectedLog.entity_type] || selectedLog.entity_type}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">ID сущности</span>
                      <p className="text-sm text-slate-200">{selectedLog.entity_id || "-"}</p>
                    </div>
                  </div>
                )}

                {selectedLog.entity_name && (
                  <div>
                    <span className="text-xs text-slate-500">Название сущности</span>
                    <p className="text-sm text-slate-200">{selectedLog.entity_name}</p>
                  </div>
                )}

                {selectedLog.description && (
                  <div>
                    <span className="text-xs text-slate-500">Описание</span>
                    <p className="text-sm text-slate-200">{selectedLog.description}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-500">IP адрес</span>
                    <p className="text-sm text-slate-200">{selectedLog.ip_address || "-"}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">User-Agent</span>
                    <p className="text-sm text-slate-400 text-xs break-all">{selectedLog.user_agent || "-"}</p>
                  </div>
                </div>

                {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                  <div>
                    <span className="text-xs text-slate-500">Дополнительные данные</span>
                    <pre className="mt-1 p-3 rounded-lg bg-slate-800 text-xs text-slate-300 overflow-x-auto">
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Кнопка закрыть */}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-2 rounded-lg text-sm bg-slate-700/50 text-slate-300 hover:bg-slate-700 border border-slate-600 transition-colors"
                >
                  Закрыть
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
