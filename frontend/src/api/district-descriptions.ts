import api from "../utils/http";

export type DistrictDescription = {
  id: number;
  district_name: string;
  description: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type DistrictDescriptionCreate = {
  district_name: string;
  description?: string | null;
};

export type DistrictDescriptionUpdate = {
  description?: string | null;
};

export const getDistrictDescriptions = async (): Promise<DistrictDescription[]> => {
  const { data } = await api.get<DistrictDescription[]>("/district-descriptions");
  return data;
};

export const getDistrictDescription = async (districtName: string): Promise<DistrictDescription | null> => {
  const { data } = await api.get<DistrictDescription | null>(`/district-descriptions/${encodeURIComponent(districtName)}`);
  return data;
};

export const createOrUpdateDistrictDescription = async (payload: DistrictDescriptionCreate): Promise<DistrictDescription> => {
  const { data } = await api.post<DistrictDescription>("/district-descriptions", payload);
  return data;
};

export const updateDistrictDescription = async (districtName: string, payload: DistrictDescriptionUpdate): Promise<DistrictDescription> => {
  const { data } = await api.put<DistrictDescription>(`/district-descriptions/${encodeURIComponent(districtName)}`, payload);
  return data;
};

export const deleteDistrictDescription = async (districtName: string): Promise<void> => {
  await api.delete(`/district-descriptions/${encodeURIComponent(districtName)}`);
};
