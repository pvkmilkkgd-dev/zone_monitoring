import api from "../utils/http";

export type AdministrativeZone = {
  id: number;
  map_id: number;
  department_name: string;
  district_names: string[];
  layer_id?: number | null;
  sub_layer_id?: number | null;
  sub_sub_layer_id?: number | null;
  created_at: string;
  updated_at?: string;
};

export type AdministrativeZoneCreate = {
  map_id: number;
  department_name: string;
  district_names: string[];
  layer_id?: number | null;
  sub_layer_id?: number | null;
  sub_sub_layer_id?: number | null;
};

export type AdministrativeZoneUpdate = {
  department_name?: string;
  district_names?: string[];
  layer_id?: number | null;
  sub_layer_id?: number | null;
  sub_sub_layer_id?: number | null;
};

export const getAdministrativeZones = async (mapId?: number) => {
  const params = mapId ? { map_id: mapId } : {};
  const { data } = await api.get<AdministrativeZone[]>("/administrative-zones", { params });
  return data;
};

export const getAdministrativeZone = async (zoneId: number) => {
  const { data } = await api.get<AdministrativeZone>(`/administrative-zones/${zoneId}`);
  return data;
};

export const createAdministrativeZone = async (payload: AdministrativeZoneCreate) => {
  const { data } = await api.post<AdministrativeZone>("/administrative-zones", payload);
  return data;
};

export const updateAdministrativeZone = async (zoneId: number, payload: AdministrativeZoneUpdate) => {
  const { data } = await api.put<AdministrativeZone>(`/administrative-zones/${zoneId}`, payload);
  return data;
};

export const deleteAdministrativeZone = async (zoneId: number) => {
  await api.delete(`/administrative-zones/${zoneId}`);
};
