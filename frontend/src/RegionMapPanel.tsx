import React from "react";
import SverdlovskMap from "./assets/maps/sverdlovsk-scheme.svg";

interface RegionMapPanelProps {
  region: string | null;
}

interface DistrictInfo {
  name: string;
  center: string;
}

const REGION_MAPS: Record<string, { image?: string; districts?: DistrictInfo[] }> = {
  "Свердловская область": {
    image: SverdlovskMap,
    districts: [
      { name: "Екатеринбург", center: "Екатеринбург" },
      { name: "Первоуральский городской округ", center: "Первоуральск" },
      { name: "Нижний Тагил", center: "Нижний Тагил" },
      { name: "Каменск-Уральский", center: "Каменск-Уральский" },
      { name: "Серовский городской округ", center: "Серов" },
      { name: "Ревдинский городской округ", center: "Ревда" },
    ],
  },
};

export const RegionMapPanel: React.FC<RegionMapPanelProps> = ({ region }) => {
  if (!region) {
    return (
      <div className="rounded-3xl bg-slate-900/85 border border-slate-800 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
        <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
          Карта региона
        </h2>
        <p className="text-sm text-slate-300">
          Выберите регион слева, чтобы увидеть его карту и основные районы.
        </p>
      </div>
    );
  }

  const config = REGION_MAPS[region];

  if (!config || !config.image) {
    return (
      <div className="rounded-3xl bg-slate-900/85 border border-slate-800 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
        <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
          Карта региона
        </h2>
        <p className="text-sm text-slate-200 mb-2">{region}</p>
        <p className="text-xs text-slate-400">
          Для этого региона карта ещё не настроена. Позже сюда можно будет добавить SVG-карту
          с делением на административные районы.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-3xl bg-slate-900/85 border border-slate-800 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
      <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
        Карта региона
      </h2>

      <p className="text-sm text-slate-200 mb-2">{region}</p>

      <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 overflow-hidden mb-4">
        <div className="bg-slate-900/80 border-b border-slate-800 px-3 py-2 text-[11px] uppercase tracking-wide text-slate-400">
          Схема административного деления
        </div>
        <div className="bg-slate-950/90 flex items-center justify-center p-3">
          <img
            src={config.image}
            alt={`Карта региона ${region}`}
            className="w-full max-h-80 object-contain"
          />
        </div>
      </div>

      {config.districts && (
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Основные районы и центры
          </div>
          <ul className="space-y-1 max-h-40 overflow-y-auto pr-1 text-xs text-slate-200">
            {config.districts.map((d) => (
              <li
                key={d.name}
                className="flex justify-between gap-2 rounded-lg bg-slate-800/70 px-2 py-1"
              >
                <span>{d.name}</span>
                <span className="text-sky-300">{d.center}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
