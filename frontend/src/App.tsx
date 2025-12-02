import { Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { EventsPage } from "./pages/EventsPage";
import { clearAuth, getCurrentUser } from "./auth";

export default function App() {
  const user = getCurrentUser();

  return (
    <div>
      <header
        style={{
          padding: "8px 16px",
          borderBottom: "1px solid #ddd",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <a href="/" style={{ fontWeight: 600, marginRight: 16 }}>
            Zone Monitoring
          </a>
          <a href="/events" style={{ marginRight: 12 }}>
            События
          </a>
        </div>

        <div style={{ fontSize: 14 }}>
          {user ? (
            <>
              <span style={{ marginRight: 8 }}>Привет, {user.username}</span>
              <button
                onClick={() => {
                  clearAuth();
                  window.location.href = "/login";
                }}
              >
                Выйти
              </button>
            </>
          ) : (
            <>
              <a href="/login" style={{ marginRight: 8 }}>
                Вход
              </a>
              <a href="/register">Регистрация</a>
            </>
          )}
        </div>
      </header>

      <main style={{ padding: "16px" }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/events" element={<EventsPage />} />
        </Routes>
      </main>
    </div>
  );
}
