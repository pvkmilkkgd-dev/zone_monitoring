import { getCurrentUser, logout } from "./auth";
import { fetchZones, updateZoneState, Zone } from "./zonesApi";
import { fetchEvents, Event } from "./eventsApi";

const userInfoEl = document.getElementById("user-info") as HTMLDivElement | null;
const logoutBtn = document.getElementById("logout-btn") as HTMLButtonElement | null;
const zonesTableBody = document.querySelector(
  "#zones-table tbody"
) as HTMLTableSectionElement | null;
const eventsTableBody = document.querySelector(
  "#events-table tbody"
) as HTMLTableSectionElement | null;
const mainMessageEl = document.getElementById("main-message") as HTMLDivElement | null;

async function init() {
  try {
    const user = getCurrentUser();

    // Если не залогинен – отправляем на страницу логина
    if (!user) {
      window.location.href = "/login.html";
      return;
    }

    if (userInfoEl) {
      userInfoEl.textContent = `Пользователь: ${user.username} (роль: ${user.role})`;
    }

    if (logoutBtn) {
      logoutBtn.onclick = () => {
        logout();
        window.location.href = "/login.html";
      };
    }

    // Загружаем и рисуем зоны
    const zones = await fetchZones();
    renderZones(zones, user.role);

    // Загружаем и рисуем события
    const events = await fetchEvents();
    renderEvents(events);
  } catch (err) {
    console.error(err);
    if (mainMessageEl) {
      mainMessageEl.textContent =
        (err as Error).message || "Ошибка при загрузке данных";
    }
  }
}

function renderZones(zones: Zone[], role: "viewer" | "editor") {
  if (!zonesTableBody) return;
  zonesTableBody.innerHTML = "";

  zones.forEach((zone) => {
    const tr = document.createElement("tr");

    const idTd = document.createElement("td");
    idTd.textContent = String(zone.id);

    const nameTd = document.createElement("td");
    nameTd.textContent = zone.name;

    const activeTd = document.createElement("td");
    activeTd.textContent = zone.is_active ? "Да" : "Нет";

    const controlTd = document.createElement("td");
    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = zone.is_active ? "Отключить" : "Включить";

    if (role !== "editor") {
      toggleBtn.disabled = true;
      toggleBtn.title = "Недостаточно прав (нужна роль editor)";
    } else {
      toggleBtn.onclick = async () => {
        toggleBtn.disabled = true;
        try {
          const newState = !zone.is_active;
          await updateZoneState(zone.id, newState);
          zone.is_active = newState;
          activeTd.textContent = zone.is_active ? "Да" : "Нет";
          toggleBtn.textContent = zone.is_active ? "Отключить" : "Включить";
        } catch (err) {
          console.error(err);
          alert((err as Error).message || "Не удалось изменить состояние зоны");
        } finally {
          toggleBtn.disabled = false;
        }
      };
    }

    controlTd.appendChild(toggleBtn);

    tr.appendChild(idTd);
    tr.appendChild(nameTd);
    tr.appendChild(activeTd);
    tr.appendChild(controlTd);

    zonesTableBody.appendChild(tr);
  });
}

function renderEvents(events: Event[]) {
  if (!eventsTableBody) return;
  eventsTableBody.innerHTML = "";

  events.forEach((evt) => {
    const tr = document.createElement("tr");

    const idTd = document.createElement("td");
    idTd.textContent = String(evt.id);

    const zoneTd = document.createElement("td");
    zoneTd.textContent = `${evt.zone_name} (#${evt.zone_id})`;

    const typeTd = document.createElement("td");
    typeTd.textContent = evt.event_type;

    const timeTd = document.createElement("td");
    // тут можно красиво форматнуть дату
    timeTd.textContent = new Date(evt.created_at).toLocaleString();

    tr.appendChild(idTd);
    tr.appendChild(zoneTd);
    tr.appendChild(typeTd);
    tr.appendChild(timeTd);

    eventsTableBody.appendChild(tr);
  });
}

init().catch(console.error);
