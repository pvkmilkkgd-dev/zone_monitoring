import React from "react";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import SetupPage from "./pages/SetupPage";

function App() {
  const path = window.location.pathname;

  if (path === "/setup") {
    return <SetupPage />;
  }

  if (path === "/admin") {
    return <AdminPage />;
  }

  return <LoginPage />;
}

export default App;
