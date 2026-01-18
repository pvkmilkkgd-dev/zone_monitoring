import { API_BASE_URL } from "../config";

export interface UserDto {
  id: number;
  username: string;
  full_name?: string | null;
  role: string;
  created_at: string;
}

// === СИСТЕМНЫЕ НАСТРОЙКИ АДМИНА ===

export interface SystemSettingsResponse {
  id: number;
  department_name: string | null;
  region_ids: string[]; // UUID[]
  region?: string | null; // совместимость

  created_at?: string;
  updated_at?: string;
}

export interface SystemSettingsUpdatePayload {
  department_name: string | null;
  region_ids: string[]; // UUID[]
}

function getAuthHeaders() {
  const token = localStorage.getItem("zone_jwt") || localStorage.getItem("access_token") || localStorage.getItem("accessToken");
  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchSystemSettings(): Promise<SystemSettingsResponse | null> {
  console.log("[API] fetchSystemSettings called, base =", API_BASE_URL);

  try {
    const resp = await fetch(`${API_BASE_URL}/admin/settings/`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...getAuthHeaders(),
      },
    });

    console.log("[API] fetchSystemSettings resp:", resp.status, resp.statusText);

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      console.error("fetchSystemSettings error body:", text);
      // вернём null, чтобы страница не висела в загрузке
      return null;
    }

    const data = await resp.json();
    console.log("[API] fetchSystemSettings data:", data);
    return data;
  } catch (e) {
    console.error("[API] fetchSystemSettings network error:", e);
    return null;
  }
}

export async function updateSystemSettings(
  payload: SystemSettingsUpdatePayload,
): Promise<SystemSettingsResponse> {
  console.log("[API] updateSystemSettings called with:", payload);

  const resp = await fetch(`${API_BASE_URL}/admin/settings/`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    console.error("[API] updateSystemSettings error body:", text);
    throw new Error(`Не удалось сохранить настройки (HTTP ${resp.status})`);
  }

  const data = (await resp.json()) as SystemSettingsResponse;
  console.log("[API] updateSystemSettings data:", data);
  return data;
}

export async function fetchUsers(): Promise<UserDto[]> {
  const resp = await fetch(`${API_BASE_URL}/admin/users/`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    let errorMessage = "Не удалось загрузить пользователей";
    try {
      const json = JSON.parse(text);
      if (json.detail) {
        errorMessage = json.detail;
      }
    } catch {
      // Если не JSON, используем текст или стандартное сообщение
      if (text) {
        errorMessage = `${errorMessage}: ${text}`;
      } else {
        errorMessage = `${errorMessage} (HTTP ${resp.status})`;
      }
    }
    throw new Error(errorMessage);
  }

  return resp.json();
}

export async function createUserByAdmin(payload: {
  username: string;
  password: string;
  full_name?: string;
  role: string;
}): Promise<UserDto> {
  const resp = await fetch(`${API_BASE_URL}/admin/users/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const data = await resp.json().catch(() => null);
    throw new Error(data?.detail || "Не удалось создать пользователя");
  }

  return resp.json();
}

export async function fetchCurrentUser() {
  const resp = await fetch(`${API_BASE_URL}/users/me`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });

  if (!resp.ok) {
    throw new Error("Failed to fetch current user");
  }

  return resp.json();
}

export async function updateCurrentUser(data: {
  username?: string;
  current_password: string;
  new_password?: string;
}) {
  const resp = await fetch(`${API_BASE_URL}/users/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const text = await resp.text();
    let message = "Не удалось обновить пользователя";
    try {
      const json = JSON.parse(text);
      if (json.detail) message = json.detail;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }

  return resp.json();
}

export async function updateUserRole(userId: number, role: string): Promise<UserDto> {
  const resp = await fetch(`${API_BASE_URL}/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ role }),
  });

  if (!resp.ok) {
    const data = await resp.json().catch(() => null);
    throw new Error(data?.detail || "Не удалось обновить роль пользователя");
  }

  return resp.json();
}

export async function updateUserByAdmin(
  userId: number,
  payload: { username?: string; full_name?: string | null }
): Promise<UserDto> {
  const resp = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const data = await resp.json().catch(() => null);
    throw new Error(data?.detail || "Не удалось обновить данные пользователя");
  }

  return resp.json();
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<UserDto> {
  const resp = await fetch(`${API_BASE_URL}/admin/users/${userId}/password`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ new_password: newPassword }),
  });

  if (!resp.ok) {
    const data = await resp.json().catch(() => null);
    throw new Error(data?.detail || "Не удалось изменить пароль пользователя");
  }

  return resp.json();
}
