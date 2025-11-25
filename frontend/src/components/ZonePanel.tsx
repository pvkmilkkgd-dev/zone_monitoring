import { intensityToColor } from "../utils/color";
import { Zone, ZoneState } from "../api/zones";

type Props = {
  zone?: Zone;
  state?: ZoneState;
};

const ZonePanel = ({ zone, state }: Props) => {
  if (!zone || !state) {
    return (
      <div className="card h-full min-h-[240px] flex items-center justify-center text-slate-500">
        Выберите зону для просмотра информации.
      </div>
    );
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{zone.name}</h3>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${intensityToColor(state.intensity)}`}>
          {state.intensity || "n/a"}
        </span>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase text-slate-500">Категория</div>
        <div className="text-sm font-medium">{state.category || "—"}</div>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase text-slate-500">Параметры</div>
        <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs overflow-auto">
          {JSON.stringify(state.parameters ?? {}, null, 2)}
        </pre>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase text-slate-500">Описание</div>
        <p className="text-sm text-slate-700">{state.summary_text || "Нет данных"}</p>
      </div>
    </div>
  );
};

export default ZonePanel;
