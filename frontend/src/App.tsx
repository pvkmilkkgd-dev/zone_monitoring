import React from "react";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import SetupPage from "./pages/SetupPage";
import AdminProfilePage from "./pages/AdminProfilePage";
import { AdminSettingsPage } from "./pages/AdminSettingsPage";
import { UsersPage } from "./pages/UsersPage";

function App() {
  const path = window.location.pathname;

  if (path === "/setup") return <SetupPage />;
  if (path === "/admin/profile") return <AdminProfilePage />;
  if (path === "/admin/users" || path === "/admin/users/") return <UsersPage />;

  // 🔥 ВАЖНО: делаем /admin и /admin/ одинаковыми
  if (path === "/admin" || path === "/admin/") {
    return <AdminSettingsPage />;
  }

  return <LoginPage />;
}

export default App;
