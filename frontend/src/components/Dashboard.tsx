import { useEffect, useState } from "react";
import { fetchMe, UserMe } from "../api/client";
import { RegionMap } from "./RegionMap";

type Props = {
  accessToken: string;
  onLogout: () => void;
};

const CONFIG_ROLES = ["admin", "editor"]; // роли, которые могут настраивать карту

export function Dashboard({ accessToken, onLogout }: Props) {
  const [me, setMe] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // выбранные регионы (по имени из geojson)
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);

  // общее название группы
  const [groupName, setGroupName] = useState("");

  // пользовательские подписи для регионов: { "Свердловская область": "Уральский кластер" }
  const [regionAliases, setRegionAliases] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const meResp = await fetchMe(accessToken);
        if (!cancelled) {
          setMe(meResp);

          // TODO: здесь позже подтягиваем настройки с backend:
          // const cfg = await fetchRegionsConfig(accessToken);
          // setSelectedRegions(cfg.regions);
          // setGroupName(cfg.groupName);
          // setRegionAliases(cfg.aliases);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError("Ошибка загрузки данных. Возможно, токен устарел.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  const isConfigurator =
    me && CONFIG_ROLES.includes(me.role.toLowerCase());

  const handleToggleRegion = (regionName: string) => {
    if (!isConfigurator) return;

    setSelectedRegions((prev) => {
      if (prev.includes(regionName)) {
        const next = prev.filter((r) => r !== regionName);
        setRegionAliases((prevAliases) => {
          const copy = { ...prevAliases };
          delete copy[regionName];
          return copy;
        });

        // TODO: сохранить next на backend
        return next;
      } else {
        setRegionAliases((prevAliases) => ({
          ...prevAliases,
          [regionName]: prevAliases[regionName] ?? regionName,
        }));

        const next = [...prev, regionName];
        // TODO: сохранить next на backend
        return next;
      }
    });
  };

  const handleAliasChange = (regionName: string, value: string) => {
    setRegionAliases((prev) => ({
      ...prev,
      [regionName]: value,
    }));

    // TODO: сохранить на backend вместе с groupName/regions
  };

  if (loading) {
    return <div className="center-message">Загрузка...</div>;
  }

  if (error) {
    return (
      <div className="card center-card">
        <div className="error-msg">{error}</div>
        <button className="btn-secondary" onClick={onLogout}>
          Войти снова
        </button>
      </div>
    );
  }

  return (
    <div className="map-screen">
      <div className="map-top-bar">
        {me && (
          <div className="user-pill">
            <span className="user-pill-name">{me.username}</span>
            <span className="user-pill-role">{me.role}</span>
          </div>
        )}
      </div>

      <div className="map-layout">
        {/* Левая колонка — карта, ЖЁСТКО ограниченная */}
        <div className="map-layout-left">
          <div className="map-canvas">
            <RegionMap
              selectedRegions={selectedRegions}
              isInteractive={!!isConfigurator}
              onToggleRegion={isConfigurator ? handleToggleRegion : undefined}
            />
          </div>
        </div>

        {/* Правая колонка — панель с полями */}
        <div className="map-layout-right">
          <div className="card config-panel">
            <h2>Группа регионов</h2>

            <label className="form-label">
              Общее название
              <input
                type="text"
                className="input"
                placeholder="Например: Уральский кластер"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                disabled={!isConfigurator}
              />
            </label>

            <div className="config-panel-list">
              <div className="config-panel-list-header">
                Выбранные регионы
              </div>

              {selectedRegions.length === 0 ? (
                <div className="config-panel-empty">
                  Пока ничего не выбрано. В режиме администратора нажмите на регионы на карте.
                </div>
              ) : (
                selectedRegions.map((name) => (
                  <div className="config-panel-row" key={name}>
                    <input
                      type="text"
                      className="input"
                      value={regionAliases[name] ?? name}
                      onChange={(e) =>
                        handleAliasChange(name, e.target.value)
                      }
                      disabled={!isConfigurator}
                    />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
