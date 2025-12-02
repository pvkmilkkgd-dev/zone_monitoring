import { apiRequest, getStoredToken, setStoredToken } from "./apiClient";

export type UserRole = "viewer" | "editor";

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  username: string;
  role: UserRole;
}

const USERNAME_KEY = "zm_username";
const ROLE_KEY = "zm_role";

export async function login(username: string, password: string): Promise<void> {
  const data = await apiRequest<LoginResponse>("/auth/login", "POST", {
    username,
    password,
  });

  setStoredToken(data.access_token);
  localStorage.setItem(USERNAME_KEY, data.username);
  localStorage.setItem(ROLE_KEY, data.role);
}

export function logout(): void {
  setStoredToken(null);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function getCurrentUser():
  | { username: string; role: UserRole; token: string }
  | null {
  const token = getStoredToken();
  if (!token) return null;

  const username = localStorage.getItem(USERNAME_KEY) ?? "";
  const role = (localStorage.getItem(ROLE_KEY) ?? "viewer") as UserRole;

  return { username, role, token };
}

export function getCurrentUserName(): string | null {
  return getCurrentUser()?.username ?? null;
}

export function getCurrentUserRole(): UserRole | null {
  return getCurrentUser()?.role ?? null;
}

export const clearAuth = logout;
