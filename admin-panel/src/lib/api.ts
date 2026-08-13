import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const api = axios.create({ baseURL: BASE });
api.interceptors.response.use((r) => r, (err) => Promise.reject(err));

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
export const getGroups = (status?: string, search?: string) =>
  api.get("/admin/groups", {
    params: { ...(status ? { status_filter: status } : {}), ...(search ? { search } : {}) },
  });
export const approveGroup = (chatId: number) => api.post(`/admin/groups/${chatId}/approve`);
export const rejectGroup  = (chatId: number) => api.post(`/admin/groups/${chatId}/reject`);

export const updateGroupMode = (chatId: number, mode: string) =>
  api.patch(`/admin/groups/${chatId}/mode`, { mode });
export const updateGroupSettings = (chatId: number, settings: { poster_auto_answer: boolean }) =>
  api.patch(`/admin/groups/${chatId}/settings`, settings);

export const getGroupRoles = (chatId: number) =>
  api.get(`/admin/groups/${chatId}/roles`);
export const updateUserRole = (chatId: number, userId: number, role: string) =>
  api.patch(`/admin/groups/${chatId}/roles/${userId}`, { role, is_manual_override: true });

export const getLearningFeed = (chatId: number) =>
  api.get(`/admin/groups/${chatId}/learning-feed`);
export const confirmLearningEntry = (chatId: number, entryId: number) =>
  api.post(`/admin/groups/${chatId}/learning-feed/${entryId}/confirm`);

export const getGroupDetailStats = (chatId: number, days = 30) =>
  api.get(`/admin/groups/${chatId}/stats`, { params: { days } });

// ── Stats ─────────────────────────────────────────────────────────────────────
export const getOverview  = () => api.get("/admin/stats/overview");
export const getTimeline  = (days = 7) => api.get("/admin/stats/timeline", { params: { days } });
export const getTopErrors = (limit = 10) => api.get("/admin/stats/top-errors", { params: { limit } });
export const getGroupStats = () => api.get("/admin/stats/groups");
