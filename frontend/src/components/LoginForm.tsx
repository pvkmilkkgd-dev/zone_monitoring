import { FormEvent, useState } from "react";
import { loginRequest } from "../api/client";

type Props = {
  onSuccess: (token: string) => void;
};

export function LoginForm({ onSuccess }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const token = await loginRequest(username, password);
      onSuccess(token);
    } catch (err) {
      console.error(err);
      setError("Неверный логин или пароль, либо ошибка сервера");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Вход</h2>
      <form onSubmit={handleSubmit} className="form">
        <label className="form-label">
          Логин
          <input
            type="text"
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>

        <label className="form-label">
          Пароль
          <input
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {error && <div className="error-msg">{error}</div>}

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Вхожу..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
