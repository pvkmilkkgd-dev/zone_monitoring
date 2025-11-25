import api from "../utils/http";

export type MapMeta = {
  id?: number;
  filename: string;
  bounds?: Record<string, unknown>;
};

export const uploadMap = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<MapMeta>("/maps/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const getCurrentMap = async () => {
  const { data } = await api.get<MapMeta | null>("/maps/current");
  return data;
};
