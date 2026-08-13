"use client";
import React, { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import {
  getGroups, approveGroup, rejectGroup,
  getGroupDetailStats, updateGroupMode, updateGroupSettings,
  getGroupRoles, updateUserRole, getLearningFeed, confirmLearningEntry,
} from "@/lib/api";
import type { Group, GroupDetailStats, GroupUserRole, LearningFeedEntry } from "@/lib/types";
import { CheckCircle, XCircle, Clock, X, ChevronRight } from "lucide-react";
import {
  AreaChart, Area, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type Filter  = "all" | "pending" | "approved" | "rejected";
type PanelTab = "stats" | "settings" | "roles" | "feed";

const TOOLTIP_STYLE = {
  backgroundColor: "#17171a", border: "1px solid #26262b",
  borderRadius: 8, color: "#f2f2f3", fontSize: 12,
};

const BOT_MODES = [
  { key: "learning",  label: "O'qish",  desc: "Kuzatish va o'rganish",  icon: "🔍" },
  { key: "knowledge", label: "Bilim",   desc: "KB → AI → Escalation",   icon: "📚" },
  { key: "express",   label: "Express", desc: "Darhol tahlil va javob",  icon: "⚡" },
] as const;

const ROLE_META: Record<string, { label: string; cls: string }> = {
  poster_staff:  { label: "Poster staff",        cls: "bg-purple-900/25 text-purple-300 border-purple-800/30" },
  plugin_staff:  { label: "Plugin staff",        cls: "bg-blue-900/25 text-blue-300 border-blue-800/30" },
  communicator:  { label: "Communicator",        cls: "bg-orange-900/25 text-orange-300 border-orange-800/30" },
  customer:      { label: "Mijoz",               cls: "bg-card2 text-dim border-rim" },
};

// ── Shared small components ───────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    pending:  { label: "Kutmoqda",     cls: "bg-amber-900/25 text-amber-300 border-amber-800/30", icon: <Clock size={11} /> },
    approved: { label: "Tasdiqlangan", cls: "bg-green-900/25 text-green-300 border-green-800/30", icon: <CheckCircle size={11} /> },
    rejected: { label: "Rad etilgan",  cls: "bg-red-900/25 text-red-300 border-red-800/30",       icon: <XCircle size={11} /> },
  };
  const s = map[status] ?? { label: status, cls: "bg-card2 text-dim border-rim", icon: null };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border ${s.cls}`}>
      {s.icon}{s.label}
    </span>
  );
}

function RoleBadge({ role }: { role: string }) {
  const r = ROLE_META[role] ?? { label: role, cls: "bg-card2 text-dim border-rim" };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${r.cls}`}>{r.label}</span>
  );
}

function MiniStat({ label, value, color = "text-ink" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-page border border-rim rounded-lg p-3">
      <p className="text-xs text-dim">{label}</p>
      <p className={`text-xl font-bold mt-0.5 ${color}`}>{value}</p>
    </div>
  );
}

