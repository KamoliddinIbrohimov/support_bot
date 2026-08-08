"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getGroups, approveGroup, rejectGroup } from "@/lib/api";
import type { Group } from "@/lib/types";
import { CheckCircle, XCircle, Clock } from "lucide-react";

type Filter = "all" | "pending" | "approved" | "rejected";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    pending:  { label: "Kutmoqda",    cls: "bg-amber-900/25 text-amber-300 border-amber-800/30", icon: <Clock size={11} /> },
    approved: { label: "Tasdiqlangan",cls: "bg-green-900/25 text-green-300 border-green-800/30", icon: <CheckCircle size={11} /> },
    rejected: { label: "Rad etilgan", cls: "bg-red-900/25 text-red-300 border-red-800/30",       icon: <XCircle size={11} /> },
  };
  const s = map[status] ?? { label: status, cls: "bg-card2 text-dim border-rim", icon: null };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border ${s.cls}`}>
      {s.icon}{s.label}
    </span>
  );
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);

  const load = (f: Filter = filter) => {
    setLoading(true);
    getGroups(f === "all" ? undefined : f)
      .then((r) => setGroups(r.data))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [filter]);

  const handleApprove = async (id: number) => {
    setActionId(id); await approveGroup(id); setActionId(null); load();
  };
  const handleReject = async (id: number) => {
    setActionId(id); await rejectGroup(id); setActionId(null); load();
  };

  const tabs: { key: Filter; label: string }[] = [
    { key: "all",      label: "Barchasi" },
    { key: "pending",  label: "Kutmoqda" },
    { key: "approved", label: "Tasdiqlangan" },
    { key: "rejected", label: "Rad etilgan" },
  ];

  const counts: Record<Filter, number> = {
    all:      groups.length,
    pending:  groups.filter((g) => g.status === "pending").length,
    approved: groups.filter((g) => g.status === "approved").length,
    rejected: groups.filter((g) => g.status === "rejected").length,
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

          {/* Filter tabs */}
          <div className="flex gap-1 bg-card border border-rim p-1 rounded-xl w-fit">
            {tabs.map(({ key, label }) => (
              <button key={key} onClick={() => setFilter(key)}
                className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  filter === key
                    ? "bg-card2 text-ink"
                    : "text-dim hover:text-ink"
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
                    <th className="px-4 py-3 text-xs text-dim font-medium">Tur</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Qo&apos;shgan</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Holat</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Sana</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <tr key={g.chat_id} className="border-b border-rim/40 last:border-0 hover:bg-card2 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-ink">{g.title ?? `Chat ${g.chat_id}`}</div>
                        {g.username && <div className="text-xs text-dim mt-0.5">@{g.username}</div>}
                        <div className="text-xs text-dim/60">{g.chat_id}</div>
                      </td>
                      <td className="px-4 py-3 text-dim text-xs capitalize">{g.chat_type ?? "—"}</td>
                      <td className="px-4 py-3">
                        {g.added_by_name ? (
                          <div>
                            <div className="text-ink">{g.added_by_name}</div>
                            {g.added_by_username && <div className="text-xs text-dim">@{g.added_by_username}</div>}
                          </div>
                        ) : <span className="text-dim">—</span>}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={g.status} /></td>
                      <td className="px-4 py-3 text-dim text-xs">
                        {new Date(g.created_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
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
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
