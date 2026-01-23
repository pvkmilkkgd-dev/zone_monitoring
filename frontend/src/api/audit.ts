import api from "../utils/http";

export type AuditLogItem = {
  id: number;
  action: string;
  user_id: number | null;
  user_name: string | null;
  entity_type: string | null;
  entity_id: number | null;
  entity_name: string | null;
  description: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type AuditLogsParams = {
  date_from?: string;
  date_to?: string;
  action?: string;
  entity_type?: string;
  user_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
};

export const getAuditLogs = async (params?: AuditLogsParams): Promise<AuditLogItem[]> => {
  const { data } = await api.get<AuditLogItem[]>("/audit", { params });
  return data;
};

export const getAuditActions = async (): Promise<string[]> => {
  const { data } = await api.get<string[]>("/audit/actions");
  return data;
};

export const getAuditEntityTypes = async (): Promise<string[]> => {
  const { data } = await api.get<string[]>("/audit/entity-types");
  return data;
};

export const exportAuditLogs = async (params?: AuditLogsParams): Promise<Blob> => {
  const { data } = await api.get("/audit/export", {
    params,
    responseType: "blob",
  });
  return data;
};