function Toggle({ value, onChange, disabled }: { value: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onChange}
      disabled={disabled}
      className={`relative w-10 h-6 rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed ${
        value ? "bg-ac" : "bg-rim"
      }`}
    >
      <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${
        value ? "translate-x-5" : "translate-x-1"
      }`} />
    </button>
  );
}

// ── Group Detail Panel ────────────────────────────────────────────────────────

function GroupDetailPanel({
  group,
  onClose,
  onApprove,
  onReject,
}: {
  group: Group;
  onClose: () => void;
  onApprove: (id: number) => Promise<void>;
  onReject:  (id: number) => Promise<void>;
}) {
  const [activeTab, setActiveTab]         = useState<PanelTab>("stats");
  const [acting, setActing]               = useState(false);
  const [currentStatus, setCurrentStatus] = useState(group.status);

  // Stats tab
  const [stats, setStats]         = useState<GroupDetailStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Settings tab
  const [currentMode, setCurrentMode]           = useState<string>(group.bot_mode ?? "knowledge");
  const [posterAutoAnswer, setPosterAutoAnswer]  = useState<boolean>(group.poster_auto_answer ?? false);
  const [savingMode, setSavingMode]             = useState(false);
  const [savingPoster, setSavingPoster]         = useState(false);

  // Roles tab
  const [roles, setRoles]       = useState<GroupUserRole[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesLoaded, setRolesLoaded]   = useState(false);

  // Feed tab
  const [feed, setFeed]         = useState<LearningFeedEntry[]>([]);
  const [feedLoading, setFeedLoading] = useState(false);
  const [feedLoaded, setFeedLoaded]   = useState(false);

  // Fetch stats on mount
  useEffect(() => {
    setStatsLoading(true);
    getGroupDetailStats(group.chat_id)
      .then((r) => setStats(r.data))
      .catch(() => null)
      .finally(() => setStatsLoading(false));
  }, [group.chat_id]);

  const handleTabChange = (tab: PanelTab) => {
    setActiveTab(tab);
    if (tab === "roles" && !rolesLoaded) {
      setRolesLoading(true);
      getGroupRoles(group.chat_id)
        .then((r) => setRoles(r.data))
        .catch(() => null)
        .finally(() => { setRolesLoading(false); setRolesLoaded(true); });
    }
    if (tab === "feed" && !feedLoaded) {
      setFeedLoading(true);
      getLearningFeed(group.chat_id)
        .then((r) => setFeed(r.data))
        .catch(() => null)
        .finally(() => { setFeedLoading(false); setFeedLoaded(true); });
    }
  };

  const handleAction = async (fn: () => Promise<void>, newStatus: string) => {
    setActing(true);
    await fn().catch(() => null);
    setCurrentStatus(newStatus as Group["status"]);
    setActing(false);
  };

  const handleModeChange = async (mode: string) => {
    setCurrentMode(mode);
    setSavingMode(true);
    await updateGroupMode(group.chat_id, mode).catch(() => null);
    setSavingMode(false);
  };

  const handleTogglePoster = async () => {
    const next = !posterAutoAnswer;
    setPosterAutoAnswer(next);
    setSavingPoster(true);
    await updateGroupSettings(group.chat_id, { poster_auto_answer: next }).catch(() => null);
    setSavingPoster(false);
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    setRoles((prev) =>
      prev.map((r) =>
        r.telegram_user_id === userId
          ? { ...r, role: newRole as GroupUserRole["role"], is_manual_override: true }
          : r
      )
    );
    await updateUserRole(group.chat_id, userId, newRole).catch(() => null);
  };

  const handleConfirm = async (entryId: number) => {
    setFeed((prev) => prev.map((e) => e.id === entryId ? { ...e, is_confirmed: true } : e));
    await confirmLearningEntry(group.chat_id, entryId).catch(() => null);
  };

  const TABS: { key: PanelTab; label: string }[] = [
    { key: "stats",    label: "Statistika" },
    { key: "settings", label: "Sozlamalar" },
    { key: "roles",    label: "Ishtirokchilar" },
    { key: "feed",     label: "O'qish rejimi" },
  ];

  return (
    <>
      <div className="fixed inset-0 z-30 bg-black/60" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-[520px] max-w-[95vw] z-40 bg-card border-l border-rim flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-rim shrink-0">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-ink truncate">
              {group.title ?? `Chat ${group.chat_id}`}
            </h2>
            {group.username && <p className="text-xs text-dim mt-0.5">@{group.username}</p>}
            <p className="text-xs text-dim/50 font-mono mt-0.5">{group.chat_id}</p>
          </div>
          <button onClick={onClose} className="ml-4 text-dim hover:text-ink transition-colors shrink-0">
            <X size={20} />
          </button>
        </div>

        {/* Action row */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-rim shrink-0 flex-wrap">
          <StatusBadge status={currentStatus} />
          {currentStatus !== "approved" && (
            <button onClick={() => handleAction(() => onApprove(group.chat_id), "approved")} disabled={acting}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-green-300 bg-green-900/20 border border-green-800/30 hover:bg-green-900/35 rounded-lg disabled:opacity-50 transition-colors">
              <CheckCircle size={12} /> Tasdiqlash
            </button>
          )}
          {currentStatus !== "rejected" && (
            <button onClick={() => handleAction(() => onReject(group.chat_id), "rejected")} disabled={acting}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-400 bg-red-900/20 border border-red-800/30 hover:bg-red-900/35 rounded-lg disabled:opacity-50 transition-colors">
              <XCircle size={12} /> Rad etish
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-rim shrink-0 px-2">
          {TABS.map(({ key, label }) => (
            <button key={key} onClick={() => handleTabChange(key)}
              className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === key
                  ? "border-ac text-ac"
                  : "border-transparent text-dim hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">

          {/* ── Stats tab ── */}
          {activeTab === "stats" && (
            <div className="p-6 space-y-6">
              {statsLoading ? (
                <p className="text-dim text-sm text-center py-8">Yuklanmoqda…</p>
              ) : !stats ? (
                <p className="text-dim text-sm text-center py-8">Ma&apos;lumot yo&apos;q</p>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <MiniStat label="Jami savollar"   value={stats.total_questions} />
                    <MiniStat label="Hal etish %"      value={`${stats.resolution_rate}%`} />
                    <MiniStat label="AI hal etdi"      value={stats.resolved_by_ai}      color="text-ac" />
                    <MiniStat label="Support hal etdi" value={stats.resolved_by_support} color="text-blue-400" />
                  </div>

                  {stats.total_questions > 0 && (
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs text-dim">
                        <span>Hal etilgan</span>
                        <span>{stats.resolved_by_ai + stats.resolved_by_support} / {stats.total_questions}</span>
                      </div>
                      <div className="h-2 bg-card2 rounded-full overflow-hidden flex">
                        <div className="h-full bg-ac" style={{ width: `${(stats.resolved_by_ai / stats.total_questions) * 100}%` }} />
                        <div className="h-full bg-blue-500" style={{ width: `${(stats.resolved_by_support / stats.total_questions) * 100}%` }} />
                      </div>
                      <div className="flex gap-4 text-xs text-dim">
                        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-ac inline-block" />AI</span>
                        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />Support</span>
                      </div>
                    </div>
                  )}

                  {stats.top_errors.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-dim uppercase tracking-wide mb-3">Top xatolar</p>
                      <div className="space-y-1.5">
                        {stats.top_errors.map((e, i) => (
                          <div key={i} className="flex items-center justify-between py-2 px-3 bg-card2 rounded-lg">
                            <span className="text-sm text-ink truncate">{e.title}</span>
                            <span className="text-xs font-bold text-ac ml-2 shrink-0">{e.count}x</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <p className="text-xs font-semibold text-dim uppercase tracking-wide mb-3">Faollik (30 kun)</p>
                    <ResponsiveContainer width="100%" height={140}>
                      <AreaChart data={stats.timeline} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#26262b" strokeOpacity={0.5} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9a9aa0" }}
                          tickFormatter={(v) => v.slice(5)} tickLine={false} axisLine={{ stroke: "#26262b" }}
                          interval={Math.max(1, Math.floor(stats.timeline.length / 5))} />
                        <YAxis tick={{ fontSize: 10, fill: "#9a9aa0" }} axisLine={false} tickLine={false} allowDecimals={false} />
                        <Tooltip contentStyle={TOOLTIP_STYLE} />
                        <Area type="monotone" dataKey="questions" stroke="#1d9e75" fill="#1d9e75"
                          fillOpacity={0.08} strokeWidth={2} dot={false} name="Savollar" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="border-t border-rim pt-4 space-y-1.5 text-xs text-dim">
                    {group.added_by_name && (
                      <p>Qo&apos;shgan: <span className="text-ink">{group.added_by_name}
                        {group.added_by_username && ` (@${group.added_by_username})`}
                      </span></p>
                    )}
                    <p>Tur: <span className="text-ink capitalize">{group.chat_type ?? "—"}</span></p>
                    <p>Qo&apos;shilgan: <span className="text-ink">
                      {new Date(group.created_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })}
                    </span></p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Settings tab ── */}
          {activeTab === "settings" && (
            <div className="p-6 space-y-6">
              {/* Bot mode */}
              <div>
                <p className="text-xs font-semibold text-dim uppercase tracking-wide mb-3">
                  Bot rejimi {savingMode && <span className="text-ac normal-case font-normal">• saqlanmoqda…</span>}
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {BOT_MODES.map(({ key, label, desc, icon }) => (
                    <button key={key} onClick={() => handleModeChange(key)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        currentMode === key
                          ? "border-ac bg-ac/10"
                          : "border-rim bg-card2 hover:border-rim/70 hover:bg-card"
                      }`}
                    >
                      <span className="text-xl">{icon}</span>
                      <p className={`text-sm font-semibold mt-1.5 ${currentMode === key ? "text-ac" : "text-ink"}`}>{label}</p>
                      <p className="text-xs text-dim mt-0.5 leading-tight">{desc}</p>
                    </button>
                  ))}
                </div>

                <div className="mt-4 p-3 bg-card2 rounded-xl text-xs text-dim space-y-1.5 border border-rim">
                  {currentMode === "learning" && <>
                    <p className="font-medium text-ink">🔍 O&apos;qish rejimi</p>
                    <p>Bot faqat kuzatadi: kim savol beradi, kim javob beradi — rollarni aniqlaydi. @mention bo&apos;lsa darhol javob beradi.</p>
                  </>}
                  {currentMode === "knowledge" && <>
                    <p className="font-medium text-ink">📚 Bilim rejimi</p>
                    <p>Avval support javob berishini kutadi. Kutish vaqti o&apos;tsa, KB → AI zanjiri ishga tushadi. Poster savollari sozlamaga bog&apos;liq.</p>
                  </>}
                  {currentMode === "express" && <>
                    <p className="font-medium text-ink">⚡ Express rejim</p>
                    <p>Kutish yo&apos;q — xabar kelishi bilanoq darhol tahlil va javob. Maksimal tezlik.</p>
                  </>}
                </div>
              </div>

              {/* Poster auto-answer toggle */}
              <div className="border border-rim rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3.5">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-ink">Poster savollariga avtomatik javob</p>
                    <p className="text-xs text-dim mt-0.5">
                      {posterAutoAnswer
                        ? "Bot Poster savollarini o'zi hal qiladi"
                        : "Poster savollari poster_staff ga yo'naltiriladi"}
                    </p>
                  </div>
                  <Toggle value={posterAutoAnswer} onChange={handleTogglePoster} disabled={savingPoster} />
                </div>
                {savingPoster && (
                  <div className="px-4 pb-2 text-xs text-ac">Saqlanmoqda…</div>
                )}
              </div>

              <div className="p-3 bg-amber-900/10 border border-amber-800/25 rounded-xl text-xs text-amber-300/80">
                Sozlamalar o&apos;zgarishi darhol kuchga kiradi. Bot keyingi xabarda yangi rejimda ishlaydi.
              </div>
            </div>
          )}

          {/* ── Roles tab ── */}
          {activeTab === "roles" && (
            <div className="p-6 space-y-4">
              <p className="text-xs font-semibold text-dim uppercase tracking-wide">
                Guruh ishtirokchilari
              </p>

              {rolesLoading ? (
                <p className="text-dim text-sm text-center py-8">Yuklanmoqda…</p>
              ) : roles.length === 0 ? (
                <div className="text-center py-10 space-y-2">
                  <p className="text-dim text-sm">Ishtirokchilar hali aniqlanmagan</p>
                  <p className="text-xs text-dim/60">
                    Bot guruhda O&apos;qish yoki Bilim rejimida ishlasa, ishtirokchilarni avtomatik aniqlaydi.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {roles.map((r) => (
                    <div key={r.telegram_user_id}
                      className="flex items-center gap-3 px-4 py-3 bg-card2 border border-rim rounded-xl">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-ink truncate">
                            {r.full_name ?? r.username ?? `ID: ${r.telegram_user_id}`}
                          </span>
                          {r.is_manual_override && (
                            <span className="text-xs text-amber-400 shrink-0">✏ qo&apos;lda</span>
                          )}
                        </div>
                        {r.username && r.full_name && (
                          <p className="text-xs text-dim">@{r.username}</p>
                        )}
                        <p className="text-xs text-dim/60 mt-0.5">
                          Ishonch: {Math.round(r.confidence_score * 100)}%
                        </p>
                      </div>
                      <select
                        value={r.role}
                        onChange={(e) => handleRoleChange(r.telegram_user_id, e.target.value)}
                        className="bg-card border border-rim text-xs text-ink rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-ac"
                      >
                        <option value="poster_staff">Poster staff</option>
                        <option value="plugin_staff">Plugin staff</option>
                        <option value="communicator">Communicator</option>
                        <option value="customer">Mijoz</option>
                      </select>
                    </div>
                  ))}
                </div>
              )}

              <div className="text-xs text-dim/60 border-t border-rim pt-3">
                Rolni qo&apos;lda o&apos;zgartirish AI klassifikatsiyasidan ustun turadi.
              </div>
            </div>
          )}

          {/* ── Learning Feed tab ── */}
          {activeTab === "feed" && (
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-dim uppercase tracking-wide">O&apos;qish rejimi lenti</p>
                {currentMode !== "learning" && (
                  <span className="text-xs text-amber-400 bg-amber-900/20 border border-amber-800/30 px-2.5 py-1 rounded-full">
                    Hozir: {BOT_MODES.find(m => m.key === currentMode)?.label ?? currentMode}
                  </span>
                )}
              </div>

              {currentMode !== "learning" && (
                <div className="p-3 bg-card2 border border-rim rounded-xl text-xs text-dim">
                  Guruh hozir <span className="text-ink font-medium">{BOT_MODES.find(m => m.key === currentMode)?.label}</span> rejimida.
                  O&apos;qish rejimiga o&apos;tkazilsa, bot yangi savol-javob juftliklarini qayd eta boshlaydi.
                </div>
              )}

              {feedLoading ? (
                <p className="text-dim text-sm text-center py-8">Yuklanmoqda…</p>
              ) : feed.length === 0 ? (
                <div className="text-center py-10 space-y-2">
                  <p className="text-dim text-sm">Hali yozuvlar yo&apos;q</p>
                  <p className="text-xs text-dim/60">
                    Bot guruhda O&apos;qish rejimida ishlagan paytda savol-javob juftliklarini qayd etadi.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {feed.map((entry) => (
                    <div key={entry.id}
                      className={`border rounded-xl p-4 space-y-3 ${
                        entry.is_confirmed ? "border-ac/30 bg-ac/5" : "border-rim bg-card2"
                      }`}
                    >
                      {/* Question */}
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-dim">Savol</span>
                          {entry.question_username && (
                            <span className="text-xs text-dim/60">@{entry.question_username}</span>
                          )}
                        </div>
                        <p className="text-sm text-ink leading-relaxed">
                          {entry.question_text ?? <span className="text-dim italic">Matn yo&apos;q</span>}
                        </p>
                      </div>

                      {/* Answer */}
                      <div className="space-y-1 border-t border-rim/50 pt-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-ac">Javob</span>
                          {entry.answer_username && (
                            <span className="text-xs text-dim/60">@{entry.answer_username}</span>
                          )}
                        </div>
                        <p className="text-sm text-ink leading-relaxed">
                          {entry.answer_text ?? <span className="text-dim italic">Matn yo&apos;q</span>}
                        </p>
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-xs text-dim/60">
                          {new Date(entry.created_at).toLocaleDateString("ru-RU", {
                            day: "2-digit", month: "2-digit", year: "numeric",
                          })}
                        </span>
                        {entry.is_confirmed ? (
                          <span className="flex items-center gap-1 text-xs text-ac font-medium">
                            <CheckCircle size={12} /> KB ga qo&apos;shildi
                          </span>
                        ) : (
                          <button onClick={() => handleConfirm(entry.id)}
                            className="flex items-center gap-1 px-3 py-1 text-xs font-medium text-ac bg-ac/10 border border-ac/25 hover:bg-ac/20 rounded-lg transition-colors">
                            <CheckCircle size={11} /> KB ga qo&apos;shish
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function GroupsPage() {
  const [groups, setGroups]             = useState<Group[]>([]);
  const [filter, setFilter]             = useState<Filter>("all");
  const [searchInput, setSearchInput]   = useState("");
  const [search, setSearch]             = useState("");
  const [loading, setLoading]           = useState(true);
  const [actionId, setActionId]         = useState<number | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const load = useCallback(() => {
    setLoading(true);
    getGroups(filter === "all" ? undefined : filter, search || undefined)
      .then((r) => setGroups(r.data))
      .catch(() => setGroups([]))
      .finally(() => setLoading(false));
  }, [filter, search]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (id: number) => {
    setActionId(id);
    await approveGroup(id).catch(() => null);
    setActionId(null);
    load();
  };
  const handleReject = async (id: number) => {
    setActionId(id);
    await rejectGroup(id).catch(() => null);
    setActionId(null);
    load();
  };

  const tabs: { key: Filter; label: string }[] = [
    { key: "all",      label: "Barchasi" },
    { key: "pending",  label: "Kutmoqda" },
    { key: "approved", label: "Tasdiqlangan" },
    { key: "rejected", label: "Rad etilgan" },
  ];

  const counts = {
    all:      groups.length,
    pending:  groups.filter((g) => g.status === "pending").length,
    approved: groups.filter((g) => g.status === "approved").length,
    rejected: groups.filter((g) => g.status === "rejected").length,
  };

  const MODE_BADGE: Record<string, string> = {
    learning:  "text-amber-400 bg-amber-900/20 border-amber-800/30",
    knowledge: "text-blue-400 bg-blue-900/20 border-blue-800/30",
    express:   "text-ac bg-ac/10 border-ac/25",
  };
  const MODE_LABEL: Record<string, string> = {
    learning: "O'qish", knowledge: "Bilim", express: "Express",
  };

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-page">
        <Sidebar />
        <main className="flex-1 p-8 space-y-6 overflow-auto">
          <div>
            <h1 className="text-xl font-bold text-ink">Guruhlar</h1>
            <p className="text-sm text-dim mt-0.5">Bot qo&apos;shilgan guruhlarni boshqarish</p>
          </div>

          {/* Filter + search */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex gap-1 bg-card border border-rim p-1 rounded-xl">
              {tabs.map(({ key, label }) => (
                <button key={key} onClick={() => setFilter(key)}
                  className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                    filter === key ? "bg-card2 text-ink" : "text-dim hover:text-ink"
                  }`}
                >
                  {label}
                  {key !== "all" && counts[key] > 0 && (
                    <span className={`ml-1.5 text-xs rounded-full px-1.5 py-0.5 ${
                      filter === key ? "bg-ac/20 text-ac" : "bg-rim text-dim"
                    }`}>
                      {counts[key]}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="relative flex-1 min-w-[180px] max-w-xs">
              <input type="text" placeholder="Guruh nomini qidirish…"
                value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
                className="w-full bg-card border border-rim rounded-xl px-4 py-2 text-sm text-ink placeholder:text-dim focus:outline-none focus:ring-1 focus:ring-ac focus:border-ac transition-colors" />
              {searchInput && (
                <button onClick={() => { setSearchInput(""); setSearch(""); }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-dim hover:text-ink">
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="bg-card border border-rim rounded-xl overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-sm text-dim">Yuklanmoqda…</div>
            ) : groups.length === 0 ? (
              <div className="p-8 text-center text-sm text-dim">Guruhlar topilmadi</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-rim">
                  <tr className="text-left">
                    <th className="px-4 py-3 text-xs text-dim font-medium">Guruh</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Rejim</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Holat</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Sana</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <tr key={g.chat_id} onClick={() => setSelectedGroup(g)}
                      className="border-b border-rim/40 last:border-0 hover:bg-card2 transition-colors cursor-pointer">
                      <td className="px-4 py-3">
                        <div className="font-medium text-ink">{g.title ?? `Chat ${g.chat_id}`}</div>
                        {g.username && <div className="text-xs text-dim mt-0.5">@{g.username}</div>}
                        <div className="text-xs text-dim/50 font-mono">{g.chat_id}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${MODE_BADGE[g.bot_mode] ?? "text-dim bg-card2 border-rim"}`}>
                          {MODE_LABEL[g.bot_mode] ?? g.bot_mode}
                        </span>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={g.status} /></td>
                      <td className="px-4 py-3 text-dim text-xs">
                        {new Date(g.created_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          {g.status !== "approved" && (
                            <button onClick={() => handleApprove(g.chat_id)} disabled={actionId === g.chat_id}
                              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-green-300 bg-green-900/20 border border-green-800/30 hover:bg-green-900/35 rounded-lg disabled:opacity-50 transition-colors">
                              <CheckCircle size={12} /> Tasdiqlash
                            </button>
                          )}
                          {g.status !== "rejected" && (
                            <button onClick={() => handleReject(g.chat_id)} disabled={actionId === g.chat_id}
                              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-400 bg-red-900/20 border border-red-800/30 hover:bg-red-900/35 rounded-lg disabled:opacity-50 transition-colors">
                              <XCircle size={12} /> Rad etish
                            </button>
                          )}
                          <ChevronRight size={16} className="text-dim" />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </main>

        {selectedGroup && (
          <GroupDetailPanel
            group={selectedGroup}
            onClose={() => { setSelectedGroup(null); load(); }}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}
      </div>
    </AuthGuard>
  );
}
