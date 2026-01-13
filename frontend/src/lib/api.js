const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export const apiFetch = async (path, options = {}) => {
  const { method = "GET", body, token } = options;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = payload.error || "request_failed";
    throw new Error(message);
  }

  return payload;
};
