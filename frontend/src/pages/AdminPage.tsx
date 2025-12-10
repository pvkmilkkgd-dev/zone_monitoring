import React, { useEffect, useState } from "react";

import { RegionsMultiSelect } from "@/components/admin/RegionsMultiSelect";

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
  maxWidth: 780,
  padding: "26px 26px 24px",
  borderRadius: 20,
  background:
    "linear-gradient(145deg, rgba(15,23,42,0.95), rgba(15,23,42,0.98))",
  border: "1px solid rgba(148,163,184,0.4)",
  boxShadow:
    "0 24px 60px rgba(15,23,42,0.95), 0 0 0 1px rgba(15,23,42,0.9)",
  backdropFilter: "blur(10px)",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: 14,
};

const appTitleStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 600,
  color: "#e5e7eb",
};

const appSubtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#cbd5f5",
  marginTop: 4,
};

const tagStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 10px",
  borderRadius: 999,
  border: "1px solid rgba(94,234,212,0.6)",
  backgroundColor: "rgba(15,118,110,0.35)",
  color: "#ccfbf1",
};

const mainRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "220px 1fr",
  gap: 18,
};

const sidebarStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 14,
  backgroundColor: "rgba(15,23,42,0.9)",
  border: "1px solid rgba(51,65,85,0.9)",
};

const sidebarTitleStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#9ca3af",
  marginBottom: 8,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
};

const sidebarButtonStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "left" as const,
  padding: "7px 9px",
  borderRadius: 10,
  border: "none",
  backgroundColor: "transparent",
  color: "#e5e7eb",
  fontSize: 13,
  cursor: "pointer",
};

const sidebarButtonActiveStyle: React.CSSProperties = {
  ...sidebarButtonStyle,
  background:
    "linear-gradient(135deg, rgba(37,99,235,0.85), rgba(59,130,246,0.9))",
};

const contentCardStyle: React.CSSProperties = {
  padding: 14,
  borderRadius: 14,
  backgroundColor: "rgba(15,23,42,0.9)",
  border: "1px solid rgba(51,65,85,0.9)",
};

const contentTitleStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  marginBottom: 4,
};

const contentSubtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#cbd5f5",
  marginBottom: 14,
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 500,
  color: "#e5e7eb",
  marginBottom: 4,
};

const fieldWrapperStyle: React.CSSProperties = {
  marginBottom: 12,
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
};

const saveButtonStyle: React.CSSProperties = {
  marginTop: 12,
  padding: "8px 14px",
  borderRadius: 10,
  border: "none",
  background:
    "linear-gradient(135deg, #22c55e 0%, #16a34a 40%, #15803d 100%)",
  color: "white",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 14px 35px rgba(22,163,74,0.7)",
};

const infoRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 10,
  marginTop: 12,
  fontSize: 11,
  color: "#9ca3af",
};

const infoBadgeStyle: React.CSSProperties = {
  padding: "4px 8px",
  borderRadius: 999,
  backgroundColor: "rgba(31,41,55,0.9)",
  border: "1px solid rgba(55,65,81,0.95)",
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

const successBoxStyle: React.CSSProperties = {
  marginBottom: 10,
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid rgba(52,211,153,0.7)",
  backgroundColor: "rgba(6,95,70,0.8)",
  fontSize: 12,
  color: "#bbf7d0",
};

export default function AdminPage() {
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/login";
    }
  }, []);

  const [managementName, setManagementName] = useState("");
  const [regions, setRegions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("system_settings");
      if (!raw) return;

      const parsed = JSON.parse(raw);

      if (parsed.managementName) {
        setManagementName(parsed.managementName);
      }

      if (Array.isArray(parsed.regions)) {
        setRegions(parsed.regions.filter((r: any) => typeof r === "string"));
      } else if (typeof parsed.region === "string" && parsed.region) {
        setRegions([parsed.region]);
      }
    } catch {
      // ignore
    }
  }, []);

  const handleSave = async () => {
    setError(null);
    setSuccess(null);

    if (!managementName.trim()) {
      setError("Введите название вашего управления");
      return;
    }

    if (regions.length === 0) {
      setError("Выберите хотя бы один регион России");
      return;
    }

    try {
      setSaving(true);

      const payload = {
        managementName: managementName.trim(),
        regions,
      };

      localStorage.setItem("system_settings", JSON.stringify(payload));

      setSuccess("Настройки сохранены.");
    } catch (e) {
      console.error(e);
      setError("Не удалось сохранить настройки");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <div style={headerRowStyle}>
          <div>
            <div
              style={{
                fontSize: 11,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "#9ca3af",
                marginBottom: 3,
              }}
            >
              ZM · Admin
            </div>
            <div style={appTitleStyle}>Настройки системы</div>
            <div style={appSubtitleStyle}>
              Конфигурация регионов, названия вашего управления и базовых
              параметров работы сервиса.
            </div>
          </div>
          <div style={tagStyle}>Режим администратора</div>
        </div>

        <div style={mainRowStyle}>
          <aside style={sidebarStyle}>
            <div style={sidebarTitleStyle}>Разделы</div>
            <button style={sidebarButtonActiveStyle}>Общие настройки</button>
            <button style={sidebarButtonStyle} disabled>
              Регионы и объекты (скоро)
            </button>
            <button style={sidebarButtonStyle} disabled>
              Пользователи и роли (скоро)
            </button>
          </aside>

          <section style={contentCardStyle}>
            <h2 style={contentTitleStyle}>Общие настройки</h2>
            <p style={contentSubtitleStyle}>
              Укажите название вашего управления и выберите один или несколько регионов, за которые
              отвечает система мониторинга.
            </p>

            {error && <div style={errorBoxStyle}>{error}</div>}
            {success && <div style={successBoxStyle}>{success}</div>}

            <div style={fieldWrapperStyle}>
              <label style={labelStyle}>Название вашего управления</label>
              <input
                type="text"
                style={inputStyle}
                placeholder="Например: Центр мониторинга обстановки города Первоуральска"
                value={managementName}
                onChange={(e) => setManagementName(e.target.value)}
              />
            </div>

            <div className="mt-4">
              <label style={labelStyle}>Регионы России (можно выбрать несколько)</label>
              <div className="mt-2 rounded-xl border border-slate-200 bg-white p-3">
                <RegionsMultiSelect value={regions} onChange={setRegions} />
              </div>
            </div>

            <button
              type="button"
              style={saveButtonStyle}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Сохранение…" : "Сохранить настройки"}
            </button>

            <div style={infoRowStyle}>
              <div style={infoBadgeStyle}>Оперативный контроль состояния обстановки</div>
              <div style={infoBadgeStyle}>История событий и журнал инцидентов</div>
              <div style={infoBadgeStyle}>Быстрая оценка по ключевым метрикам</div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
