/**
 * Утилиты для работы с авторизацией
 */

const TOKEN_KEY = "zone_jwt";
const ROLE_KEY = "zone_role";

/**
 * Проверяет, авторизован ли пользователь
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem(TOKEN_KEY);
}

/**
 * Получает токен авторизации
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Получает роль пользователя
 */
export function getUserRole(): string | null {
  return localStorage.getItem(ROLE_KEY);
}

/**
 * Выполняет выход из системы и перенаправляет на страницу входа
 */
export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  window.location.href = "/";
}

/**
 * Проверяет авторизацию и перенаправляет на страницу входа, если пользователь не авторизован
 * Использовать в useEffect
 */
export function requireAuth(): boolean {
  if (!isAuthenticated()) {
    window.location.href = "/";
    return false;
  }
  return true;
}

/**
 * Обрабатывает ошибку авторизации
 * Если это ошибка 401, выполняет logout
 */
export function handleAuthError(error: any): boolean {
  if (
    error?.response?.status === 401 ||
    error?.status === 401 ||
    error?.message?.includes("401") ||
    error?.message?.includes("Не авторизован")
  ) {
    logout();
    return true;
  }
  return false;
}

/**
 * Проверяет, имеет ли пользователь указанную роль
 */
export function hasRole(role: string): boolean {
  return getUserRole() === role;
}

/**
 * Проверяет, является ли пользователь администратором
 */
export function isAdmin(): boolean {
  return hasRole("admin");
}

/**
 * Проверяет, является ли пользователь редактором или администратором
 */
export function canEdit(): boolean {
  const role = getUserRole();
  return role === "admin" || role === "editor";
}
