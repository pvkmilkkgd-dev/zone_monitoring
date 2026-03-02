import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("zone_jwt");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Sliding window: подхватываем обновлённый токен из заголовка ответа.
// Бэкенд при каждом успешном запросе продлевает токен на 2 часа
// от текущего момента (а не от момента логина).
api.interceptors.response.use((response) => {
  const newToken = response.headers["x-new-token"];
  if (newToken) {
    localStorage.setItem("zone_jwt", newToken);
  }
  return response;
});

export default api;
