import { RUSSIAN_REGIONS } from "@/constants/regions";

interface RegionsMultiSelectProps {
  value: string[];
  onChange: (regions: string[]) => void;
}

export function RegionsMultiSelect({ value, onChange }: RegionsMultiSelectProps) {
  const toggleRegion = (region: string) => {
    if (value.includes(region)) {
      onChange(value.filter((r) => r !== region));
    } else {
      onChange([...value, region]);
    }
  };

  const removeRegion = (region: string) => {
    onChange(value.filter((r) => r !== region));
  };

  return (
    <div className="space-y-4">
      {/* Выбранные регионы */}
      <div>
        <div className="mb-1 text-sm font-medium text-slate-100">
          Выбранные регионы
        </div>

        {value.length === 0 ? (
          <p className="text-xs text-slate-400">
            Пока ничего не выбрано. Нажмите на регион в списке ниже, чтобы добавить его.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {value.map((region) => (
              <button
                key={region}
                type="button"
                onClick={() => removeRegion(region)}
                className="group inline-flex items-center gap-1 rounded-full border border-sky-500/70 bg-sky-900/70 px-3 py-1 text-xs text-sky-50 shadow-sm hover:bg-sky-800/80"
              >
                <span className="whitespace-nowrap">{region}</span>
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-sky-500 text-[10px] text-white group-hover:bg-sky-400">
                  ×
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Список регионов в прокручиваемом поле */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-100">
          Список регионов
        </label>
        <p className="text-xs text-slate-400">
          Клик по региону добавляет или убирает его из выбранных.
        </p>

        <div
          className="
            mt-1 max-h-64 overflow-y-auto rounded-xl
            border border-sky-700/60 bg-sky-950/40
            backdrop-blur-sm
          "
        >
          <ul className="divide-y divide-sky-900/60">
            {RUSSIAN_REGIONS.map((region) => {
              const selected = value.includes(region);
              return (
                <li key={region}>
                  <button
                    type="button"
                    onClick={() => toggleRegion(region)}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left text-xs sm:text-sm transition ${
                      selected
                        ? "bg-sky-900/70 text-sky-50"
                        : "text-slate-100 hover:bg-sky-900/40"
                    }`}
                  >
                    <span>{region}</span>
                    <span
                      className={`ml-3 inline-flex h-5 w-5 items-center justify-center rounded-full border text-[10px] ${
                        selected
                          ? "border-sky-400 bg-sky-500 text-white"
                          : "border-slate-500 text-slate-400"
                      }`}
                    >
                      {selected ? "✓" : "+"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
