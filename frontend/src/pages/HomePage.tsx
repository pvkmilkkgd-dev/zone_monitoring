// src/pages/HomePage.tsx
import { useEffect, useState } from "react";
import { fetchEvents, ZoneEvent } from "../api";
import { getCurrentUser, getCurrentUserRole } from "../auth";

function StatusDot({ status }: { status: string }) {
  let color = "#4caf50";

  if (status === "warning") color = "#ff9800";
  if (status === "alert") color = "#f44336";

  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: color,
        marginRight: 6,
      }}
    />
  );
}

export function HomePage() {
  const user = getCurrentUser();
  const role = getCurrentUserRole();

  const [events, setEvents] = useState<ZoneEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchEvents();
        setEvents(data.slice(0, 5));
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Ошибка загрузки событий");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [user]);

  if (!user) {
    return (
      <div>
        <h2>Добро пожаловать в Zone Monitoring</h2>
        <p style={{ maxWidth: 600 }}>
          Это система контроля зон. Обычные пользователи видят текущий статус зон и события,
          которые привели к изменению заливки (например, превышение порога по нагрузке или
          инцидентам).
        </p>
        <p>
          Чтобы начать работу, <a href="/login">войдите в систему</a> или{" "}
          <a href="/register">зарегистрируйтесь</a>.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2>Обзор зон</h2>
      <p style={{ fontSize: 14, opacity: 0.8 }}>
        Пользователь: <strong>{user.username}</strong> · Роль:{" "}
        <strong>{role ?? "не определена"}</strong>
      </p>

      <p style={{ marginTop: 12 }}>
        Ниже — последние события по зонам. Для полного списка откройте страницу{" "}
        <a href="/events">«События»</a>.
      </p>

      {loading && <p>Загрузка событий…</p>}
      {error && <p style={{ color: "red" }}>Ошибка: {error}</p>}

      {!loading && !error && events.length === 0 && <p>Событий пока нет — все зоны в норме.</p>}

      {!loading && !error && events.length > 0 && (
        <ul style={{ listStyle: "none", paddingLeft: 0, marginTop: 12 }}>
          {events.map((ev) => (
            <li
              key={ev.id}
              style={{
                border: "1px solid #e0e0e0",
                borderRadius: 8,
                padding: "8px 10px",
                marginBottom: 8,
              }}
            >
              <div style={{ fontSize: 13, opacity: 0.7 }}>
                {ev.created_at} · {ev.map_name} · {ev.zone_name}
              </div>
              <div style={{ marginTop: 4 }}>
                <StatusDot status={ev.status} />
                <strong>{ev.title}</strong>
              </div>
              <div style={{ fontSize: 13, marginTop: 2 }}>{ev.description}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
