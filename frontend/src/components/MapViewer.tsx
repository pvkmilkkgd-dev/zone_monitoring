import { useEffect, useRef } from "react";
import { getZones, getZoneState, Zone, ZoneState } from "../api/zones";

type Props = {
  onZoneSelect?: (zone: Zone, state: ZoneState) => void;
};

const MapViewer = ({ onZoneSelect }: Props) => {
  const onZoneSelectRef = useRef(onZoneSelect);
  
  // Обновляем ref при изменении функции
  useEffect(() => {
    onZoneSelectRef.current = onZoneSelect;
  }, [onZoneSelect]);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const zones = await getZones();
        if (zones.length === 0) return;
        const first = zones[0];
        const state = await getZoneState(first.id);
        onZoneSelectRef.current?.(first, state);
      } catch (err) {
        console.error("Failed to fetch zones", err);
      }
    };
    bootstrap();
  }, []); // Запускаем только один раз при монтировании

  return (
    <div className="card h-full min-h-[320px] flex items-center justify-center">
      <div className="text-center space-y-2">
        <div className="text-lg font-semibold">Карта в разработке</div>
        <p className="text-sm text-slate-500">
          Здесь появится интерактивная карта зон с GeoJSON-данными. Пока выберите зону из списка для загрузки
          состояния.
        </p>
      </div>
    </div>
  );
};

export default MapViewer;
