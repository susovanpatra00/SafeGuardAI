import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, Search as SearchIcon, ArrowUpDown } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SectionCard } from "@/components/section-card";
import { searchByFace, formatRelative } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/search")({
  head: () => ({
    meta: [
      { title: "Search — SafeGuardAI" },
      { name: "description", content: "Search across all footage and logs by uploading a face." },
      { property: "og:title", content: "Search · SafeGuardAI" },
      { property: "og:description", content: "Face-based search across all recordings." },
    ],
  }),
  component: SearchPage,
});

function SearchPage() {
  const results = useQuery({ queryKey: ["search-results"], queryFn: searchByFace });
  const [preview, setPreview] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<"confidence" | "date">("confidence");
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = (f: File) => setPreview(URL.createObjectURL(f));

  const sorted = [...(results.data ?? [])]
    .filter((r) => !query || r.person.toLowerCase().includes(query.toLowerCase()) || r.source.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => sortBy === "confidence" ? b.confidence - a.confidence : b.timestamp.localeCompare(a.timestamp));

  return (
    <AppShell title="Search" subtitle="Find a face across every camera and archived recording">
      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard title="Search by Face" subtitle="Upload a reference photo">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
            onClick={() => inputRef.current?.click()}
            className="relative aspect-square rounded-xl border border-dashed border-border/70 hover:border-primary/60 bg-white/[0.02] cursor-pointer overflow-hidden transition"
          >
            {preview ? (
              <>
                <img src={preview} alt="" className="absolute inset-0 h-full w-full object-cover" />
                <div className="absolute rounded border-2 border-primary shadow-[0_0_20px_var(--accent-cyan)]"
                  style={{ left: "24%", top: "18%", width: "52%", height: "58%" }} />
              </>
            ) : (
              <div className="absolute inset-0 grid place-items-center text-center p-6">
                <div>
                  <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 grid place-items-center mb-3">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  <p className="text-[13px] font-medium">Upload reference face</p>
                  <p className="text-[11px] text-muted-foreground mt-1">We'll match across all archives</p>
                </div>
              </div>
            )}
            <input ref={inputRef} type="file" accept="image/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
          </div>

          <button className="mt-4 w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-[var(--grad-primary)] px-3 py-2 text-[12px] font-semibold text-[oklch(0.14_0.02_260)] shadow-[var(--shadow-glow)] hover:brightness-110 transition">
            <SearchIcon className="h-3.5 w-3.5" /> Run Face Search
          </button>

          <div className="mt-5 space-y-3 text-[12px]">
            <div className="relative">
              <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter by name or camera…"
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-white/[0.03] border border-border/60 outline-none focus:border-primary/60" />
            </div>
            <div className="flex items-center gap-2">
              <input type="date" className="flex-1 py-1.5 px-2 rounded-lg bg-white/[0.03] border border-border/60 outline-none" />
              <span className="text-muted-foreground">→</span>
              <input type="date" className="flex-1 py-1.5 px-2 rounded-lg bg-white/[0.03] border border-border/60 outline-none" />
            </div>
          </div>
        </SectionCard>

        <SectionCard
          className="lg:col-span-2"
          title="Matches"
          subtitle={`${sorted.length} results across your archive`}
          actions={
            <button onClick={() => setSortBy((s) => s === "confidence" ? "date" : "confidence")}
              className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-[11px] hover:bg-white/[0.03]">
              <ArrowUpDown className="h-3 w-3" />
              Sort: {sortBy}
            </button>
          }
          bodyClassName="p-3"
        >
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 xl:grid-cols-4">
            {sorted.map((r) => (
              <div key={r.id} className="animate-slide-up group rounded-xl border border-border/60 bg-white/[0.02] overflow-hidden hover:border-primary/40 transition">
                <div className="relative aspect-square">
                  <img src={r.thumbnail} alt="" className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-2">
                    <div className="text-[11px] font-semibold truncate">{r.person}</div>
                    <div className="text-[10px] text-muted-foreground truncate">{r.source}</div>
                  </div>
                  <span className={cn("absolute top-1.5 right-1.5 text-[10px] px-1.5 py-0.5 rounded font-medium backdrop-blur",
                    r.confidence > 90 ? "bg-emerald-500/80 text-white" : r.confidence > 80 ? "bg-primary text-[oklch(0.14_0.02_260)]" : "bg-amber-500/80 text-white")}>
                    {r.confidence}%
                  </span>
                </div>
                <div className="px-2.5 py-1.5 text-[10px] text-muted-foreground border-t border-border/40">
                  {formatRelative(r.timestamp)}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}