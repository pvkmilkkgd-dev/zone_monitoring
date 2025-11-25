import api from "../utils/http";

export type Zone = {
  id: number;
  name: string;
  polygon: string;
};

export type ZoneState = {
  zone_id: number;
  parameters?: Record<string, unknown>;
  intensity?: string;
  category?: string;
  summary_text?: string;
};

export const getZones = async () => {
  const { data } = await api.get<Zone[]>("/zones");
  return data;
};

export const getZoneState = async (zoneId: number) => {
  const { data } = await api.get<ZoneState>(`/zones/${zoneId}/state`);
  return data;
};

export const updateZoneState = async (zoneId: number, payload: Partial<ZoneState>) => {
  const { data } = await api.post(`/zones/${zoneId}/state`, payload);
  return data;
};
