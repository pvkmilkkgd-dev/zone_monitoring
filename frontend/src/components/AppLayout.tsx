// src/components/AppLayout.tsx
import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { clearAuth, getCurrentUserName, getCurrentUserRole } from "../auth";

type Props = {
  children: ReactNode;
};

export function AppLayout({ children }: Props) {
  const username = getCurrentUserName();
  const role = getCurrentUserRole();

  function handleLogout() {
    clearAuth();
    window.location.href = "/login";
  }

  return (
    <div>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          borderBottom: "1px solid #ddd",
        }}
      >
        <div>
          <strong>Zone Monitoring</strong>{" "}
          <span style={{ opacity: 0.7 }}>— панель мониторинга зон</span>
        </div>

        <nav style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link to="/">Главная</Link>
          <Link to="/maps">Карты</Link>
          <Link to="/events">События</Link>

          <span style={{ marginLeft: 16, fontSize: 14, opacity: 0.8 }}>
            {username && (
              <>
                {username} ({role})
              </>
            )}
          </span>

          <button onClick={handleLogout} style={{ marginLeft: 8 }}>
            Выйти
          </button>
        </nav>
      </header>

      <main style={{ padding: "16px" }}>{children}</main>
    </div>
  );
}
