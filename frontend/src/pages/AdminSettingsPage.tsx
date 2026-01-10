import { useEffect, useMemo, useRef, useState } from "react";
import { fetchSystemSettings, updateSystemSettings } from "../api";
import { RussiaRegionsMapSvg } from "../components/RussiaRegionsMapSvg";

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
  const [departmentName, setDepartmentName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionsLoading, setRegionsLoading] = useState(false);
  const deptRef = useRef<HTMLTextAreaElement>(null);
  const [deptFocused, setDeptFocused] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await fetchSystemSettings();
        if (data) {
          setDepartmentName(data.department_name ?? "");
          setSelectedRegionIds(Array.isArray(data.region_ids) ? data.region_ids.map(String) : []);
        }

        setRegionsLoading(true);
        const res = await fetch("/api/regions");
        if (!res.ok) throw new Error(`Не удалось загрузить регионы: HTTP ${res.status}`);
        const list = (await res.json()) as Region[];
        setRegions(list);
      } catch (e: any) {
        console.error(e);
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
    for (const r of regions) m.set(r.name, String(r.id));
    return m;
  }, [regions]);

  const toggleRegionId = (id: string) => {
    setSelectedRegionIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectedRegionKeys = useMemo(() => {
    const names = selectedRegionIds
      .map((id) => regionIdToName.get(id))
      .filter(Boolean) as string[];
    return [...selectedRegionIds, ...names];
  }, [selectedRegionIds, regionIdToName]);

  const handleMapClick = (key: string) => {
    const uuidLike = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (uuidLike.test(key)) {
      toggleRegionId(key);
      return;
    }
    const id = regionNameToId.get(key);
    if (id) toggleRegionId(id);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      await updateSystemSettings({
        region_ids: selectedRegionIds,
        department_name: departmentName || null,
      });

      alert("Настройки сохранены");
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Ошибка при сохранении настроек");
    } finally {
      setSaving(false);
    }
  };

  return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white flex items-center justify-center px-4 py-8">
        <div className="max-w-7xl w-full flex flex-col lg:flex-row gap-6">
          {/* Левая панель */}
          <div className="relative overflow-hidden rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur lg:flex-1 min-w-0">
          <div className="pointer-events-none absolute inset-0 opacity-20">
            <div className="absolute -right-32 -top-32 h-64 w-64 rounded-full bg-sky-500/40 blur-3xl" />
            <div className="absolute -left-24 bottom-0 h-72 w-72 rounded-full bg-blue-400/30 blur-3xl" />
            <div className="absolute inset-8 border border-sky-400/10 rounded-3xl [mask-image:radial-gradient(circle_at_top,_black,_transparent)]" />
          </div>

          <div className="relative space-y-6">
            <div>
              <h1 className="text-2xl lg:text-3xl font-semibold tracking-tight">
                Настройки системы
              </h1>
              <p className="mt-2 text-sm text-slate-300/90 max-w-xl">
                Внутренний сервис мониторинга обстановки. Укажите название вашего управления и
                выберите один или несколько регионов, за которые отвечает система мониторинга.
              </p>
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                {error}
              </div>
            )}

            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1 text-sm w-fit">
              <button
                type="button"
                className="px-4 py-1.5 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
              >
                Регион и управление
              </button>
              <button type="button" className="px-4 py-1.5 rounded-full text-slate-400" disabled>
                Пользователи
              </button>
              <button type="button" className="px-4 py-1.5 rounded-full text-slate-400" disabled>
                Зоны и устройства
              </button>
            </div>

            {loading ? (
              <div className="py-10 text-sm text-slate-300">Загрузка настроек…</div>
            ) : (
              <>
                <div className="space-y-5">
                  {/* Название управления */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-slate-100">
                      Название управления
                    </label>

                    {/* Контейнер 1-в-1 как у "Регионы ещё не выбраны..." */}
                    <div
                      className="relative min-h-[40px] rounded-2xl border border-slate-700/70 bg-slate-900/80"
                      onClick={() => deptRef.current?.focus()}
                    >
                      {/* Подсказка (не сдвигает курсор) */}
                      {!departmentName.trim() && !deptFocused && (
                        <div className="pointer-events-none absolute inset-0 px-3 py-2 text-xs text-slate-500">
                          Например: Отдел мониторинга и реагирования, УОМЗ г. Первоуральск
                        </div>
                      )}

                      {/* Реальное поле ввода */}
                      <textarea
                        ref={deptRef}
                        value={departmentName}
                        onChange={(e) => setDepartmentName(e.target.value)}
                        onFocus={() => setDeptFocused(true)}
                        onBlur={() => setDeptFocused(false)}
                        rows={1}
                        className="w-full min-h-[40px] bg-transparent px-3 py-2 text-sm text-slate-50 focus:outline-none resize-none overflow-y-auto"
                      />
                    </div>

                    <p className="text-xs text-slate-400">
                      Это название будет отображаться в шапке сервиса и в формируемых документах.
                    </p>
                  </div>

                  {/* Выбранные регионы */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <label className="block text-sm font-medium text-slate-100">
                        Регионы мониторинга
                      </label>
                      {selectedRegionIds.length > 0 && (
                        <span className="text-xs text-slate-400">Выбрано: {selectedRegionIds.length}</span>
                      )}
                    </div>

                    <div className="min-h-[40px] rounded-2xl border border-slate-700/70 bg-slate-900/80 px-3 py-2">
                      {selectedRegionIds.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          Регионы ещё не выбраны. Отметьте один или несколько регионов в списке
                          ниже.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {selectedRegionIds.map((id) => (
                            <span
                              key={id}
                              className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 border border-sky-500/40 px-3 py-1 text-xs text-sky-100"
                            >
                              <span>{regionIdToName.get(id) ?? id}</span>
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

                    {/* СКРОЛБОКС СО СПИСКОМ РЕГИОНОВ */}
                    <div className="rounded-2xl border border-slate-700 bg-slate-900/90">
                      <div className="max-h-60 overflow-y-auto divide-y divide-slate-800">
                        {regionsLoading ? (
                          <div className="px-3 py-3 text-sm text-slate-300">Загрузка списка регионов…</div>
                        ) : (
                          regions.map((r) => {
                            const id = String(r.id);
                            const active = selectedRegionIds.includes(id);
                            return (
                              <button
                                key={id}
                                type="button"
                                onClick={() => toggleRegionId(id)}
                                className={
                                  "w-full flex items-center justify-between px-3 py-2.5 text-left text-xs sm:text-sm transition " +
                                  (active
                                    ? "bg-sky-500/15 text-sky-100"
                                    : "text-slate-200 hover:bg-slate-800/80")
                                }
                              >
                                <span>{r.name}</span>
                                {active && (
                                  <span className="ml-3 h-2.5 w-2.5 rounded-full bg-sky-400" />
                                )}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400">
                      Выбранные регионы используются в отчётах, фильтрах и в шапке панели
                      мониторинга.
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 pt-2">
                  <div className="text-xs text-slate-400">
                    Изменения можно будет скорректировать в любой момент.
                  </div>
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
            <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
              Панель администратора
            </h2>
            <p className="text-sm text-slate-200 mb-3">
              Здесь администратор настраивает базовые параметры системы перед началом работы
              операторов.
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
              После первичной настройки администратора остальные сотрудники будут заходить только
              через стандартную страницу авторизации и работать с панелью мониторинга в своих ролях.
            </p>
          </div>

          <div className="rounded-3xl bg-slate-900/80 border border-slate-700/60 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide">
                  Карта регионов РФ
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Клик по региону добавляет/убирает его в выбранные.
                </p>
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
                  selectedRegionIds={selectedRegionKeys}
                  padding={10}
                  onRegionClick={(key) => handleMapClick(key)}
                />
              </div>
            </div>
            </div>
        </div>
      </div>
    </div>
  );
}
