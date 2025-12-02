const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

const TOKEN_KEY = "zm_access_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export async function apiRequest<T>(
  path: string,
  method: HttpMethod = "GET",
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const token = getStoredToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401 || resp.status === 403) {
    // Можно здесь сразу чистить токен и кидать пользователя на логин
    throw new Error("Не авторизован. Войдите в систему.");
  }

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(
      `Ошибка API (${resp.status}): ${text || resp.statusText || "unknown"}`
    );
  }

  if (resp.status === 204) {
    // нет тела ответа
    return undefined as T;
  }

  return (await resp.json()) as T;
}
