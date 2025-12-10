import { FC, memo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";

type RegionMapProps = {
  selectedRegions: string[];
  onToggleRegion?: (regionName: string) => void;
  isInteractive?: boolean;
};

const geoUrl =
  "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/russia.geojson";

type MapPosition = {
  coordinates: [number, number];
  zoom: number;
};

const RegionMapComponent: FC<RegionMapProps> = ({
  selectedRegions,
  onToggleRegion,
  isInteractive = false,
}) => {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);

  const [position, setPosition] = useState<MapPosition>({
    coordinates: [60, 60],
    zoom: 1,
  });

  const handleClick = (name?: string) => {
    if (!isInteractive || !onToggleRegion || !name) return;
    onToggleRegion(name);
  };

  const handleEnter = (name?: string) => {
    if (!name) return;
    setHoveredRegion(name);
  };

  const handleLeave = () => {
    setHoveredRegion(null);
  };

  return (
    <div className="region-map-wrapper">
      <div className="region-map-inner">
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            center: [60, 60],
            scale: 600, // Чуть меньше, чем исходные 750
          }}
          width={480} // Было 600 — теперь компактнее
          height={320} // Было 400
          style={{ width: "100%", height: "100%" }}
        >
          <ZoomableGroup
            center={position.coordinates}
            zoom={position.zoom}
            minZoom={0.7}
            maxZoom={8}
            onMoveEnd={(pos) => {
              setPosition(pos as MapPosition);
            }}
          >
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const props = geo.properties as any;
                  const name: string | undefined =
                    props?.name || props?.NAME_RU || props?.NAME;

                  const isSelected =
                    !!name && selectedRegions.includes(name);

                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      onClick={() => handleClick(name)}
                      onMouseEnter={() => handleEnter(name)}
                      onMouseLeave={handleLeave}
                      stroke="#ffffff"
                      strokeWidth={0.5}
                      style={{
                        default: {
                          fill: isSelected ? "#f97316" : "#60a5fa",
                          outline: "none",
                          cursor: isInteractive ? "pointer" : "grab",
                        },
                        hover: {
                          fill: isSelected ? "#ea580c" : "#3b82f6",
                          outline: "none",
                          cursor: isInteractive ? "pointer" : "grab",
                        },
                        pressed: {
                          fill: isSelected ? "#c2410c" : "#1d4ed8",
                          outline: "none",
                          cursor: "grabbing",
                        },
                      }}
                    />
                  );
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>

        {hoveredRegion && (
          <div className="region-tooltip">{hoveredRegion}</div>
        )}
      </div>

      <div className="zone-legend">
        <span className="legend-item">
          <span className="legend-dot legend-selected" />
          Выбранный регион
        </span>
        <span className="legend-item">
          <span className="legend-dot legend-normal" />
          Обычный регион
        </span>
      </div>

      {isInteractive && (
        <div className="map-hint">
          Режим настройки: кликайте по регионам, чтобы добавить/убрать их из набора
          выбранных. Колёсико мыши — масштаб, зажатая ЛКМ — перемещение карты.
        </div>
      )}
    </div>
  );
};

export const RegionMap = memo(RegionMapComponent);
export default RegionMap;
