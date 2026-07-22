import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, Play, Pause, FileVideo } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SectionCard } from "@/components/section-card";
import { fetchDetections, uploadDetectionJob, type Detection } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/detect/upload")({
  head: () => ({
    meta: [
      { title: "Detect · Upload — SafeGuardAI" },
      { name: "description", content: "Analyze uploaded videos and images for face detections." },
      { property: "og:title", content: "Detect · Upload" },
      { property: "og:description", content: "Batch face detection on uploaded media." },
    ],
  }),
  component: DetectUploadPage,
});

function DetectUploadPage() {
  const detections = useQuery({ queryKey: ["detections"], queryFn: fetchDetections });
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState(false);
  const [threshold, setThreshold] = useState(75);
  const inputRef = useRef<HTMLInputElement>(null);

  const start = async (f: File) => {
    setFile(f); setDone(false); setProcessing(true); setProgress(0);
    await uploadDetectionJob(f);
  };

  useEffect(() => {
    if (!processing) return;
    const t = setInterval(() => {
      setProgress((p) => {
        const next = p + 3 + Math.random() * 5;
        if (next >= 100) { clearInterval(t); setProcessing(false); setDone(true); return 100; }
        return next;
      });
    }, 220);
    return () => clearInterval(t);
  }, [processing]);

  const filtered = (detections.data ?? []).filter((d) => d.confidence >= threshold);

  return (
    <AppShell title="Detect · Upload" subtitle="Run face detection on uploaded video or image files">
      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard className="lg:col-span-1" title="Upload Media" subtitle="MP4, MOV, JPG, PNG">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) start(f); }}
            onClick={() => inputRef.current?.click()}
            className="rounded-xl border border-dashed border-border/70 hover:border-primary/60 bg-white/[0.02] p-8 text-center cursor-pointer transition"
          >
            <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 grid place-items-center mb-3">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <p className="text-[13px] font-medium">Drop file to analyze</p>
            <p className="text-[11px] text-muted-foreground mt-1">or click to browse</p>
            <input ref={inputRef} type="file" accept="video/*,image/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) start(f); }} />
          </div>

          {file && (
            <div className="mt-4 rounded-lg border border-border/60 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2 text-[12px]">
                <FileVideo className="h-4 w-4 text-primary" />
                <span className="truncate font-medium">{file.name}</span>
                <span className="ml-auto text-muted-foreground tabular-nums">{(file.size / 1024 / 1024).toFixed(1)}MB</span>
              </div>
              {processing && (
                <>
                  <div className="mt-3 flex items-center justify-between text-[11px]">
                    <span className="text-primary">Analyzing frames…</span>
                    <span className="tabular-nums">{Math.floor(progress)}%</span>
                  </div>
                  <div className="mt-1.5 h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full bg-[var(--grad-primary)] transition-[width] duration-200" style={{ width: `${progress}%` }} />
                  </div>
                </>
              )}
              {done && (
                <div className="mt-2 text-[11px] text-emerald-400">✓ Analysis complete · {detections.data?.length ?? 0} faces detected</div>
              )}
            </div>
          )}

          <div className="mt-5">
            <div className="flex items-center justify-between text-[11px] mb-2">
              <span className="text-muted-foreground uppercase tracking-[0.14em]">Confidence Threshold</span>
              <span className="text-primary tabular-nums font-medium">{threshold}%</span>
            </div>
            <input type="range" min={50} max={99} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-[var(--accent-cyan)]" />
          </div>
        </SectionCard>

        <SectionCard className="lg:col-span-2" title="Preview" subtitle="Annotated frame with detected faces" bodyClassName="p-0">
          <div className="relative aspect-video bg-[oklch(0.08_0.01_260)] overflow-hidden">
            <div className="absolute inset-0 opacity-30" style={{
              backgroundImage: "radial-gradient(circle at 30% 40%, oklch(0.3 0.05 260) 0, transparent 45%), radial-gradient(circle at 70% 60%, oklch(0.25 0.04 220) 0, transparent 40%)"
            }} />
            {done && filtered.slice(0, 4).map((d, i) => (
              <div key={d.id} className="absolute rounded border-2 border-primary shadow-[0_0_20px_var(--accent-cyan)] animate-slide-up"
                style={{
                  left: `${15 + (i * 20)}%`, top: `${20 + (i % 2) * 30}%`,
                  width: "14%", height: "28%",
                }}>
                <span className="absolute -top-6 left-0 text-[10px] font-medium bg-primary text-[oklch(0.14_0.02_260)] px-1.5 py-0.5 rounded whitespace-nowrap">
                  {d.name} · {d.confidence}%
                </span>
              </div>
            ))}
            {!done && processing && (
              <div className="absolute inset-0 grid place-items-center">
                <div className="text-center">
                  <div className="mx-auto h-14 w-14 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                  <div className="mt-3 text-[12px] text-primary">Processing frames…</div>
                </div>
              </div>
            )}
            {!file && (
              <div className="absolute inset-0 grid place-items-center text-muted-foreground text-[12px]">
                Upload a file to see annotated preview
              </div>
            )}
            <div className="absolute bottom-3 left-3 right-3 flex items-center gap-3 rounded-lg bg-black/60 backdrop-blur px-3 py-2">
              <button className="h-6 w-6 grid place-items-center rounded-full bg-primary text-[oklch(0.14_0.02_260)]">
                {processing ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
              </button>
              <div className="flex-1 h-1 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${done ? 100 : progress}%` }} />
              </div>
              <span className="text-[10px] tabular-nums text-muted-foreground">00:{String(Math.floor(progress * 0.6)).padStart(2, "0")} / 01:00</span>
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard className="mt-6" title="Detections" subtitle={`${filtered.length} faces above ${threshold}% confidence`} bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.14em] text-muted-foreground border-b border-border/60">
                <th className="px-5 py-3">Person</th>
                <th className="px-5 py-3">Timestamp</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">Frame</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => <DetectionRow key={d.id} d={d} />)}
              {filtered.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-10 text-center text-muted-foreground">No detections above threshold</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </AppShell>
  );
}

function DetectionRow({ d }: { d: Detection }) {
  const unknown = d.name === "Unknown";
  return (
    <tr className="border-b border-border/40 hover:bg-white/[0.02]">
      <td className="px-5 py-3">
        <div className="flex items-center gap-2.5">
          <img src={d.thumbnail} alt="" className={cn("h-8 w-8 rounded-full object-cover ring-1 ring-border", unknown && "grayscale")} />
          <span className="font-medium">{d.name}</span>
        </div>
      </td>
      <td className="px-5 py-3 tabular-nums text-muted-foreground">{d.videoTimestamp}</td>
      <td className="px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="h-1 w-20 rounded-full bg-white/5 overflow-hidden">
            <div className={cn("h-full", d.confidence > 90 ? "bg-emerald-400" : d.confidence > 75 ? "bg-primary" : "bg-amber-400")}
              style={{ width: `${d.confidence}%` }} />
          </div>
          <span className="tabular-nums text-[11px]">{d.confidence}%</span>
        </div>
      </td>
      <td className="px-5 py-3">
        <div className="h-10 w-14 rounded border border-border/60 bg-white/5 overflow-hidden">
          <img src={d.thumbnail} alt="" className={cn("h-full w-full object-cover", unknown && "grayscale blur-[2px]")} />
        </div>
      </td>
    </tr>
  );
}