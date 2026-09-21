const API_BASE = (
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const TOKEN_KEY = "fastapi_react_token";

export { API_BASE };

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, form, token } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (body instanceof FormData) {
    payload = body;
  } else if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
  });

  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await res.json()
    : null;

  if (!res.ok) {
    let message = `请求失败（HTTP ${res.status}）`;
    if (data?.message) message = data.message;
    else if (Array.isArray(data?.detail)) {
      message = data.detail.map((item) => item.msg || JSON.stringify(item)).join("；");
    } else if (data?.detail) message = data.detail;
    throw new Error(message);
  }
  return data;
}

export const api = {
  health: () => request("/"),
  jsonDemo: () => request("/json"),
  register: (payload) => request("/users/register", { method: "POST", body: payload }),
  login: (username, password) =>
    request("/auth/login", { method: "POST", form: { username, password } }),
  me: (token) => request("/users/me", { token }),
  listUsers: (page = 1, size = 10) => request(`/users?page=${page}&size=${size}`),
  listItems: (page = 1, size = 10) => request(`/items?page=${page}&size=${size}`),
  createItem: (token, payload) =>
    request("/items", { method: "POST", body: payload, token }),
  updateItem: (token, id, payload) =>
    request(`/items/${id}`, { method: "PUT", body: payload, token }),
  deleteItem: (token, id) => request(`/items/${id}`, { method: "DELETE", token }),
  upload: (username, file) => {
    const fd = new FormData();
    fd.append("username", username);
    fd.append("file", file);
    return request("/upload", { method: "POST", body: fd });
  },
  sendEmail: (email) => request("/send", { method: "POST", form: { email } }),
};
