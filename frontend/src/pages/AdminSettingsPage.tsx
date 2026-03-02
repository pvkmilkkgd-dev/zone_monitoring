import { useEffect, useMemo, useRef, useState } from "react";
import { fetchSystemSettings, updateSystemSettings } from "../api/admin";
import { RussiaRegionsMapSvg } from "../components/RussiaRegionsMapSvg";
import { requireAdmin, handleAuthError, logout } from "../utils/auth";
import { Modal } from "../components/Modal";

type Region = { id: string; name: string };

function normRegionName(s: string) {
  return (s || "")
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[—–]/g, "-")
    .replace(/\s*-\s*/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

export function AdminSettingsPage() {
  const [selectedRegionIds, setSelectedRegionIds] = useState<string[]>([]);
  const [savedRegionIds, setSavedRegionIds] = useState<string[]>([]); // region_ids из БД для сравнения
  const [departmentName, setDepartmentName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionsLoading, setRegionsLoading] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [showDeactivateWarning, setShowDeactivateWarning] = useState(false);
  const [mapKey, setMapKey] = useState(0); // Ключ для принудительного обновления карты
  const deptRef = useRef<HTMLTextAreaElement>(null);

  // Автоматическое изменение высоты textarea
  useEffect(() => {
    const textarea = deptRef.current;
    if (textarea) {
      // Вычисляем высоту одной строки с учетом padding
      const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);
      const paddingTop = parseFloat(getComputedStyle(textarea).paddingTop);
      const paddingBottom = parseFloat(getComputedStyle(textarea).paddingBottom);
      const singleLineHeight = lineHeight + paddingTop + paddingBottom;
      
      // Сбрасываем высоту, чтобы получить правильный scrollHeight
      textarea.style.height = "auto";
      // Получаем необходимую высоту
      const scrollHeight = textarea.scrollHeight;
      
      // Устанавливаем высоту только если нужна вторая строка (больше одной строки)
      // Если scrollHeight больше или равен высоте одной строки + небольшой запас, используем scrollHeight
      // Иначе оставляем высоту одной строки
      if (scrollHeight > singleLineHeight) {
        textarea.style.height = `${scrollHeight}px`;
      } else {
        textarea.style.height = `${singleLineHeight}px`;
      }
    }
  }, [departmentName]);

  useEffect(() => {
    if (!requireAdmin()) return;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await fetchSystemSettings();
        if (data) {
          setDepartmentName(data.department_name || "");
          const ids = Array.isArray(data.region_ids) ? data.region_ids.map(String) : [];
          setSelectedRegionIds(ids);
          setSavedRegionIds(ids);
        }

        setRegionsLoading(true);
        const res = await fetch("/api/regions");
        if (!res.ok) throw new Error(`Не удалось загрузить регионы: HTTP ${res.status}`);
        const list = (await res.json()) as Region[];
        setRegions(list);
      } catch (e: any) {
        console.error(e);
        if (handleAuthError(e)) return;
        setError(e.message || "Ошибка загрузки настроек");
      } finally {
        setRegionsLoading(false);
        setLoading(false);
      }
    };

    load();
  }, []);

  const regionIdToName = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of regions) m.set(String(r.id), r.name);
    return m;
  }, [regions]);

  const regionNameToId = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of regions) {
      const base = normRegionName(r.name);
      m.set(r.name, r.id);
      m.set(base, r.id);
    }
    return m;
  }, [regions]);

  const selectedRegions = useMemo(() => {
    return selectedRegionIds.map((id) => ({
      id,
      name: regionIdToName.get(id) ?? id,
    }));
  }, [selectedRegionIds, regionIdToName]);

  const toggleRegionId = (id: string) => {
    setSelectedRegionIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const uploadRegion = async (file: File) => {
    const token = localStorage.getItem("zone_jwt") || localStorage.getItem("access_token") || localStorage.getItem("accessToken");
    const fd = new FormData();
    fd.append("file", file);

    const resp = await fetch("/api/v1/admin/regions/import", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(text || `Upload failed: ${resp.status}`);
    }
    return resp.json();
  };

  const doSave = async (deactivateRemoved: boolean) => {
    try {
      setSaving(true);
      setError(null);

      const cleanedName = departmentName.trim();
      await updateSystemSettings({
        department_name: cleanedName.length ? cleanedName : null,
        region_ids: selectedRegionIds,
        deactivate_removed: deactivateRemoved,
      });
      setDepartmentName(cleanedName);
      setSavedRegionIds([...selectedRegionIds]); // обновляем сохранённые ID

      setNotification({ type: "success", message: "Настройки успешно сохранены" });
      setTimeout(() => setNotification(null), 3000);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка при сохранении настроек");
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    // Проверяем, есть ли удалённые регионы
    const removedIds = savedRegionIds.filter((id) => !selectedRegionIds.includes(id));
    if (removedIds.length > 0) {
      // Показываем предупреждение
      setShowDeactivateWarning(true);
      return;
    }
    // Нет удалённых регионов — сохраняем напрямую
    await doSave(false);
  };

  const handleConfirmDeactivate = async () => {
    setShowDeactivateWarning(false);
    await doSave(true);
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
                className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
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
        <h1 className="text-2xl font-semibold tracking-tight mb-3">Настройки системы</h1>
      </div>

      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-6">
        {/* Левая панель */}
        <div className="relative overflow-hidden rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur lg:flex-1 min-w-0">
          <div className="pointer-events-none absolute inset-0 opacity-20">
            <div className="absolute -right-32 -top-32 h-64 w-64 rounded-full bg-sky-500/40 blur-3xl" />
            <div className="absolute -left-24 bottom-0 h-72 w-72 rounded-full bg-blue-400/30 blur-3xl" />
            <div className="absolute inset-8 border border-sky-400/10 rounded-3xl [mask-image:radial-gradient(circle_at_top,_black,_transparent)]" />
          </div>

          <div className="relative space-y-6">
            {error && (
              <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                {error}
              </div>
            )}

            {loading ? (
              <div className="py-10 text-sm text-slate-300">Загрузка настроек…</div>
            ) : (
              <>
                <div className="space-y-5">
                  {/* Название управления */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-slate-100">Название управления</label>

                    <div
                      className="relative rounded-2xl border border-slate-700/70 bg-slate-900/80 cursor-text flex items-center"
                      onClick={() => deptRef.current?.focus()}
                    >
                      {departmentName.length === 0 && (
                        <div className="pointer-events-none absolute inset-0 px-3 py-2 text-xs text-slate-500 flex items-center">
                          Например: Управление по N-ской области
                        </div>
                      )}

                      <textarea
                        ref={deptRef}
                        value={departmentName}
                        onChange={(e) => setDepartmentName(e.target.value)}
                        rows={1}
                        onBlur={() => setDepartmentName((v) => v.trim())}
                        className="w-full bg-transparent px-3 py-2 text-sm text-slate-50 focus:outline-none resize-none overflow-hidden leading-normal"
                        style={{ height: "auto", minHeight: "2.5rem" }}
                      />
                    </div>

                    <p className="text-xs text-slate-400">
                      Это название будет отображаться в шапке сервиса и в формируемых документах.
                    </p>
                  </div>

                  {/* Выбранные регионы */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <label className="block text-sm font-medium text-slate-100">Регионы мониторинга</label>
                      {selectedRegionIds.length > 0 && (
                        <span className="text-xs text-slate-400">Выбрано: {selectedRegionIds.length}</span>
                      )}
                    </div>

                    <div className="min-h-[40px] rounded-2xl border border-slate-700/70 bg-slate-900/80 px-3 py-2">
                      {selectedRegionIds.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          Регионы ещё не выбраны. Отметьте один или несколько регионов в списке ниже.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {selectedRegions.map(({ id, name }) => (
                            <span
                              key={id}
                              className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 border border-sky-500/40 px-3 py-1 text-xs text-sky-100"
                            >
                              <span>{name}</span>
                              <button
                                type="button"
                                onClick={() => toggleRegionId(id)}
                                className="ml-1 text-sky-200/80 hover:text-sky-50 text-[10px] leading-none"
                              >
                                ✕
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Список регионов */}
                    <div className="rounded-2xl border border-slate-700 bg-slate-900/90">
                      <div className="max-h-[360px] min-h-[300px] overflow-y-auto divide-y divide-slate-800">
                        {regionsLoading ? (
                          <div className="px-3 py-3 text-sm text-slate-300">Загрузка списка регионов…</div>
                        ) : (
                          regions.map((r) => {
                            const active = selectedRegionIds.includes(r.id);
                            return (
                              <button
                                key={r.id}
                                type="button"
                                onClick={() => toggleRegionId(r.id)}
                                className={
                                  "w-full flex items-center justify-between px-3 py-2.5 text-left text-xs sm:text-sm transition " +
                                  (active ? "bg-sky-500/15 text-sky-100" : "text-slate-200 hover:bg-slate-800/80")
                                }
                              >
                                <span>{r.name}</span>
                                {active && <span className="ml-3 h-2.5 w-2.5 rounded-full bg-sky-400" />}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400">
                      Выбранные регионы используются в отчётах, фильтрах и в шапке панели мониторинга.
                    </p>

                    <div className="pt-1">
                      <label className="block text-xs text-slate-400 mb-1">Загрузить регион (GeoJSON)</label>
                      <input
                        type="file"
                        accept=".geojson,.json"
                        className="text-xs text-slate-300 file:mr-3 file:rounded-lg file:border file:border-slate-600 file:bg-slate-800 file:px-3 file:py-1.5 file:text-slate-100 file:cursor-pointer"
                        onChange={async (e) => {
                          const f = e.target.files?.[0];
                          if (!f) return;
                          try {
                            await uploadRegion(f);
                            const res = await fetch("/api/regions");
                            if (res.ok) {
                              const list = (await res.json()) as Region[];
                              setRegions(list);
                            }
                            setNotification({ type: "success", message: "Регион успешно загружен. Карта обновлена." });
                            setMapKey((prev) => prev + 1); // Принудительно обновляем карту
                            setTimeout(() => setNotification(null), 3000);
                          } catch (err: any) {
                            setNotification({ type: "error", message: err?.message || "Ошибка загрузки региона" });
                            setTimeout(() => setNotification(null), 5000);
                          } finally {
                            e.currentTarget.value = "";
                          }
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 pt-2">
                  <div className="text-xs text-slate-400">Изменения можно будет скорректировать в любой момент.</div>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={saving}
                    className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60"
                  >
                    {saving ? "Сохранение…" : "Сохранить настройки"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Правая колонка с описанием */}
        <div className="space-y-4 w-full lg:w-[720px] shrink-0 min-w-0">
          <div className="rounded-3xl bg-slate-900/80 border border-slate-700/60 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
            <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">Панель администратора</h2>
            <p className="text-sm text-slate-200 mb-3">
              Здесь администратор настраивает базовые параметры системы перед началом работы операторов.
            </p>
            <ul className="space-y-2 text-sm text-slate-300">
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />
                <span>Оперативный контроль состояния обстановки.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />
                <span>История событий и журнал инцидентов.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />
                <span>Быстрая оценка обстановки по ключевым метрикам.</span>
              </li>
            </ul>
          </div>

          <div className="rounded-3xl bg-sky-950/60 border border-sky-800/70 p-5 text-sm text-slate-100 shadow-lg shadow-sky-900/50">
            <p className="font-medium mb-2">Доступ только для администратора системы.</p>
            <p className="text-slate-300 text-xs leading-relaxed">
              После первичной настройки администратора остальные сотрудники будут заходить только через стандартную
              страницу авторизации и работать с панелью мониторинга в своих ролях.
            </p>
          </div>

          <div className="rounded-3xl bg-slate-900/80 border border-slate-700/60 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide">Карта регионов РФ</h2>
                <p className="text-xs text-slate-400 mt-1">Клик по региону добавляет/убирает его в выбранные.</p>
              </div>
              <span className="shrink-0 rounded-full border border-sky-700/60 bg-sky-950/60 px-3 py-1 text-[11px] text-sky-200">
                РОССИЯ
              </span>
            </div>

            <div className="rounded-2xl bg-slate-950/70 overflow-hidden">
              <div className="bg-slate-900/70 px-3 py-2 text-[11px] uppercase tracking-wide text-slate-400">
                Выбрано: {selectedRegionIds.length}
              </div>
              <div className="w-full h-[360px]">
                <RussiaRegionsMapSvg
                  key={mapKey}
                  selectedRegionIds={selectedRegionIds}
                  padding={10}
                  resolveRegionId={(name) => regionNameToId.get(normRegionName(name))}
                  onRegionClick={(regionId) => toggleRegionId(regionId)}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Модальное окно предупреждения о деактивации */}
      <Modal open={showDeactivateWarning} onClose={() => setShowDeactivateWarning(false)} closeOnEnter={false}>
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-500/20 border border-amber-400/30 flex items-center justify-center">
            <svg className="w-6 h-6 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div className="flex-1 pt-1">
            <h3 className="text-lg font-semibold mb-2 text-amber-300">Внимание</h3>
            <p className="text-slate-200 text-sm leading-relaxed">
              При удалении региона из списка все связанные события и подразделения будут деактивированы.
              Восстановить их будет невозможно — при повторном выборе этого региона данные будут создаваться заново.
            </p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => setShowDeactivateWarning(false)}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-700/60 text-slate-300 hover:bg-slate-700 border border-slate-600/50 transition-colors"
          >
            Отмена
          </button>
          <button
            onClick={handleConfirmDeactivate}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 transition-colors"
          >
            Подтвердить
          </button>
        </div>
      </Modal>

      {/* Модальное окно уведомлений */}
      <Modal open={!!notification} onClose={() => setNotification(null)} className="relative rounded-3xl bg-slate-900/95 border border-slate-700/60 shadow-2xl shadow-sky-900/40 max-w-md w-full p-6 backdrop-blur">
            <button
              onClick={() => setNotification(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors"
              aria-label="Закрыть"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div className="flex items-start gap-4">
              {notification?.type === "success" ? (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-sky-500/20 border border-sky-400/30 flex items-center justify-center">
                  <svg className="w-6 h-6 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-500/20 border border-red-400/30 flex items-center justify-center">
                  <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              )}
              <div className="flex-1 pt-1">
                <h3 className={`text-lg font-semibold mb-2 ${
                  notification?.type === "success" ? "text-sky-300" : "text-red-300"
                }`}>
                  {notification?.type === "success" ? "Успешно" : "Ошибка"}
                </h3>
                <p className="text-slate-200 text-sm leading-relaxed">
                  {notification?.message}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setNotification(null)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  notification?.type === "success"
                    ? "bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/30"
                    : "bg-red-500/20 text-red-300 hover:bg-red-500/30 border border-red-500/30"
                }`}
              >
                Закрыть
              </button>
            </div>
      </Modal>
    </div>
  );
}
