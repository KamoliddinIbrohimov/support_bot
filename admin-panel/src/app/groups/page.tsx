"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getGroups, approveGroup, rejectGroup } from "@/lib/api";
import type { Group } from "@/lib/types";
import { CheckCircle, XCircle, Clock } from "lucide-react";

type Filter = "all" | "pending" | "approved" | "rejected";

const STATUS_LABEL: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  pending: {
    label: "Kutmoqda",
    cls: "bg-yellow-50 text-yellow-700",
    icon: <Clock size={12} />,
  },
  approved: {
    label: "Tasdiqlangan",
    cls: "bg-green-50 text-green-700",
    icon: <CheckCircle size={12} />,
  },
  rejected: {
    label: "Rad etilgan",
    cls: "bg-red-50 text-red-700",
    icon: <XCircle size={12} />,
  },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_LABEL[status] ?? { label: status, cls: "bg-gray-100 text-gray-600", icon: null };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full ${s.cls}`}>
      {s.icon}
      {s.label}
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

  useEffect(() => { load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleApprove = async (chatId: number) => {
    setActionId(chatId);
    await approveGroup(chatId);
    setActionId(null);
    load();
  };

  const handleReject = async (chatId: number) => {
    setActionId(chatId);
    await rejectGroup(chatId);
    setActionId(null);
    load();
  };

  const tabs: { key: Filter; label: string }[] = [
    { key: "all", label: "Barchasi" },
    { key: "pending", label: "Kutmoqda" },
    { key: "approved", label: "Tasdiqlangan" },
    { key: "rejected", label: "Rad etilgan" },
  ];

  const counts = {
    all: groups.length,
    pending: groups.filter((g) => g.status === "pending").length,
    approved: groups.filter((g) => g.status === "approved").length,
    rejected: groups.filter((g) => g.status === "rejected").length,
  };

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 space-y-6 overflow-auto">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Guruhlar</h1>
            <p className="text-sm text-gray-500 mt-1">Bot qo&apos;shilgan guruhlarni boshqarish</p>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  filter === key
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {label}
                {key !== "all" && (
                  <span
                    className={`ml-1.5 text-xs rounded-full px-1.5 py-0.5 ${
                      filter === key ? "bg-blue-100 text-blue-700" : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {counts[key]}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-sm text-gray-400">Yuklanmoqda…</div>
            ) : groups.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">Guruhlar topilmadi</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Guruh</th>
                    <th className="px-4 py-3">Tur</th>
                    <th className="px-4 py-3">Qo&apos;shgan</th>
                    <th className="px-4 py-3">Holat</th>
                    <th className="px-4 py-3">Qo&apos;shilgan sana</th>
                    <th className="px-4 py-3 text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {groups.map((g) => (
                    <tr key={g.chat_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">
                          {g.title ?? `Chat ${g.chat_id}`}
                        </div>
                        {g.username && (
                          <div className="text-xs text-gray-400 mt-0.5">@{g.username}</div>
                        )}
                        <div className="text-xs text-gray-400">{g.chat_id}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs capitalize">
                        {g.chat_type ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        {g.added_by_name ? (
                          <div>
                            <div className="font-medium text-gray-800">{g.added_by_name}</div>
                            {g.added_by_username && (
                              <div className="text-xs text-gray-400">@{g.added_by_username}</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={g.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {new Date(g.created_at).toLocaleDateString("ru-RU", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {g.status !== "approved" && (
                            <button
                              onClick={() => handleApprove(g.chat_id)}
                              disabled={actionId === g.chat_id}
                              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg disabled:opacity-50 transition-colors"
                            >
                              <CheckCircle size={13} />
                              Tasdiqlash
                            </button>
                          )}
                          {g.status !== "rejected" && (
                            <button
                              onClick={() => handleReject(g.chat_id)}
                              disabled={actionId === g.chat_id}
                              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg disabled:opacity-50 transition-colors"
                            >
                              <XCircle size={13} />
                              Rad etish
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
