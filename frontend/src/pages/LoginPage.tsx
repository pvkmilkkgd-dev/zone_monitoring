import React, { useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  margin: 0,
  padding: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background:
    "radial-gradient(circle at top left, #1d4ed8 0, #020617 40%), radial-gradient(circle at bottom right, #0ea5e9 0, #020617 45%)",
  backgroundColor: "#020617",
  fontFamily:
    'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  color: "#e5e7eb",
};

const cardStyle: React.CSSProperties = {
  position: "relative",
  width: "100%",
  maxWidth: 420,
  padding: "28px 28px 26px",
  borderRadius: 20,
  background:
    "linear-gradient(145deg, rgba(15,23,42,0.95), rgba(15,23,42,0.98))",
  border: "1px solid rgba(148,163,184,0.4)",
  boxShadow:
    "0 24px 60px rgba(15,23,42,0.95), 0 0 0 1px rgba(15,23,42,0.9)",
  backdropFilter: "blur(10px)",
};

const badgeStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "4px 10px",
  borderRadius: 999,
  border: "1px solid rgba(56,189,248,0.5)",
  background: "rgba(8,47,73,0.7)",
  fontSize: 10,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#e0f2fe",
  marginBottom: 10,
};

const titleStyle: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 600,
  margin: 0,
  color: "#e5e7eb",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#cbd5f5",
  marginTop: 6,
  marginBottom: 16,
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 500,
  color: "#e5e7eb",
  marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid rgba(148,163,184,0.7)",
  backgroundColor: "rgba(15,23,42,0.85)",
  color: "#e5e7eb",
  fontSize: 13,
  outline: "none",
  boxSizing: "border-box",
};

const inputWrapperStyle: React.CSSProperties = {
  marginBottom: 10,
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  marginTop: 8,
  padding: "10px 14px",
  borderRadius: 10,
  border: "none",
  background:
    "linear-gradient(135deg, #0ea5e9 0%, #1d4ed8 45%, #4f46e5 100%)",
  color: "white",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 14px 35px rgba(37,99,235,0.7)",
};

const errorBoxStyle: React.CSSProperties = {
  marginBottom: 10,
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid rgba(248,113,113,0.6)",
  backgroundColor: "rgba(127,29,29,0.8)",
  fontSize: 12,
  color: "#fee2e2",
};

const bulletListStyle: React.CSSProperties = {
  marginTop: 12,
  paddingLeft: 18,
  fontSize: 12,
  color: "#cbd5f5",
};

export default function LoginPage() {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!login.trim() || !password) {
      setError("Введите логин и пароль");
      return;
    }

    try {
      setIsSubmitting(true);

      const body = new URLSearchParams();
      body.append("username", login);
      body.append("password", password);

      const resp = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      if (!resp.ok) {
        if (resp.status === 401) {
          throw new Error("Неверный логин или пароль");
        }
        const data = await resp.json().catch(() => null);
        throw new Error(
          data?.detail ?? "Не удалось выполнить вход в систему"
        );
      }

      const data = await resp.json();
      if (data?.access_token) {
        localStorage.setItem("access_token", data.access_token);
      }

      window.location.href = "/admin";
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Ошибка при входе в систему");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <div style={badgeStyle}>Внутренний сервис</div>
        <h1 style={titleStyle}>Внутренний сервис мониторинга обстановки</h1>
        <p style={subtitleStyle}>
          Авторизуйтесь, чтобы получить доступ к панели мониторинга и
          данным. Доступ только для сотрудников.
        </p>

        {error && <div style={errorBoxStyle}>{error}</div>}

        <form onSubmit={handleLogin}>
          <div style={inputWrapperStyle}>
            <label style={labelStyle}>Логин</label>
            <input
              type="text"
              style={inputStyle}
              placeholder="Введите логин"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
            />
          </div>

          <div style={inputWrapperStyle}>
            <label style={labelStyle}>Пароль</label>
            <input
              type="password"
              style={inputStyle}
              placeholder="Введите пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" style={buttonStyle} disabled={isSubmitting}>
            {isSubmitting ? "Вход…" : "Войти"}
          </button>
        </form>

        <ul style={bulletListStyle}>
          <li>Оперативный контроль состояния обстановки</li>
          <li>История событий и журнал инцидентов</li>
          <li>Быстрая оценка обстановки по ключевым метрикам</li>
        </ul>
      </div>
    </div>
  );
}
