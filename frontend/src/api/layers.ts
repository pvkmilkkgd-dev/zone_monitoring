import api from "../utils/http";

export interface SubSubLayer {
  id: number;
  name: string;
  parent_sub_layer_id: number;
  is_visible: boolean;
  order: number;
}

export interface SubLayer {
  id: number;
  name: string;
  parent_layer_id: number;
  is_visible: boolean;
  order: number;
  sub_sub_layers: SubSubLayer[];
}

export interface Layer {
  id: number;
  name: string;
  map_id: number;
  is_visible: boolean;
  order: number;
  sub_layers: SubLayer[];
}

export interface LayerCreate {
  name: string;
  map_id: number;
}

export interface LayerUpdate {
  name?: string;
  is_visible?: boolean;
  order?: number;
}

export interface SubLayerCreate {
  name: string;
  parent_layer_id: number;
}

export interface SubLayerUpdate {
  name?: string;
  is_visible?: boolean;
  order?: number;
}

export interface SubSubLayerCreate {
  name: string;
  parent_sub_layer_id: number;
}

export interface SubSubLayerUpdate {
  name?: string;
  is_visible?: boolean;
  order?: number;
}

export async function getLayers(): Promise<Layer[]> {
  const { data } = await api.get<Layer[]>("/layers");
  return data;
}

export async function getLayer(id: number): Promise<Layer> {
  const { data } = await api.get<Layer>(`/layers/${id}`);
  return data;
}

export async function createLayer(data: LayerCreate): Promise<Layer> {
  const response = await api.post<Layer>("/layers", data);
  return response.data;
}

export async function updateLayer(id: number, data: LayerUpdate): Promise<Layer> {
  const response = await api.patch<Layer>(`/layers/${id}`, data);
  return response.data;
}

export async function deleteLayer(id: number): Promise<void> {
  await api.delete(`/layers/${id}`);
}

export async function createSubLayer(data: SubLayerCreate): Promise<SubLayer> {
  const response = await api.post<SubLayer>("/layers/sublayers", data);
  return response.data;
}

export async function updateSubLayer(id: number, data: SubLayerUpdate): Promise<SubLayer> {
  const response = await api.patch<SubLayer>(`/layers/sublayers/${id}`, data);
  return response.data;
}

export async function deleteSubLayer(id: number): Promise<void> {
  await api.delete(`/layers/sublayers/${id}`);
}

export async function createSubSubLayer(data: SubSubLayerCreate): Promise<SubSubLayer> {
  const response = await api.post<SubSubLayer>("/layers/subsublayers", data);
  return response.data;
}

export async function updateSubSubLayer(id: number, data: SubSubLayerUpdate): Promise<SubSubLayer> {
  const response = await api.patch<SubSubLayer>(`/layers/subsublayers/${id}`, data);
  return response.data;
}

export async function deleteSubSubLayer(id: number): Promise<void> {
  await api.delete(`/layers/subsublayers/${id}`);
}

export interface ReorderItem {
  id: number;
  order: number;
}

export async function reorderLayers(items: ReorderItem[]): Promise<Layer[]> {
  const response = await api.post<Layer[]>("/layers/reorder", { items });
  return response.data;
}

export async function reorderSubLayers(items: ReorderItem[]): Promise<void> {
  await api.post("/layers/sublayers/reorder", { items });
}

export async function reorderSubSubLayers(items: ReorderItem[]): Promise<void> {
  await api.post("/layers/subsublayers/reorder", { items });
}
