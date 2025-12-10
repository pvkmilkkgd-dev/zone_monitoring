const API_BASE_URL = "http://127.0.0.1:8000";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function loginRequest(username: string, password: string): Promise<string> {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);
  params.append("grant_type", "password");

  const res = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Ошибка входа: ${res.status} ${text}`);
  }

  const data = (await res.json()) as LoginResponse;
  return data.access_token;
}

export type UserMe = {
  id: number;
  username: string;
  role: string;
  created_at: string;
};

export async function fetchMe(token: string): Promise<UserMe> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error("Не удалось получить данные пользователя");
  }

  return (await res.json()) as UserMe;
}

// Тип зоны подгони под свой ответ backend
export type Zone = {
  id: number;
  name: string;
  state?: string;
};

export async function fetchZones(token: string): Promise<Zone[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/zones`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error("Не удалось загрузить зоны");
  }

  return (await res.json()) as Zone[];
}
