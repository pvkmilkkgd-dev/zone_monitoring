// src/zonesApi.ts
import { apiRequest } from "./apiClient";

export interface Zone {
  id: number;
  name: string;
  is_active: boolean;
}

export async function fetchZones(): Promise<Zone[]> {
  return apiRequest<Zone[]>("/zones", "GET");
}

export async function updateZoneState(zoneId: number, isActive: boolean) {
  await apiRequest(`/zones/${zoneId}/state`, "POST", {
    is_active: isActive,
  });
}
