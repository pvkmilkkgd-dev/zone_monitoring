/**
 * Утилиты для работы с авторизацией
 */

const TOKEN_KEY = "zone_jwt";
const ROLE_KEY = "zone_role";
const USER_ID_KEY = "zone_user_id";

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
  localStorage.removeItem(USER_ID_KEY);
  window.location.href = "/";
}

/**
 * Получает ID текущего пользователя
 */
export function getCurrentUserId(): number | null {
  const id = localStorage.getItem(USER_ID_KEY);
  return id ? parseInt(id, 10) : null;
}

/**
 * Проверяет, может ли пользователь редактировать все события (admin, editor_plus)
 */
export function canEditAll(): boolean {
  const role = getUserRole();
  return role === "admin" || role === "editor_plus";
}

/**
 * Проверяет, может ли текущий пользователь редактировать конкретное событие
 */
export function canEditEvent(createdById: number | null): boolean {
  if (canEditAll()) return true;
  if (getUserRole() === "editor") {
    const currentUserId = getCurrentUserId();
    return currentUserId !== null && createdById === currentUserId;
  }
  return false;
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
  return role === "admin" || role === "editor_plus" || role === "editor";
}

/**
 * Проверяет авторизацию и права администратора
 * Перенаправляет на /situation если пользователь не админ
 */
export function requireAdmin(): boolean {
  if (!isAuthenticated()) {
    window.location.href = "/";
    return false;
  }
  if (!isAdmin()) {
    window.location.href = "/situation";
    return false;
  }
  return true;
}

/**
 * Проверяет авторизацию и права редактора (admin, editor_plus, editor)
 * Перенаправляет на /situation если пользователь не имеет прав редактирования
 */
export function requireEditor(): boolean {
  if (!isAuthenticated()) {
    window.location.href = "/";
    return false;
  }
  if (!canEdit()) {
    window.location.href = "/situation";
    return false;
  }
  return true;
}
