"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getOverview, getTimeline, getTopErrors } from "@/lib/api";
import type { OverviewStats, DailyPoint, TopError } from "@/lib/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1 text-gray-900">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [timeline, setTimeline] = useState<DailyPoint[]>([]);
  const [topErrors, setTopErrors] = useState<TopError[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getOverview().then((r) => setStats(r.data)),
      getTimeline(7).then((r) => setTimeline(r.data)),
      getTopErrors(10).then((r) => setTopErrors(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 space-y-8 overflow-auto">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-500 mt-1">Bot faoliyati umumiy ko&apos;rinishi</p>
          </div>

          {loading ? (
            <div className="text-gray-400 text-sm">Yuklanmoqda…</div>
          ) : (
            <>
              {stats && (
                <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                  <StatCard label="Bugungi savollar" value={stats.today_questions} />
                  <StatCard label="Jami guruhlar" value={stats.total_groups} />
                  <StatCard label="Faol guruhlar" value={stats.approved_groups} />
                  <StatCard label="Xatolar bazasi" value={stats.total_errors_in_db} />
                  <StatCard
                    label="Hal etish foizi"
                    value={`${stats.resolution_rate_percent}%`}
                  />
                  <StatCard
                    label="O'rtacha javob"
                    value={
                      stats.avg_response_time_sec != null
                        ? `${stats.avg_response_time_sec}s`
                        : "—"
                    }
                  />
                </div>
              )}

              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-base font-semibold text-gray-800 mb-5">
                  So&apos;nggi 7 kun — savollar va hal etilganlar
                </h2>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={timeline} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "#9ca3af" }}
                      tickFormatter={(v) => v.slice(5)}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      formatter={(v: number, name: string) => [v, name]}
                    />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                    <Line
                      type="monotone"
                      dataKey="questions"
                      stroke="#2563eb"
                      strokeWidth={2}
                      name="Savollar"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="resolved"
                      stroke="#16a34a"
                      strokeWidth={2}
                      name="Hal etildi"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-base font-semibold text-gray-800 mb-4">Top xatolar</h2>
                {topErrors.length === 0 ? (
                  <p className="text-sm text-gray-400">Ma&apos;lumot yo&apos;q</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 border-b text-xs uppercase tracking-wide">
                        <th className="pb-2 w-8">#</th>
                        <th className="pb-2">Xato</th>
                        <th className="pb-2 text-right">Murojaatlar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topErrors.map((e, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-2.5 text-gray-400 text-xs">{i + 1}</td>
                          <td className="py-2.5 font-medium">{e.title}</td>
                          <td className="py-2.5 text-right font-bold text-blue-600">
                            {e.count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
