// src/pages/MapsPage.tsx
import { getCurrentUserRole } from "../auth";

type ZoneStatus = "ok" | "warning" | "alert";

type Zone = {
  id: number;
  name: string;
  status: ZoneStatus;
  lastEvent: string;
  lastUpdated: string;
};

const mockZones: Zone[] = [
  {
    id: 1,
    name: "Зона 1 — Север",
    status: "ok",
    lastEvent: "Параметры в норме",
    lastUpdated: "30.11.2025 18:20",
  },
  {
    id: 2,
    name: "Зона 2 — Центр",
    status: "warning",
    lastEvent: "Рост значения критерия «Нагрузка»",
    lastUpdated: "30.11.2025 18:05",
  },
  {
    id: 3,
    name: "Зона 3 — Юг",
    status: "alert",
    lastEvent: "Превышен порог по критерию «Инциденты»",
    lastUpdated: "30.11.2025 17:50",
  },
];

function ZoneStatusBadge({ status }: { status: ZoneStatus }) {
  let color = "#4caf50";
  let label = "Норма";

  if (status === "warning") {
    color = "#ff9800";
    label = "Внимание";
  }

  if (status === "alert") {
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

export function MapsPage() {
  const role = getCurrentUserRole(); // "admin" | "editor" | "viewer" | null
  const canEdit = role === "admin" || role === "editor";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1.5fr", gap: 24 }}>
      {/* Левая часть — карта */}
      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
          minHeight: 400,
          background:
            "repeating-linear-gradient(45deg, #fafafa, #fafafa 10px, #f0f0f0 10px, #f0f0f0 20px)",
        }}
      >
        <div
          style={{
            marginBottom: 12,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0 }}>Карта региона</h2>

          {canEdit && (
            <div style={{ display: "flex", gap: 8 }}>
              <button>Загрузить карту</button>
              <button>Настроить зоны</button>
            </div>
          )}
        </div>

        <p style={{ marginTop: 0, fontSize: 14, opacity: 0.8 }}>
          Здесь позже будет реальное картографическое изображение, разбитое на зоны.
          Сейчас это просто заглушка, чтобы настроить структуру интерфейса.
        </p>

        <div
          style={{
            marginTop: 16,
            borderRadius: 8,
            border: "1px dashed #bbb",
            height: 300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#888",
            fontSize: 14,
            textAlign: "center",
            padding: 16,
          }}
        >
          Область для карты.  
          Сюда мы позже добавим:
          <ul style={{ textAlign: "left", marginTop: 8 }}>
            <li>подложку-изображение (PNG/JPEG);</li>
            <li>полигональные зоны;</li>
            <li>заливку по интенсивности критериев;</li>
            <li>подсказки при клике по зоне.</li>
          </ul>
        </div>
      </section>

      {/* Правая часть — список зон */}
      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
          minHeight: 400,
          backgroundColor: "#fff",
        }}
      >
        <div
          style={{
            marginBottom: 12,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0 }}>Зоны на карте</h2>

          {canEdit && (
            <button>Добавить зону</button>
          )}
        </div>

        {role === "viewer" && (
          <p style={{ fontSize: 13, opacity: 0.8 }}>
            У вас роль <strong>просмотр</strong>: вы можете контролировать ситуацию по зонам
            и смотреть причины изменений, но не можете редактировать карту и критерии.
          </p>
        )}

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
                Последнее изменение
              </th>
              <th
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #ddd",
                  padding: "4px 8px",
                }}
              >
                Обновлено
              </th>
            </tr>
          </thead>
          <tbody>
            {mockZones.map((zone) => (
              <tr key={zone.id}>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  {zone.name}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  <ZoneStatusBadge status={zone.status} />
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  {zone.lastEvent}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    borderBottom: "1px solid #f0f0f0",
                    whiteSpace: "nowrap",
                  }}
                >
                  {zone.lastUpdated}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
