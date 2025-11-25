import api from "../utils/http";

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  role?: string;
};

export const login = async (payload: LoginRequest) => {
  const params = new URLSearchParams();
  params.append("username", payload.username);
  params.append("password", payload.password);

  const { data } = await api.post<LoginResponse>("/auth/login", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  localStorage.setItem("zone_jwt", data.access_token);
  if (data.role) {
    localStorage.setItem("zone_role", data.role);
  }
  return data;
};

