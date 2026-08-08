"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getOverview, getTimeline, getTopErrors } from "@/lib/api";
import type { OverviewStats, DailyPoint, TopError } from "@/lib/types";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-card border border-rim rounded-xl p-5">
      <p className="text-xs text-dim uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1 text-ink">{value}</p>
    </div>
  );
}

const TOOLTIP_STYLE = {
  backgroundColor: "#17171a",
  border: "1px solid #26262b",
  borderRadius: 8,
  color: "#f2f2f3",
  fontSize: 12,
};

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
      <div className="flex min-h-screen bg-page">
        <Sidebar />
        <main className="flex-1 p-8 space-y-8 overflow-auto">
          <div>
            <h1 className="text-xl font-bold text-ink">Dashboard</h1>
            <p className="text-sm text-dim mt-0.5">Bot faoliyati umumiy ko&apos;rinishi</p>
          </div>

          {loading ? (
            <p className="text-dim text-sm">Yuklanmoqda…</p>
          ) : (
            <>
              {stats && (
                <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
                  <StatCard label="Bugungi savollar"  value={stats.today_questions} />
                  <StatCard label="Jami guruhlar"     value={stats.total_groups} />
                  <StatCard label="Faol guruhlar"     value={stats.approved_groups} />
                  <StatCard label="Xatolar bazasi"    value={stats.total_errors_in_db} />
                  <StatCard label="Hal etish %"       value={`${stats.resolution_rate_percent}%`} />
                  <StatCard label="O'rtacha javob"    value={stats.avg_response_time_sec != null ? `${stats.avg_response_time_sec}s` : "—"} />
                </div>
              )}

              <div className="bg-card border border-rim rounded-xl p-6">
                <h2 className="text-sm font-semibold text-ink mb-5">
                  So&apos;nggi 7 kun
                </h2>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={timeline} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26262b" strokeOpacity={0.6} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "#9a9aa0" }}
                      axisLine={{ stroke: "#26262b" }}
                      tickLine={false}
                      tickFormatter={(v) => v.slice(5)}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "#9a9aa0" }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: "#26262b" }} />
                    <Legend
                      iconSize={10}
                      wrapperStyle={{ fontSize: 12, color: "#9a9aa0" }}
                    />
                    <Line type="monotone" dataKey="questions" stroke="#1d9e75" strokeWidth={2} name="Savollar" dot={false} />
                    <Line type="monotone" dataKey="resolved"  stroke="#378add" strokeWidth={2} name="Hal etildi" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-card border border-rim rounded-xl p-6">
                <h2 className="text-sm font-semibold text-ink mb-4">Top xatolar</h2>
                {topErrors.length === 0 ? (
                  <p className="text-dim text-sm">Ma&apos;lumot yo&apos;q</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left border-b border-rim">
                        <th className="pb-2 text-xs text-dim font-medium w-8">#</th>
                        <th className="pb-2 text-xs text-dim font-medium">Xato</th>
                        <th className="pb-2 text-xs text-dim font-medium text-right">Murojaatlar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topErrors.map((e, i) => (
                        <tr key={i} className="border-b border-rim/50 last:border-0">
                          <td className="py-2.5 text-dim text-xs">{i + 1}</td>
                          <td className="py-2.5 text-ink">{e.title}</td>
                          <td className="py-2.5 text-right font-bold text-ac">{e.count}</td>
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
