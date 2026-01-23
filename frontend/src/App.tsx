import React from "react";
import AdminPage from "./pages/AdminPage";
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

function App() {
  const path = window.location.pathname;

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
