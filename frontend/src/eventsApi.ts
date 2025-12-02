// src/eventsApi.ts
import { apiRequest } from "./apiClient";

export interface Event {
  id: number;
  zone_id: number;
  zone_name: string;
  event_type: string;
  created_at: string;
}

export async function fetchEvents(): Promise<Event[]> {
  return apiRequest<Event[]>("/events", "GET");
}
