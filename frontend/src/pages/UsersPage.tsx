import { useEffect, useState } from "react";
import { fetchUsers, createUserByAdmin, updateUserRole, resetUserPassword, updateUserByAdmin, UserDto } from "../api/admin";
import { requireAuth, handleAuthError, logout } from "../utils/auth";

type UserRole = "admin" | "editor_plus" | "editor" | "viewer";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Администратор",
  editor_plus: "Редактор+",
  editor: "Редактор",
  viewer: "Пользователь",
};

const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: "Полный доступ ко всем функциям системы",
  editor_plus: "Расширенные права редактирования с доступом к дополнительным функциям",
  editor: "Может редактировать данные, но не управлять пользователями",
  viewer: "Только просмотр данных без возможности редактирования",
};

export function UsersPage() {
  const [users, setUsers] = useState<UserDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Форма создания пользователя
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    role: "viewer" as UserRole,
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Состояние для сброса пароля
  const [resettingPasswordFor, setResettingPasswordFor] = useState<number | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetting, setResetting] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Состояние для редактирования пользователя
  const [editingUser, setEditingUser] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ username: "", full_name: "" });
  const [updating, setUpdating] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Состояние для модального окна успеха
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!requireAuth()) return;
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchUsers();
      setUsers(data);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки пользователей");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    // Очищаем предыдущие ошибки
    setCreateError(null);

    if (!newUser.username.trim()) {
      setCreateError("Введите логин пользователя");
      return;
    }
    if (!newUser.password.trim()) {
      setCreateError("Введите пароль");
      return;
    }
    if (newUser.password.length < 6) {
      setCreateError("Пароль должен содержать минимум 6 символов");
      return;
    }
    if (newUser.password !== newUser.confirmPassword) {
      setCreateError("Пароли не совпадают");
      return;
    }

    try {
      setCreating(true);
      setCreateError(null);

      const payload = {
        username: newUser.username.trim(),
        password: newUser.password,
        role: newUser.role,
        ...(newUser.full_name.trim() ? { full_name: newUser.full_name.trim() } : {}),
      };

      await createUserByAdmin(payload);
      
      setNotification({ type: "success", message: "Пользователь успешно создан" });
      setTimeout(() => setNotification(null), 3000);

      // Сброс формы
      setNewUser({
        username: "",
        password: "",
        confirmPassword: "",
        full_name: "",
        role: "viewer",
      });
      setShowCreateForm(false);

      // Перезагрузка списка
      await loadUsers();
    } catch (e: any) {
      console.error(e);
      setCreateError(e.message || "Ошибка создания пользователя");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateRole = async (userId: number, newRole: UserRole) => {
    try {
      setError(null);
      await updateUserRole(userId, newRole);
      
      setNotification({ type: "success", message: "Роль пользователя обновлена" });
      setTimeout(() => setNotification(null), 3000);

      // Обновляем локальное состояние
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Ошибка обновления роли");
      setNotification({ type: "error", message: e.message || "Ошибка обновления роли" });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleResetPassword = async (userId: number) => {
    // Очищаем предыдущие ошибки
    setPasswordError(null);

    if (!newPassword.trim()) {
      setPasswordError("Введите новый пароль");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("Пароли не совпадают");
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError("Пароль должен содержать минимум 6 символов");
      return;
    }

    try {
      setResetting(true);
      setPasswordError(null);
      await resetUserPassword(userId, newPassword);
      
      // Закрываем форму
      setResettingPasswordFor(null);
      setNewPassword("");
      setConfirmPassword("");

      // Показываем модальное окно успеха
      setSuccessMessage("Пароль пользователя успешно изменен");
      setShowSuccessModal(true);
    } catch (e: any) {
      console.error(e);
      setPasswordError(e.message || "Ошибка изменения пароля");
    } finally {
      setResetting(false);
    }
  };

  const handleEditUser = (user: UserDto) => {
    setEditingUser(user.id);
    setEditForm({
      username: user.username,
      full_name: user.full_name || "",
    });
    setEditError(null); // Очищаем ошибки при открытии формы
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;

    // Очищаем предыдущие ошибки
    setEditError(null);

    if (!editForm.username.trim()) {
      setEditError("Введите логин пользователя");
      return;
    }

    try {
      setUpdating(true);
      setEditError(null);

      const payload: { username?: string; full_name?: string | null } = {};
      if (editForm.username.trim()) {
        payload.username = editForm.username.trim();
      }
      if (editForm.full_name.trim()) {
        payload.full_name = editForm.full_name.trim();
      } else {
        payload.full_name = null;
      }

      const updatedUser = await updateUserByAdmin(editingUser, payload);
      
      // Обновляем локальное состояние
      setUsers((prev) =>
        prev.map((u) => (u.id === editingUser ? updatedUser : u))
      );

      // Закрываем форму
      setEditingUser(null);
      setEditForm({ username: "", full_name: "" });

      // Показываем модальное окно успеха
      setSuccessMessage("Данные пользователя успешно обновлены");
      setShowSuccessModal(true);
    } catch (e: any) {
      console.error(e);
      setEditError(e.message || "Ошибка обновления данных пользователя");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white px-4 py-4">
      <div className="max-w-7xl mx-auto">
        {/* Навигация */}
        <div className="mb-3 flex items-center justify-between gap-4">
          <div className="flex gap-2 rounded-full bg-slate-800/80 p-1 text-sm">
            <button
              type="button"
              onClick={() => { window.location.href = "/admin"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Регион и управление
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/zones"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Зоны и устройства
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/layers"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Слои
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/events"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              События
            </button>
            <button
              type="button"
              className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
            >
              Пользователи
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = "/admin/situation"; }}
              className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              Обстановка
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={logout}
              className="shrink-0 px-3 py-1.5 rounded-lg text-sm text-slate-300 hover:text-red-300 hover:bg-red-500/10 border border-slate-600/50 hover:border-red-500/50 transition-colors"
            >
              Выход
            </button>
          </div>
        </div>

        {/* Заголовок */}
        <h1 className="text-2xl font-semibold tracking-tight mb-3">Пользователи</h1>

        {/* Уведомления */}
        {notification && (
          <div
            className={`mb-6 rounded-2xl border p-4 ${
              notification.type === "success"
                ? "border-sky-500/60 bg-sky-500/10 text-sky-100"
                : "border-red-500/60 bg-red-500/10 text-red-100"
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="text-sm">{notification.message}</p>
              <button
                onClick={() => setNotification(null)}
                className="ml-4 text-slate-400 hover:text-slate-200 transition-colors"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Ошибка */}
        {error && !notification && (
          <div className="mb-6 rounded-2xl border border-red-500/60 bg-red-500/10 p-4 text-red-100">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Кнопка создания пользователя */}
        <div className="mb-6">
            <button
              onClick={() => {
                setShowCreateForm(!showCreateForm);
                if (showCreateForm) {
                  setNewUser({ username: "", password: "", confirmPassword: "", full_name: "", role: "viewer" });
                  setCreateError(null);
                }
              }}
              className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showCreateForm ? "Отменить создание" : "Создать пользователя"}
            </button>
        </div>

        {/* Форма создания пользователя */}
        {showCreateForm && (
          <div className="mb-8 rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur">
            <h2 className="text-xl font-semibold mb-6">Новый пользователь</h2>
            <div className="space-y-5">
              {/* Отображение ошибок */}
              {createError && (
                <div className="rounded-xl border border-red-500/60 bg-red-500/10 p-3 text-red-100 text-sm">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">
                  Логин <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => {
                    setNewUser({ ...newUser, username: e.target.value });
                    setCreateError(null);
                  }}
                  className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                    createError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-900/80 focus:ring-sky-500/50"
                  }`}
                  placeholder="Введите логин пользователя"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">
                  Пароль <span className="text-red-400">*</span>
                </label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => {
                    setNewUser({ ...newUser, password: e.target.value });
                    setCreateError(null);
                  }}
                  className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                    createError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-900/80 focus:ring-sky-500/50"
                  }`}
                  placeholder="Введите пароль (минимум 6 символов)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">
                  Подтвердите пароль <span className="text-red-400">*</span>
                </label>
                <input
                  type="password"
                  value={newUser.confirmPassword}
                  onChange={(e) => {
                    setNewUser({ ...newUser, confirmPassword: e.target.value });
                    setCreateError(null);
                  }}
                  className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                    createError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-900/80 focus:ring-sky-500/50"
                  }`}
                  placeholder="Повторите пароль"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">Полное имя</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full rounded-xl border border-slate-700/70 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                  placeholder="Введите полное имя (необязательно)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">Роль</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value as UserRole })}
                  className="w-full rounded-xl border border-slate-700/70 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                >
                  {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
                    <option key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </option>
                  ))}
                </select>
                <p className="mt-1.5 text-xs text-slate-400">{ROLE_DESCRIPTIONS[newUser.role]}</p>
              </div>

              <div className="flex items-center gap-4 pt-2">
                <button
                  onClick={handleCreateUser}
                  disabled={creating}
                  className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60"
                >
                  {creating ? "Создание…" : "Создать пользователя"}
                </button>
                <button
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewUser({ username: "", password: "", confirmPassword: "", full_name: "", role: "viewer" });
                    setCreateError(null);
                  }}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-800 px-5 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition"
                >
                  Отмена
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Список пользователей */}
        <div className="rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-slate-300">Загрузка пользователей…</div>
          ) : users.length === 0 ? (
            <div className="p-8 text-center text-slate-300">
              Пользователи не найдены. Создайте первого пользователя.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-800/60 border-b border-slate-700">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Логин
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Полное имя
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Роль
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Дата создания
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-100 font-medium">
                        {user.username}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        {user.full_name || <span className="text-slate-500">—</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={user.role}
                          onChange={(e) => handleUpdateRole(user.id, e.target.value as UserRole)}
                          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                        >
                          {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
                            <option key={role} value={role}>
                              {ROLE_LABELS[role]}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                        {user.created_at
                          ? new Date(user.created_at).toLocaleDateString("ru-RU", {
                              year: "numeric",
                              month: "long",
                              day: "numeric",
                            })
                          : "—"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleEditUser(user)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 transition"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Редактировать
                          </button>
                          <button
                            onClick={() => {
                              setResettingPasswordFor(user.id);
                              setPasswordError(null); // Очищаем ошибки при открытии
                            }}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 transition"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            Пароль
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Модальное окно для редактирования пользователя */}
        {editingUser !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl bg-slate-900/95 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-slate-100">
                  Редактировать пользователя
                </h2>
                <button
                  onClick={() => {
                    setEditingUser(null);
                    setEditForm({ username: "", full_name: "" });
                    setEditError(null);
                  }}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-5">
                {/* Отображение ошибок */}
                {editError && (
                  <div className="rounded-xl border border-red-500/60 bg-red-500/10 p-3 text-red-100 text-sm">
                    {editError}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-100 mb-2">
                    Логин <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={editForm.username}
                    onChange={(e) => {
                      setEditForm({ ...editForm, username: e.target.value });
                      setEditError(null); // Очищаем ошибку при вводе
                    }}
                    className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                      editError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-800/80 focus:ring-sky-500/50"
                    }`}
                    placeholder="Введите логин пользователя"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-100 mb-2">
                    Полное имя
                  </label>
                  <input
                    type="text"
                    value={editForm.full_name}
                    onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                    className="w-full rounded-xl border border-slate-700/70 bg-slate-800/80 px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    placeholder="Введите полное имя (необязательно)"
                  />
                </div>

                <div className="flex items-center gap-4 pt-2">
                  <button
                    onClick={handleUpdateUser}
                    disabled={updating}
                    className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60"
                  >
                    {updating ? "Сохранение…" : "Сохранить изменения"}
                  </button>
                  <button
                    onClick={() => {
                      setEditingUser(null);
                      setEditForm({ username: "", full_name: "" });
                      setEditError(null);
                    }}
                    disabled={updating}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-800 px-5 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition disabled:opacity-60"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Модальное окно для сброса пароля */}
        {resettingPasswordFor !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl bg-slate-900/95 border border-slate-700/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-slate-100">
                  Сменить пароль пользователя
                </h2>
                <button
                  onClick={() => {
                    setResettingPasswordFor(null);
                    setNewPassword("");
                    setConfirmPassword("");
                    setPasswordError(null);
                  }}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4 text-sm text-slate-300">
                Пользователь: <span className="font-medium text-slate-100">
                  {users.find(u => u.id === resettingPasswordFor)?.username}
                </span>
              </div>

              <div className="space-y-5">
                {/* Отображение ошибок */}
                {passwordError && (
                  <div className="rounded-xl border border-red-500/60 bg-red-500/10 p-3 text-red-100 text-sm">
                    {passwordError}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-100 mb-2">
                    Новый пароль <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      setPasswordError(null); // Очищаем ошибку при вводе
                    }}
                    className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                      passwordError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-800/80 focus:ring-sky-500/50"
                    }`}
                    placeholder="Введите новый пароль (минимум 6 символов)"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-100 mb-2">
                    Подтвердите пароль <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      setPasswordError(null); // Очищаем ошибку при вводе
                    }}
                    className={`w-full rounded-xl border px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 ${
                      passwordError ? "border-red-500/60 bg-red-500/5" : "border-slate-700/70 bg-slate-800/80 focus:ring-sky-500/50"
                    }`}
                    placeholder="Повторите новый пароль"
                  />
                </div>

                <div className="flex items-center gap-4 pt-2">
                  <button
                    onClick={() => handleResetPassword(resettingPasswordFor)}
                    disabled={resetting}
                    className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60"
                  >
                    {resetting ? "Изменение…" : "Изменить пароль"}
                  </button>
                  <button
                    onClick={() => {
                      setResettingPasswordFor(null);
                      setNewPassword("");
                      setConfirmPassword("");
                      setPasswordError(null);
                    }}
                    disabled={resetting}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-800 px-5 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition disabled:opacity-60"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Модальное окно успешного сохранения */}
        {showSuccessModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl bg-slate-900/95 border border-sky-500/60 shadow-xl shadow-sky-900/40 p-6 lg:p-8 backdrop-blur">
              <div className="flex flex-col items-center text-center">
                {/* Иконка успеха */}
                <div className="mb-4 rounded-full bg-sky-500/20 p-4">
                  <svg className="w-12 h-12 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>

                {/* Заголовок */}
                <h2 className="text-xl font-semibold text-slate-100 mb-2">
                  Изменения сохранены
                </h2>

                {/* Сообщение */}
                <p className="text-sm text-slate-300 mb-6">
                  {successMessage}
                </p>

                {/* Кнопка закрытия */}
                <button
                  onClick={() => setShowSuccessModal(false)}
                  className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-6 py-2.5 text-sm font-medium text-slate-900 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition"
                >
                  Отлично
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
