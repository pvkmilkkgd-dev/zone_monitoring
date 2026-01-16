import { useEffect, useState } from "react";
import { fetchUsers, createUserByAdmin, updateUserRole, UserDto } from "../api";

type UserRole = "admin" | "editor" | "viewer";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Администратор",
  editor: "Редактор",
  viewer: "Пользователь",
};

const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: "Полный доступ ко всем функциям системы",
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
    full_name: "",
    role: "viewer" as UserRole,
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
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
      setError(e.message || "Ошибка загрузки пользователей");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUser.username.trim()) {
      setNotification({ type: "error", message: "Введите логин пользователя" });
      setTimeout(() => setNotification(null), 3000);
      return;
    }
    if (!newUser.password.trim()) {
      setNotification({ type: "error", message: "Введите пароль" });
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    try {
      setCreating(true);
      setError(null);

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
        full_name: "",
        role: "viewer",
      });
      setShowCreateForm(false);

      // Перезагрузка списка
      await loadUsers();
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Ошибка создания пользователя");
      setNotification({ type: "error", message: e.message || "Ошибка создания пользователя" });
      setTimeout(() => setNotification(null), 5000);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <button
              onClick={() => {
                window.location.href = "/admin";
              }}
              className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 transition"
            >
              ← Настройки
            </button>
            <h1 className="text-3xl lg:text-4xl font-semibold tracking-tight">Пользователи</h1>
          </div>
          <p className="text-sm text-slate-300/90 max-w-2xl">
            Управление пользователями системы. Создавайте новых пользователей и назначайте им роли: Администраторы, Редакторы, Пользователи.
          </p>
        </div>

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
            onClick={() => setShowCreateForm(!showCreateForm)}
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
              <div>
                <label className="block text-sm font-medium text-slate-100 mb-2">
                  Логин <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full rounded-xl border border-slate-700/70 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
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
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full rounded-xl border border-slate-700/70 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                  placeholder="Введите пароль"
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
                    setNewUser({ username: "", password: "", full_name: "", role: "viewer" });
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
