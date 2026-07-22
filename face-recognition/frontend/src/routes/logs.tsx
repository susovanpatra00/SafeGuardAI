import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Search as SearchIcon, EyeOff } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SectionCard } from "@/components/section-card";
import { fetchLogs, type LogEntry } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/logs")({
  head: () => ({
    meta: [
      { title: "Logs & Reports — SafeGuardAI" },
      { name: "description", content: "Filter, sort, and export recognition event logs." },
      { property: "og:title", content: "Logs & Reports · SafeGuardAI" },
      { property: "og:description", content: "Complete audit trail of every recognition event." },
    ],
  }),
  component: LogsPage,
});

type SortKey = "timestamp" | "confidence" | "person";

function LogsPage() {
  const logs = useQuery({ queryKey: ["logs"], queryFn: fetchLogs });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | "known" | "unknown">("all");
  const [source, setSource] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [privacyBlur, setPrivacyBlur] = useState(true);

  const sources = Array.from(new Set((logs.data ?? []).map((l) => l.source)));
  const rows = (logs.data ?? [])
    .filter((l) => (status === "all" || l.status === status))
    .filter((l) => (source === "all" || l.source === source))
    .filter((l) => !query || l.person.toLowerCase().includes(query.toLowerCase()) || l.source.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "confidence") return (a.confidence - b.confidence) * dir;
      if (sortKey === "person") return a.person.localeCompare(b.person) * dir;
      return a.timestamp.localeCompare(b.timestamp) * dir;
    });

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  return (
    <AppShell title="Logs & Reports" subtitle="Every recognition event, audit-ready">
      <SectionCard
        actions={
          <div className="flex items-center gap-2">
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 px-2.5 py-1.5 text-[11px] hover:bg-white/[0.03] transition">
              <FileText className="h-3.5 w-3.5" /> Export PDF
            </button>
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 px-2.5 py-1.5 text-[11px] hover:bg-white/[0.03] transition">
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
          </div>
        }
        title="Filters"
        subtitle="Narrow the audit trail before exporting"
      >
        <div className="grid gap-3 md:grid-cols-4">
          <div className="relative">
            <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search person or source…"
              className="w-full pl-8 pr-3 py-2 text-[12px] rounded-lg bg-white/[0.03] border border-border/60 outline-none focus:border-primary/60" />
          </div>
          <select value={status} onChange={(e) => setStatus(e.target.value as "all" | "known" | "unknown")}
            className="text-[12px] bg-white/[0.03] border border-border/60 rounded-lg px-2 py-2 outline-none">
            <option value="all">All statuses</option>
            <option value="known">Known</option>
            <option value="unknown">Unknown</option>
          </select>
          <select value={source} onChange={(e) => setSource(e.target.value)}
            className="text-[12px] bg-white/[0.03] border border-border/60 rounded-lg px-2 py-2 outline-none">
            <option value="all">All cameras</option>
            {sources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <label className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-white/[0.02] px-3 py-2 cursor-pointer">
            <div className="flex items-center gap-2 min-w-0">
              <EyeOff className="h-3.5 w-3.5 text-primary shrink-0" />
              <div className="min-w-0">
                <div className="text-[12px] font-medium">Privacy Blur</div>
                <div className="text-[10px] text-muted-foreground truncate">Blur unknown faces in previews</div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setPrivacyBlur((v) => !v)}
              className={cn("relative h-5 w-9 rounded-full transition shrink-0",
                privacyBlur ? "bg-primary" : "bg-white/10")}
            >
              <span className={cn("absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all",
                privacyBlur ? "left-4" : "left-0.5")} />
            </button>
          </label>
        </div>
      </SectionCard>

      <SectionCard
        className="mt-4"
        title="Events"
        subtitle={`${rows.length} events`}
        bodyClassName="p-0"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.14em] text-muted-foreground border-b border-border/60">
                <Th onClick={() => toggleSort("person")} active={sortKey === "person"} dir={sortDir}>Person</Th>
                <Th onClick={() => toggleSort("timestamp")} active={sortKey === "timestamp"} dir={sortDir}>Timestamp</Th>
                <th className="px-5 py-3">Source</th>
                <Th onClick={() => toggleSort("confidence")} active={sortKey === "confidence"} dir={sortDir}>Confidence</Th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((l) => <LogRow key={l.id} l={l} blur={privacyBlur} />)}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </AppShell>
  );
}

function Th({ children, onClick, active, dir }: { children: React.ReactNode; onClick?: () => void; active?: boolean; dir?: "asc" | "desc" }) {
  return (
    <th className="px-5 py-3">
      <button onClick={onClick} className={cn("inline-flex items-center gap-1 hover:text-foreground transition", active && "text-primary")}>
        {children}
        {active && <span className="text-[9px]">{dir === "asc" ? "▲" : "▼"}</span>}
      </button>
    </th>
  );
}

function LogRow({ l, blur }: { l: LogEntry; blur: boolean }) {
  const unknown = l.status === "unknown";
  return (
    <tr className="border-b border-border/40 hover:bg-white/[0.02]">
      <td className="px-5 py-3">
        <div className="flex items-center gap-2.5">
          <div className={cn("h-7 w-7 rounded-full bg-white/5 grid place-items-center text-[10px] font-semibold text-primary", unknown && blur && "blur-[2px]")}>
            {unknown ? "?" : l.person.split(" ").map((n) => n[0]).join("").slice(0, 2)}
          </div>
          <span className="font-medium">{l.person}</span>
        </div>
      </td>
      <td className="px-5 py-3 tabular-nums text-muted-foreground">{new Date(l.timestamp).toLocaleString()}</td>
      <td className="px-5 py-3 text-muted-foreground">{l.source}</td>
      <td className="px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="h-1 w-20 rounded-full bg-white/5 overflow-hidden">
            <div className={cn("h-full", l.confidence > 90 ? "bg-emerald-400" : l.confidence > 75 ? "bg-primary" : "bg-amber-400")}
              style={{ width: `${l.confidence}%` }} />
          </div>
          <span className="tabular-nums text-[11px]">{l.confidence}%</span>
        </div>
      </td>
      <td className="px-5 py-3">
        <span className={cn("inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
          unknown ? "bg-rose-500/10 text-rose-400" : "bg-emerald-500/10 text-emerald-400")}>
          <span className={cn("h-1.5 w-1.5 rounded-full", unknown ? "bg-rose-400" : "bg-emerald-400")} />
          {l.status}
        </span>
      </td>
    </tr>
  );
}