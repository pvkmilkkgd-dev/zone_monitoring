// src/pages/EventsPage.tsx
import { useEffect, useState } from "react";
import { fetchEvents, ZoneEvent } from "../api";
import { getCurrentUser, getCurrentUserRole } from "../auth";

function StatusBadge({ status }: { status: string }) {
  let color = "#4caf50";
  let label = "Норма";

  if (status === "warning") {
    color = "#ff9800";
    label = "Внимание";
  } else if (status === "alert") {
    color = "#f44336";
    label = "Тревога";
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "2px 8px",
        borderRadius: 999,
        backgroundColor: "#f5f5f5",
        fontSize: 12,
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          backgroundColor: color,
        }}
      />
      {label}
    </span>
  );
}

export function EventsPage() {
  const [events, setEvents] = useState<ZoneEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const user = getCurrentUser();
  const role = getCurrentUserRole();

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchEvents();
        setEvents(data);
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Ошибка загрузки событий");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (!user) {
    return <p>Для просмотра событий войдите в систему.</p>;
  }

  return (
    <div>
      <h2>События по зонам</h2>
      <p style={{ fontSize: 14, opacity: 0.8 }}>
        Здесь отображаются изменения, из-за которых менялась заливка зон на карте.
        Ваша роль: <strong>{role ?? "не определена"}</strong>.
      </p>

      {loading && <p>Загрузка событий…</p>}
      {error && <p style={{ color: "red" }}>Ошибка: {error}</p>}

      {!loading && !error && events.length === 0 && <p>Событий пока нет.</p>}

      {!loading && !error && events.length > 0 && (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 14,
            marginTop: 8,
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Время
              </th>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Карта
              </th>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Зона
              </th>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Статус
              </th>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Событие / причина
              </th>
            </tr>
          </thead>
          <tbody>
            {events.map((ev) => (
              <tr key={ev.id}>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                    whiteSpace: "nowrap",
                  }}
                >
                  {ev.created_at}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  {ev.map_name}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  {ev.zone_name}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  <StatusBadge status={ev.status} />
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  <strong>{ev.title}</strong>
                  <div style={{ fontSize: 13, opacity: 0.85 }}>{ev.description}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
