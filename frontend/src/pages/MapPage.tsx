import { useCallback, useEffect, useState } from "react";
import MapViewer from "../components/MapViewer";
import ZonePanel from "../components/ZonePanel";
import { Zone, ZoneState, getZones, getZoneState } from "../api/zones";
import { getCurrentMap } from "../api/maps";

const MapPage = () => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | undefined>(undefined);
  const [zoneState, setZoneState] = useState<ZoneState | undefined>(undefined);
  const [mapMeta, setMapMeta] = useState<string>("загрузка карты...");

  useEffect(() => {
    const load = async () => {
      try {
        setZones(await getZones());
      } catch {
        // TODO: surface error to UI
      }
      try {
        const meta = await getCurrentMap();
        if (meta?.filename) {
          setMapMeta(meta.filename);
        } else {
          setMapMeta("Карта не загружена (доступно администратору)");
        }
      } catch {
        setMapMeta("Не удалось получить карту");
      }
    };
    load();
  }, []);

  const handleZoneSelect = useCallback((zone: Zone, state: ZoneState) => {
    setSelectedZone(zone);
    setZoneState(state);
  }, []);

  const handleZoneClick = async (zone: Zone) => {
    setSelectedZone(zone);
    const state = await getZoneState(zone.id);
    setZoneState(state);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Zone Monitoring</h1>
          <p className="text-sm text-slate-500">Состояние зон и загруженная карта: {mapMeta}</p>
        </div>
        <a className="text-sm text-primary font-semibold" href="/login">
          Вход / сменить пользователя
        </a>
      </header>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="md:col-span-2 space-y-3">
          <MapViewer onZoneSelect={handleZoneSelect} />
          <div className="card">
            <div className="text-sm font-semibold mb-2">Зоны</div>
            <div className="flex flex-wrap gap-2">
              {zones.map((z) => (
                <button
                  key={z.id}
                  onClick={() => handleZoneClick(z)}
                  className={`px-3 py-2 rounded-lg border text-sm ${
                    selectedZone?.id === z.id ? "bg-primary text-white" : "bg-white"
                  }`}
                >
                  {z.name}
                </button>
              ))}
              {zones.length === 0 && <span className="text-slate-500 text-sm">Зон пока нет</span>}
            </div>
          </div>
        </div>
        <ZonePanel zone={selectedZone} state={zoneState} />
      </div>
    </div>
  );
};

export default MapPage;
