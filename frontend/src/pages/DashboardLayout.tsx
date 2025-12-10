import { Route, Routes } from "react-router-dom";
import { AdminSettingsPage } from "./AdminSettingsPage";

export function DashboardLayout() {
  return (
    <Routes>
      <Route path="/" element={<AdminSettingsPage />} />
    </Routes>
  );
}
