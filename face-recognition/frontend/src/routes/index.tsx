import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Users, Eye, ShieldAlert, Camera, TrendingUp } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ActivityFeedItem } from "@/components/activity-feed";
import {
  fetchDashboardStats,
  fetchRecentActivity,
  fetchRecognitionSeries,
  fetchMostRecognized,
  generateActivityEvent,
  type ActivityEvent,
} from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — SafeGuardAI" },
      { name: "description", content: "Live face intelligence overview: recognitions, alerts, and camera activity." },
      { property: "og:title", content: "SafeGuardAI Dashboard" },
      { property: "og:description", content: "Live face intelligence overview." },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const [range, setRange] = useState<"24h" | "7d">("24h");
  const stats = useQuery({ queryKey: ["dashboard-stats"], queryFn: fetchDashboardStats });
  const series = useQuery({ queryKey: ["recognitions", range], queryFn: () => fetchRecognitionSeries(range) });
  const activity = useQuery({ queryKey: ["recent-activity"], queryFn: () => fetchRecentActivity(10) });
  const leaders = useQuery({ queryKey: ["most-recognized"], queryFn: fetchMostRecognized });

  // Simulate live feed
  const [feed, setFeed] = useState<ActivityEvent[]>([]);
  useEffect(() => {
    if (activity.data && feed.length === 0) setFeed(activity.data);
  }, [activity.data, feed.length]);
  useEffect(() => {
    let i = 100;
    const t = setInterval(() => {
      i += 1;
      setFeed((prev) => [generateActivityEvent(i), ...prev].slice(0, 12));
    }, 4200);
    return () => clearInterval(t);
  }, []);

  const s = stats.data;

  return (
    <AppShell title="Dashboard" subtitle="Real-time face intelligence across your infrastructure">
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Enrolled Faces" value={s?.totalEnrolled ?? 0} delta={s?.deltas.totalEnrolled} icon={Users} accent />
        <StatCard label="Recognitions Today" value={s?.recognitionsToday ?? 0} delta={s?.deltas.recognitionsToday} icon={Eye} />
        <StatCard label="Unknown Faces Flagged" value={s?.unknownFlagged ?? 0} delta={s?.deltas.unknownFlagged} icon={ShieldAlert} />
        <StatCard label="Active Cameras" value={s?.activeCameras ?? 0} delta={s?.deltas.activeCameras} icon={Camera} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <SectionCard
          className="lg:col-span-2"
          title="Recognitions"
          subtitle="Recognition volume across all connected cameras"
          actions={
            <div className="flex items-center gap-1 rounded-lg border border-border/60 bg-white/[0.02] p-0.5">
              {(["24h", "7d"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    "px-2.5 py-1 text-[11px] font-medium rounded-md transition",
                    range === r ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          }
          bodyClassName="p-0"
        >
          <div className="h-72 px-2 pt-2 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series.data ?? []} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="grad-recog" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d9ff" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#00d9ff" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="grad-unk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="label" stroke="rgba(255,255,255,0.35)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="rgba(255,255,255,0.35)" fontSize={11} tickLine={false} axisLine={false} width={30} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(15,18,28,0.95)",
                    border: "1px solid rgba(0,217,255,0.25)",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#9ca3af" }}
                />
                <Area type="monotone" dataKey="recognitions" stroke="#00d9ff" strokeWidth={2} fill="url(#grad-recog)" />
                <Area type="monotone" dataKey="unknown" stroke="#f43f5e" strokeWidth={1.5} fill="url(#grad-unk)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard
          title="Most Recognized"
          subtitle="Top identities across the last 7 days"
          actions={<TrendingUp className="h-4 w-4 text-primary" />}
          bodyClassName="p-3"
        >
          <ol className="space-y-1">
            {(leaders.data ?? []).map((l, idx) => {
              const max = leaders.data?.[0].count ?? 1;
              const pct = Math.round((l.count / max) * 100);
              return (
                <li key={l.person.id} className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-white/[0.03]">
                  <span className="w-4 text-[11px] text-muted-foreground tabular-nums text-right">{idx + 1}</span>
                  <img src={l.person.avatar} alt="" className="h-7 w-7 rounded-full object-cover ring-1 ring-border" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[12px] font-medium truncate">{l.person.name}</span>
                      <span className="text-[11px] tabular-nums text-primary">{l.count}</span>
                    </div>
                    <div className="mt-1 h-1 rounded-full bg-white/5 overflow-hidden">
                      <div className="h-full bg-[var(--grad-primary)]" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </SectionCard>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <SectionCard
          className="lg:col-span-2"
          title="Recent Activity"
          subtitle="Live recognition events streaming from all cameras"
          actions={
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />
              LIVE
            </span>
          }
          bodyClassName="p-2 max-h-[420px] overflow-y-auto"
        >
          <div className="space-y-0.5">
            {feed.map((e) => (
              <ActivityFeedItem key={e.id} event={e} />
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Camera Health" subtitle="Uptime across active cameras">
          <div className="space-y-3">
            {["Cam-01 · Lobby", "Cam-04 · Server Room", "Cam-07 · Parking", "Cam-12 · Rooftop", "Cam-03 · Main Entry"].map((c, i) => {
              const uptime = [99.9, 99.7, 98.2, 99.5, 96.4][i];
              return (
                <div key={c}>
                  <div className="flex items-center justify-between text-[12px]">
                    <span className="text-foreground/90">{c}</span>
                    <span className="tabular-nums text-muted-foreground">{uptime}%</span>
                  </div>
                  <div className="mt-1.5 h-1 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className={cn("h-full", uptime > 99 ? "bg-emerald-400/80" : uptime > 97 ? "bg-primary" : "bg-amber-400/80")}
                      style={{ width: `${uptime}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}
