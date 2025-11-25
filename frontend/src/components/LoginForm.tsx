import { FormEvent, useState } from "react";
import { login } from "../api/auth";

type Props = {
  onLoggedIn?: () => void;
};

const LoginForm = ({ onLoggedIn }: Props) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login({ username, password });
      onLoggedIn?.();
    } catch (err) {
      setError("Не удалось войти. Проверьте логин/пароль.");
      console.error(err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4 w-full max-w-md">
      <div className="space-y-1">
        <label className="text-sm font-medium text-slate-700">Логин</label>
        <input
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="admin"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-slate-700">Пароль</label>
        <input
          type="password"
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••"
        />
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
      <button
        type="submit"
        className="w-full bg-primary text-white rounded-lg py-2 font-semibold hover:brightness-95 transition"
      >
        Войти
      </button>
      <p className="text-xs text-slate-500">
        Токен сохраняется в localStorage. После добавления реального API добавить логику обновления токена.
      </p>
    </form>
  );
};

export default LoginForm;
