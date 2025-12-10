import { API_BASE_URL } from "./config";

function getAuthHeader() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchSystemSettings() {
  const res = await fetch(`${API_BASE_URL}/admin/settings/`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("Недостаточно прав или истёк токен");
  }

  if (!res.ok) {
    throw new Error("Не удалось загрузить настройки системы");
  }

  if (res.status === 204) return null;

  return res.json();
}

export async function updateSystemSettings(data: {
  region: string | null;
  department_name: string | null;
}) {
  const res = await fetch(`${API_BASE_URL}/admin/settings/`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(data),
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("Недостаточно прав или истёк токен");
  }

  if (!res.ok) {
    throw new Error("Ошибка при сохранении настроек системы");
  }

  return res.json();
}
