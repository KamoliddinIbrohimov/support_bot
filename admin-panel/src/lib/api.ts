import axios from "axios";
import Cookies from "js-cookie";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: BASE });

api.interceptors.request.use((config) => {
  const token = Cookies.get("admin_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 || err.response?.status === 403) {
      Cookies.remove("admin_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (username: string, password: string) =>
  api.post("/admin/auth/login", { username, password });

// ── Errors ────────────────────────────────────────────────────────────────────
export const getErrors = (page = 1, pageSize = 20, search = "") =>
  api.get("/admin/errors", { params: { page, page_size: pageSize, search: search || undefined } });

export const createError = (data: unknown) => api.post("/admin/errors", data);
export const updateError = (id: number, data: unknown) => api.put(`/admin/errors/${id}`, data);
export const deleteError = (id: number) => api.delete(`/admin/errors/${id}`);

// ── Groups ────────────────────────────────────────────────────────────────────
export const getGroups = (status?: string) =>
  api.get("/admin/groups", { params: status ? { status_filter: status } : {} });

export const approveGroup = (chatId: number) => api.post(`/admin/groups/${chatId}/approve`);
export const rejectGroup = (chatId: number) => api.post(`/admin/groups/${chatId}/reject`);

// ── Stats ─────────────────────────────────────────────────────────────────────
export const getOverview = () => api.get("/admin/stats/overview");
export const getTimeline = (days = 7) => api.get("/admin/stats/timeline", { params: { days } });
export const getTopErrors = (limit = 10) => api.get("/admin/stats/top-errors", { params: { limit } });
export const getGroupStats = () => api.get("/admin/stats/groups");
