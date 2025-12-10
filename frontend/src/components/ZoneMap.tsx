import { Zone } from "../api/client";

type Props = {
  zones: Zone[];
};

function getZoneClassByState(state?: string): string {
  if (!state) return "zone-tile--unknown";

  const s = state.toLowerCase();

  if (["ok", "normal", "active", "on", "в норме"].some((k) => s.includes(k))) {
    return "zone-tile--ok";
  }

  if (["warn", "warning", "attention", "предупр", "жёлт", "желт"].some((k) => s.includes(k))) {
    return "zone-tile--warning";
  }

  if (
    ["alarm", "error", "critical", "off", "offline", "авар", "красн"].some((k) =>
      s.includes(k)
    )
  ) {
    return "zone-tile--alarm";
  }

  return "zone-tile--unknown";
}

export function ZoneMap({ zones }: Props) {
  if (zones.length === 0) {
    return <div>Зон пока нет</div>;
  }

  return (
    <div className="zone-map-wrapper">
      <div className="zone-map">
        {zones.map((zone) => (
          <div
            key={zone.id}
            className={`zone-tile ${getZoneClassByState(zone.state)}`}
          >
            <div className="zone-tile-name">{zone.name}</div>
            {zone.state && <div className="zone-tile-state">{zone.state}</div>}
          </div>
        ))}
      </div>

      <div className="zone-legend">
        <span className="legend-item">
          <span className="legend-dot legend-ok" />
          Норма
        </span>
        <span className="legend-item">
          <span className="legend-dot legend-warning" />
          Предупреждение
        </span>
        <span className="legend-item">
          <span className="legend-dot legend-alarm" />
          Тревога / ошибка
        </span>
        <span className="legend-item">
          <span className="legend-dot legend-unknown" />
          Неизвестно
        </span>
      </div>
    </div>
  );
}
