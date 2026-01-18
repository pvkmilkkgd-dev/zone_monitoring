import React, { useEffect, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";

interface RegionBoundaryMapProps {
  regionName: string;
}

interface GeoJSONFeature {
  type: string;
  properties: {
    id: string;
    name: string;
  };
  geometry: any;
}

interface GeoJSONFeatureCollection {
  type: string;
  features: GeoJSONFeature[];
}

export const RegionBoundaryMap: React.FC<RegionBoundaryMapProps> = ({ regionName }) => {
  const [geoData, setGeoData] = useState<GeoJSONFeatureCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bbox, setBbox] = useState<[number, number, number, number] | null>(null);

  useEffect(() => {
    const fetchRegionData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Получаем список регионов для определения ID
        const regionsRes = await fetch("/api/regions");
        if (!regionsRes.ok) throw new Error("Не удалось загрузить список регионов");
        
        const regions = await regionsRes.json();
        const region = regions.find((r: any) => r.name === regionName);
        
        if (!region) {
          throw new Error(`Регион "${regionName}" не найден`);
        }

        // Загружаем GeoJSON для региона
        const geoRes = await fetch(`/api/maps/ru/region/${region.id}/districts.geojson`);
        if (!geoRes.ok) throw new Error("Не удалось загрузить границы региона");
        
        const data: GeoJSONFeatureCollection = await geoRes.json();
        setGeoData(data);

        // Вычисляем bbox для центрирования карты
        if (data.features && data.features.length > 0) {
          const coordinates = extractAllCoordinates(data.features[0].geometry);
          if (coordinates.length > 0) {
            const lons = coordinates.map(c => c[0]);
            const lats = coordinates.map(c => c[1]);
            const minLon = Math.min(...lons);
            const maxLon = Math.max(...lons);
            const minLat = Math.min(...lats);
            const maxLat = Math.max(...lats);
            setBbox([minLon, minLat, maxLon, maxLat]);
          }
        }
      } catch (err: any) {
        console.error("Ошибка загрузки данных региона:", err);
        setError(err.message || "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };

    fetchRegionData();
  }, [regionName]);

  // Функция для извлечения всех координат из геометрии
  const extractAllCoordinates = (geometry: any): [number, number][] => {
    if (!geometry) return [];
    
    if (geometry.type === "Polygon") {
      return geometry.coordinates[0];
    } else if (geometry.type === "MultiPolygon") {
      return geometry.coordinates.flatMap((poly: any) => poly[0]);
    }
    return [];
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
        Загрузка карты...
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (!geoData || !bbox) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
        Нет данных для отображения
      </div>
    );
  }

  // Вычисляем центр и масштаб для отображения
  const centerLon = (bbox[0] + bbox[2]) / 2;
  const centerLat = (bbox[1] + bbox[3]) / 2;
  const lonDiff = bbox[2] - bbox[0];
  const latDiff = bbox[3] - bbox[1];
  const scale = Math.min(800 / lonDiff, 600 / latDiff) * 0.8;

  return (
    <div className="w-full h-full">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          center: [centerLon, centerLat],
          scale: scale,
        }}
        width={640}
        height={420}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup
          center={[centerLon, centerLat]}
          zoom={1}
          minZoom={0.5}
          maxZoom={8}
        >
          <Geographies geography={geoData}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  stroke="#38bdf8"
                  strokeWidth={2}
                  style={{
                    default: {
                      fill: "#0ea5e9",
                      fillOpacity: 0.15,
                      outline: "none",
                    },
                    hover: {
                      fill: "#0ea5e9",
                      fillOpacity: 0.25,
                      outline: "none",
                    },
                    pressed: {
                      fill: "#0ea5e9",
                      fillOpacity: 0.3,
                      outline: "none",
                    },
                  }}
                />
              ))
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>
    </div>
  );
};
