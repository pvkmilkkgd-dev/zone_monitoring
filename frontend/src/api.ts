// src/api.ts
import { apiRequest } from "./apiClient";

export type ZoneEvent = {
  id: number;
  map_name: string;
  zone_name: string;
  status: string;
  title: string;
  description: string;
  created_at: string;
};

export function fetchEvents(): Promise<ZoneEvent[]> {
  return apiRequest<ZoneEvent[]>("/events", "GET");
}
