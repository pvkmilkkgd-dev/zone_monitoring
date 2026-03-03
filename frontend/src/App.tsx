import React, { useEffect, useState } from "react";
import LoginPage from "./pages/LoginPage";
import SetupPage from "./pages/SetupPage";
import AdminProfilePage from "./pages/AdminProfilePage";
import { AdminSettingsPage } from "./pages/AdminSettingsPage";
import { UsersPage } from "./pages/UsersPage";
import { ZonesAndDevicesPage } from "./pages/ZonesAndDevicesPage";
import { LayersPage } from "./pages/LayersPage";
import { EventsPage } from "./pages/EventsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SituationPage } from "./pages/SituationPage";
import { JournalPage } from "./pages/JournalPage";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function App() {
  const path = window.location.pathname;
  const [bootstrapChecked, setBootstrapChecked] = useState(false);
  const [needsBootstrap, setNeedsBootstrap] = useState(false);

  useEffect(() => {
    let alive = true;

    const checkBootstrap = async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/v1/auth/bootstrap-status`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!alive) return;
        setNeedsBootstrap(Boolean(data?.needs_bootstrap));
      } catch {
        if (!alive) return;
        // Если статус не удалось получить, не блокируем приложение.
        setNeedsBootstrap(false);
      } finally {
        if (alive) setBootstrapChecked(true);
      }
    };

    checkBootstrap();
    return () => {
      alive = false;
    };
  }, []);

  if (!bootstrapChecked) return null;

  if (needsBootstrap && path !== "/setup") {
    window.location.href = "/setup";
    return null;
  }

  if (!needsBootstrap && path === "/setup") {
    window.location.href = "/";
    return null;
  }

  if (path === "/setup") return <SetupPage />;
  if (path === "/admin/profile") return <AdminProfilePage />;
  if (path === "/admin/users" || path === "/admin/users/") return <UsersPage />;
  if (path === "/admin/zones" || path === "/admin/zones/") return <ZonesAndDevicesPage />;
  if (path === "/editor/layers" || path === "/editor/layers/") return <LayersPage />;
  if (path === "/editor/events" || path === "/editor/events/") return <EventsPage />;
  if (path === "/editor/reports" || path === "/editor/reports/") return <ReportsPage />;
  if (path === "/situation" || path === "/situation/") return <SituationPage />;
  if (path === "/admin/journal" || path === "/admin/journal/") return <JournalPage />;

  // 🔥 ВАЖНО: делаем /admin и /admin/ одинаковыми
  if (path === "/admin" || path === "/admin/") {
    return <AdminSettingsPage />;
  }

  return <LoginPage />;
}

export default App;
