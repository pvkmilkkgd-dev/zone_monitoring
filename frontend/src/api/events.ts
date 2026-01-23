import api from "../utils/http";

export type EventImage = {
  id: number;
  name: string;
  file_path: string;
  created_at: string;
};

export type EventDocument = {
  id: number;
  name: string;
  file_path: string;
  created_at: string;
};

export type EventComment = {
  id: number;
  event_id: number;
  user_id: number | null;
  user_name: string | null;
  text: string;
  created_at: string;
};

export type EventListItem = {
  id: number;
  map_id: number;
  administrative_zone_id: number | null;
  department_name: string | null;
  district_name: string | null;
  status: string;
  title: string;
  description: string | null;
  importance: number;
  is_archived: boolean;
  layer_id: number | null;
  sub_layer_id: number | null;
  sub_sub_layer_id: number | null;
  created_by_id: number | null;
  created_by_name: string | null;
  updated_by_id: number | null;
  updated_by_name: string | null;
  created_at: string;
  updated_at: string | null;
  images_count: number;
  documents_count: number;
  comments_count: number;
};

export type EventDetail = {
  id: number;
  map_id: number;
  administrative_zone_id: number | null;
  department_name: string | null;
  district_name: string | null;
  status: string;
  title: string;
  description: string | null;
  importance: number;
  is_archived: boolean;
  layer_id: number | null;
  sub_layer_id: number | null;
  sub_sub_layer_id: number | null;
  created_by_id: number | null;
  created_by_name: string | null;
  updated_by_id: number | null;
  updated_by_name: string | null;
  created_at: string;
  updated_at: string | null;
  images: EventImage[];
  documents: EventDocument[];
  comments: EventComment[];
};

export type EventCreateData = {
  map_id: number;
  district_name: string;
  title: string;
  description?: string;
  importance: number;
  layer_id?: number | null;
  sub_layer_id?: number | null;
  sub_sub_layer_id?: number | null;
  images?: File[];
  documents?: File[];
};

export type EventUpdateData = {
  title?: string;
  description?: string | null;
  importance?: number;
  status?: string;
  is_archived?: boolean;
  district_name?: string;
  layer_id?: number | null;
  sub_layer_id?: number | null;
  sub_sub_layer_id?: number | null;
};

export const getEvents = async (): Promise<EventListItem[]> => {
  const { data } = await api.get<EventListItem[]>("/events");
  return data;
};

export const getEvent = async (eventId: number): Promise<EventDetail> => {
  const { data } = await api.get<EventDetail>(`/events/${eventId}`);
  return data;
};

export const createEvent = async (eventData: EventCreateData): Promise<EventDetail> => {
  const formData = new FormData();
  formData.append("map_id", String(eventData.map_id));
  formData.append("district_name", eventData.district_name);
  formData.append("title", eventData.title);
  formData.append("importance", String(eventData.importance));
  
  if (eventData.description) {
    formData.append("description", eventData.description);
  }
  
  if (eventData.layer_id != null) {
    formData.append("layer_id", String(eventData.layer_id));
  }
  
  if (eventData.sub_layer_id != null) {
    formData.append("sub_layer_id", String(eventData.sub_layer_id));
  }
  
  if (eventData.sub_sub_layer_id != null) {
    formData.append("sub_sub_layer_id", String(eventData.sub_sub_layer_id));
  }
  
  if (eventData.images) {
    eventData.images.forEach((file) => {
      formData.append("images", file);
    });
  }
  
  if (eventData.documents) {
    eventData.documents.forEach((file) => {
      formData.append("documents", file);
    });
  }
  
  const { data } = await api.post<EventDetail>("/events", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data;
};

export const updateEvent = async (eventId: number, eventData: EventUpdateData): Promise<EventDetail> => {
  const { data } = await api.put<EventDetail>(`/events/${eventId}`, eventData);
  return data;
};

export const deleteEvent = async (eventId: number): Promise<void> => {
  await api.delete(`/events/${eventId}`);
};

export const addEventComment = async (eventId: number, text: string): Promise<EventComment> => {
  const { data } = await api.post<EventComment>(`/events/${eventId}/comments`, { text });
  return data;
};

export const deleteEventComment = async (eventId: number, commentId: number): Promise<void> => {
  await api.delete(`/events/${eventId}/comments/${commentId}`);
};
