import { useEffect, useState } from "react";
import { fetchCurrentUser, updateCurrentUser } from "../api";

export function AdminProfilePage() {
  const [username, setUsername] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPassword2, setNewPassword2] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const me = await fetchCurrentUser();
        setUsername(me.username ?? "");
      } catch (e: any) {
        console.error(e);
        setError(e.message || "Ошибка загрузки профиля");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const handleSave = async () => {
    setError(null);
    setSuccess(null);

    if (!currentPassword) {
      setError("Укажите текущий пароль");
      return;
    }

    if (newPassword || newPassword2) {
      if (newPassword !== newPassword2) {
        setError("Новый пароль и повтор пароля не совпадают");
        return;
      }
    }

    try {
      setSaving(true);
      const payload: {
        username?: string;
        current_password: string;
        new_password?: string;
      } = {
        current_password: currentPassword,
      };

      if (username) payload.username = username;
      if (newPassword) payload.new_password = newPassword;

      const updated = await updateCurrentUser(payload);
      setUsername(updated.username);
      setCurrentPassword("");
      setNewPassword("");
      setNewPassword2("");

      setSuccess("Данные профиля обновлены");
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Ошибка при сохранении профиля");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white flex items-center justify-center px-4 py-8">
      <div className="max-w-xl w-full relative">
        <div className="pointer-events-none absolute -left-40 -top-40 h-72 w-72 rounded-full bg-sky-500/30 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 bottom-0 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />

        <div className="relative rounded-3xl bg-slate-900/80 border border-slate-700/70 shadow-2xl shadow-sky-900/40 px-6 py-7 md:px-8 md:py-8 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-sky-300/80 mb-1">
                Профиль администратора
              </div>
              <h1 className="text-xl md:text-2xl font-semibold">Настройки учётной записи</h1>
            </div>
            <button
              type="button"
              onClick={() => (window.location.href = "/admin")}
              className="text-xs rounded-full border border-slate-600/70 bg-slate-800/80 px-3 py-1.5 text-slate-200 hover:border-sky-500 hover:text-sky-100 transition"
            >
              ← Назад к настройкам системы
            </button>
          </div>

          {loading ? (
            <p className="text-sm text-slate-300 py-8">Загрузка профиля…</p>
          ) : (
            <>
              {error && (
                <div className="mb-3 rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                  {error}
                </div>
              )}
              {success && (
                <div className="mb-3 rounded-xl border border-emerald-500/60 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">
                  {success}
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-slate-200">Логин</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    placeholder="Логин администратора"
                  />
                  <p className="text-[11px] text-slate-400">Используется для входа в систему.</p>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-slate-200">Текущий пароль</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    placeholder="Введите текущий пароль"
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-1.5">
                    <label className="block text-xs font-medium text-slate-200">Новый пароль</label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                      placeholder="Оставьте пустым, если не меняете"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="block text-xs font-medium text-slate-200">
                      Повтор нового пароля
                    </label>
                    <input
                      type="password"
                      value={newPassword2}
                      onChange={(e) => setNewPassword2(e.target.value)}
                      className="w-full rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                      placeholder="Повторите новый пароль"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3">
                <p className="text-[11px] text-slate-400 max-w-xs">
                  После изменения логина или пароля не забудьте сообщить их только тем, кому нужен
                  доступ администратора.
                </p>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-slate-950 shadow-lg shadow-sky-500/40 hover:bg-sky-400 active:scale-[0.98] transition disabled:opacity-60"
                >
                  {saving ? "Сохранение…" : "Сохранить изменения"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminProfilePage;
