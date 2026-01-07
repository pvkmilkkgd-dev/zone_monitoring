import React from "react";
import { AdminSettingsPage } from "./AdminSettingsPage";

function AdminPage() {
  // Показываем только страницу настроек системы, без кнопки "Настройки администратора"
  return <AdminSettingsPage />;
}

export default AdminPage;
