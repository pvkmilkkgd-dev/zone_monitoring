import React from "react";
import { RegionBoundaryMap } from "./components/RegionBoundaryMap";

interface RegionMapPanelProps {
  region: string | null;
}

const SUPPORTED_REGIONS = [
  "Свердловская область",
];

export const RegionMapPanel: React.FC<RegionMapPanelProps> = ({ region }) => {
  if (!region) {
    return (
      <div className="rounded-3xl bg-slate-900/85 border border-slate-800 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
        <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
          Карта региона
        </h2>
        <p className="text-sm text-slate-300">
          Выберите регион слева, чтобы увидеть его границы на карте.
        </p>
      </div>
    );
  }

  const isSupported = SUPPORTED_REGIONS.includes(region);

  if (!isSupported) {
    return (
      <div className="rounded-3xl bg-slate-900/85 border border-slate-800 p-5 lg:p-6 shadow-lg shadow-slate-950/60">
        <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-3">
          Карта региона
        </h2>
        <p className="text-sm text-slate-200 mb-2">{region}</p>
        <p className="text-xs text-slate-400">
          Для этого региона карта ещё не настроена. Границы регионов можно добавить через панель администратора.
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

      <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 overflow-hidden">
        <div className="bg-slate-900/80 border-b border-slate-800 px-3 py-2 text-[11px] uppercase tracking-wide text-slate-400">
          Границы региона
        </div>
        <div className="bg-slate-950/90 h-80">
          <RegionBoundaryMap regionName={region} />
        </div>
      </div>
    </div>
  );
};
