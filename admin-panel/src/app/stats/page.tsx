"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getOverview, getTimeline, getGroupStats } from "@/lib/api";
import type { OverviewStats, DailyPoint, GroupStat } from "@/lib/types";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";

const DAYS_OPTIONS = [
  { label: "7 kun",  value: 7 },
  { label: "30 kun", value: 30 },
  { label: "90 kun", value: 90 },
];

const TOOLTIP_STYLE = {
  backgroundColor: "#17171a",
  border: "1px solid #26262b",
  borderRadius: 8,
  color: "#f2f2f3",
  fontSize: 12,
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-card border border-rim rounded-xl p-5">
      <p className="text-xs text-dim uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1 text-ink">{value}</p>
    </div>
  );
}

function RateBadge({ rate }: { rate: number }) {
  const cls =
    rate >= 70 ? "text-green-400" :
    rate >= 40 ? "text-amber-400" :
    "text-red-400";
  return <span className={`text-xs font-semibold ${cls}`}>{rate}%</span>;
}

export default function StatsPage() {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [timeline, setTimeline] = useState<DailyPoint[]>([]);
  const [groupStats, setGroupStats] = useState<GroupStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getOverview().then((r) => setOverview(r.data)).catch(() => null),
      getTimeline(days).then((r) => setTimeline(r.data)).catch(() => null),
      getGroupStats().then((r) => setGroupStats(r.data)).catch(() => null),
    ]).finally(() => setLoading(false));
  }, [days]);

  const totalQ       = groupStats.reduce((s, g) => s + g.questions, 0);
  const totalAI      = groupStats.reduce((s, g) => s + g.resolved_by_ai, 0);
  const totalSupport = groupStats.reduce((s, g) => s + g.resolved_by_support, 0);

  const aiPct      = totalQ ? Math.round((totalAI / totalQ) * 100) : 0;
  const supportPct = totalQ ? Math.round((totalSupport / totalQ) * 100) : 0;

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-page">
        <Sidebar />
        <main className="flex-1 p-8 space-y-8 overflow-auto">

          {/* Header */}
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-xl font-bold text-ink">Statistika</h1>
              <p className="text-sm text-dim mt-0.5">Bot faoliyatining batafsil tahlili</p>
            </div>

            {/* Days selector */}
            <div className="flex gap-1 bg-card border border-rim p-1 rounded-xl">
              {DAYS_OPTIONS.map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => setDays(value)}
                  className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                    days === value ? "bg-card2 text-ink" : "text-dim hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Overview cards */}
          {overview && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard label="Bugungi savollar" value={overview.today_questions} />
              <StatCard label="Faol guruhlar"    value={overview.approved_groups} />
              <StatCard label="Hal etish %"      value={`${overview.resolution_rate_percent}%`} />
              <StatCard label="Xatolar bazasi"   value={overview.total_errors_in_db} />
            </div>
          )}

          {/* AI vs Support breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-card border border-rim rounded-xl p-5">
              <p className="text-xs text-dim uppercase tracking-wide">Jami savollar</p>
              <p className="text-3xl font-bold text-ink mt-2">{totalQ}</p>
              <p className="text-xs text-dim mt-1">Barcha guruhlar bo&apos;yicha</p>
            </div>
            <div className="bg-card border border-rim rounded-xl p-5">
              <p className="text-xs text-dim uppercase tracking-wide">AI hal etdi</p>
              <p className="text-3xl font-bold text-ac mt-2">{totalAI}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-card2 rounded-full overflow-hidden">
                  <div className="h-full bg-ac rounded-full" style={{ width: `${aiPct}%` }} />
                </div>
                <span className="text-xs text-dim">{aiPct}%</span>
              </div>
            </div>
            <div className="bg-card border border-rim rounded-xl p-5">
              <p className="text-xs text-dim uppercase tracking-wide">Support hal etdi</p>
              <p className="text-3xl font-bold text-blue-400 mt-2">{totalSupport}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-card2 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${supportPct}%` }} />
                </div>
                <span className="text-xs text-dim">{supportPct}%</span>
              </div>
            </div>
          </div>

          {/* Timeline chart */}
          <div className="bg-card border border-rim rounded-xl p-6">
            <h2 className="text-sm font-semibold text-ink mb-5">
              So&apos;nggi {days} kun faoliyati
            </h2>
            {loading ? (
              <div className="h-56 flex items-center justify-center text-dim text-sm">
                Yuklanmoqda…
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={timeline} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#26262b" strokeOpacity={0.6} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "#9a9aa0" }}
                    axisLine={{ stroke: "#26262b" }}
                    tickLine={false}
                    tickFormatter={(v) => v.slice(5)}
                    interval={Math.max(0, Math.floor(timeline.length / 8) - 1)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#9a9aa0" }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: "#26262b" }} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: "#9a9aa0" }} />
                  <Line
                    type="monotone" dataKey="questions"
                    stroke="#1d9e75" strokeWidth={2} name="Savollar" dot={false}
                  />
                  <Line
                    type="monotone" dataKey="resolved"
                    stroke="#378add" strokeWidth={2} name="Hal etildi" dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Groups ranking */}
          <div className="bg-card border border-rim rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-rim flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Guruhlar reytingi</h2>
              <span className="text-xs text-dim">{groupStats.length} ta guruh</span>
            </div>

            {groupStats.length === 0 ? (
              <div className="p-8 text-center text-sm text-dim">
                {loading ? "Yuklanmoqda…" : "Ma'lumot yo'q"}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-rim">
                  <tr className="text-left">
                    <th className="px-4 py-3 text-xs text-dim font-medium w-8">#</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Guruh</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Savollar</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">AI</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Support</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Hal etish %</th>
                  </tr>
                </thead>
                <tbody>
                  {groupStats.map((g, i) => {
                    const resolved = g.resolved_by_ai + g.resolved_by_support;
                    const rate = g.questions ? Math.round((resolved / g.questions) * 100) : 0;
                    return (
                      <tr
                        key={g.chat_id}
                        className="border-b border-rim/40 last:border-0 hover:bg-card2 transition-colors"
                      >
                        <td className="px-4 py-3 text-dim text-xs">{i + 1}</td>
                        <td className="px-4 py-3">
                          <div className="font-medium text-ink">
                            {g.title ?? `Chat ${g.chat_id}`}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-ink">{g.questions}</td>
                        <td className="px-4 py-3 text-right text-ac">{g.resolved_by_ai}</td>
                        <td className="px-4 py-3 text-right text-blue-400">{g.resolved_by_support}</td>
                        <td className="px-4 py-3 text-right"><RateBadge rate={rate} /></td>
                      </tr>
                    );
                  })}
                </tbody>

                {/* Totals row */}
                {groupStats.length > 1 && (
                  <tfoot className="border-t border-rim bg-card2">
                    <tr>
                      <td className="px-4 py-3" />
                      <td className="px-4 py-3 text-xs font-semibold text-dim">Jami</td>
                      <td className="px-4 py-3 text-right font-bold text-ink">{totalQ}</td>
                      <td className="px-4 py-3 text-right font-bold text-ac">{totalAI}</td>
                      <td className="px-4 py-3 text-right font-bold text-blue-400">{totalSupport}</td>
                      <td className="px-4 py-3 text-right">
                        <RateBadge rate={totalQ ? Math.round(((totalAI + totalSupport) / totalQ) * 100) : 0} />
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            )}
          </div>

        </main>
      </div>
    </AuthGuard>
  );
}
