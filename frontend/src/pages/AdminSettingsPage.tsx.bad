import { useEffect, useState } from "react";
import { fetchSystemSettings, updateSystemSettings } from "../api";

const REGIONS = [
  "Алтайский край",
  "Амурская область",
  "Архангельская область",
  "Астраханская область",
  "Белгородская область",
  "Брянская область",
  "Владимирская область",
  "Волгоградская область",
  "Вологодская область",
  "Воронежская область",
  "Еврейская автономная область",
  "Забайкальский край",
  "Ивановская область",
  "Иркутская область",
  "Кабардино-Балкарская Республика",
  "Калининградская область",
  "Калужская область",
  "Камчатский край",
  "Карачаево-Черкесская Республика",
  "Кемеровская область",
  "Кировская область",
  "Костромская область",
  "Краснодарский край",
  "Красноярский край",
  "Курганская область",
  "Курская область",
  "Ленинградская область",
  "Липецкая область",
  "Магаданская область",
  "Москва",
  "Московская область",
  "Мурманская область",
  "Ненецкий автономный округ",
  "Нижегородская область",
  "Новгородская область",
  "Новосибирская область",
  "Омская область",
  "Оренбургская область",
  "Орловская область",
  "Пензенская область",
  "Пермский край",
  "Приморский край",
  "Псковская область",
  "Республика Адыгея",
  "Республика Алтай",
  "Республика Башкортостан",
  "Республика Бурятия",
  "Республика Дагестан",
  "Республика Ингушетия",
  "Республика Калмыкия",
  "Республика Карелия",
  "Республика Коми",
  "Республика Крым",
  "Республика Марий Эл",
  "Республика Мордовия",
  "Республика Саха (Якутия)",
  "Республика Северная Осетия — Алания",
  "Республика Татарстан",
  "Республика Тыва",
  "Республика Хакасия",
  "Ростовская область",
  "Рязанская область",
  "Самарская область",
  "Санкт-Петербург",
  "Саратовская область",
  "Сахалинская область",
  "Свердловская область",
  "Севастополь",
  "Смоленская область",
  "Ставропольский край",
  "Тамбовская область",
  "Тверская область",
  "Томская область",
  "Тульская область",
  "Тюменская область",
  "Удмуртская Республика",
  "Ульяновская область",
  "Хабаровский край",
  "Ханты-Мансийский автономный округ — Югра",
  "Челябинская область",
  "Чеченская Республика",
  "Чувашская Республика",
  "Чукотский автономный округ",
  "Ямало-Ненецкий автономный округ",
  "Ярославская область",
  "Донецкая Народная Республика",
  "Луганская Народная Республика",
  "Херсонская область",
  "Запорожская область",
];

export function AdminSettingsPage() {
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [departmentName, setDepartmentName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchSystemSettings();
        if (data) {
          if (data.region) {
            const regionsFromServer = String(data.region)
              .split(",")
              .map((r) => r.trim())
              .filter(Boolean);
            setSelectedRegions(regionsFromServer);
          }
          setDepartmentName(data.department_name || "");
        }
      } catch (e: any) {
        console.error(e);
        setError(e.message || "Ошибка загрузки настроек");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const toggleRegion = (region: string) => {
    setSelectedRegions((prev) =>
      prev.includes(region) ? prev.filter((r) => r !== region) : [...prev, region]
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const regionValue =
        selectedRegions.length > 0 ? selectedRegions.join(", ") : null;

      await updateSystemSettings({
        region: regionValue,
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
      <div className="max-w-5xl w-full grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        {/* Левая панель */}
        <div className="relative overflow-hidden rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur">
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
                    <input
                      type="text"
                      value={departmentName}
                      onChange={(e) => setDepartmentName(e.target.value)}
                      placeholder="Например: Отдел мониторинга и реагирования, УОМЗ г. Первоуральск"
                      className="w-full rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    />
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
                      {selectedRegions.length > 0 && (
                        <span className="text-xs text-slate-400">
                          Выбрано: {selectedRegions.length}
                        </span>
                      )}
                    </div>

                    <div className="min-h-[40px] rounded-2xl border border-slate-700/70 bg-slate-900/80 px-3 py-2">
                      {selectedRegions.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          Регионы ещё не выбраны. Отметьте один или несколько регионов в списке
                          ниже.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {selectedRegions.map((region) => (
                            <span
                              key={region}
                              className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 border border-sky-500/40 px-3 py-1 text-xs text-sky-100"
                            >
                              <span>{region}</span>
                              <button
                                type="button"
                                onClick={() => toggleRegion(region)}
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
                        {REGIONS.map((region) => {
                          const active = selectedRegions.includes(region);
                          return (
                            <button
                              key={region}
                              type="button"
                              onClick={() => toggleRegion(region)}
                              className={
                                "w-full flex items-center justify-between px-3 py-2.5 text-left text-xs sm:text-sm transition " +
                                (active
                                  ? "bg-sky-500/15 text-sky-100"
                                  : "text-slate-200 hover:bg-slate-800/80")
                              }
                            >
                              <span>{region}</span>
                              {active && (
                                <span className="ml-3 h-2.5 w-2.5 rounded-full bg-sky-400" />
                              )}
                            </button>
                          );
                        })}
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
        <div className="space-y-4">
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
        </div>
      </div>
    </div>
  );
}
