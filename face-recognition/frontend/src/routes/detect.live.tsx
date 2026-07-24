import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Play, Square, Maximize2, Camera as CameraIcon } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SectionCard } from "@/components/section-card";
import { ActivityFeedItem } from "@/components/activity-feed";
import { generateActivityEvent, type ActivityEvent } from "@/lib/mock-data";

export const Route = createFileRoute("/detect/live")({
  head: () => ({
    meta: [
      { title: "Detect · Live — SafeGuardAI" },
      { name: "description", content: "Live face detection from RTSP and webcam feeds." },
      { property: "og:title", content: "Detect · Live" },
      { property: "og:description", content: "Real-time face recognition on live streams." },
    ],
  }),
  component: LivePage,
});

const OVERLAY_BOXES = [
  { name: "Alex Chen", confidence: 97.4, left: "18%", top: "28%", w: "16%", h: "34%" },
  { name: "Jordan Patel", confidence: 92.1, left: "48%", top: "40%", w: "14%", h: "30%" },
  { name: "Unknown", confidence: 71.5, left: "72%", top: "22%", w: "15%", h: "32%" },
];

function LivePage() {
  const [streaming, setStreaming] = useState(true);
  const [feed, setFeed] = useState<ActivityEvent[]>(() => Array.from({ length: 8 }, (_, i) => generateActivityEvent(i)));
  const [selectedCamera, setSelectedCamera] = useState("Cam-01 · Lobby");

  useEffect(() => {
    if (!streaming) return;
    let i = 200;
    const t = setInterval(() => {
      i += 1;
      setFeed((prev) => [generateActivityEvent(i), ...prev].slice(0, 20));
    }, 2600);
    return () => clearInterval(t);
  }, [streaming]);

  return (
    <AppShell title="Detect · Live" subtitle="Real-time recognition across active camera feeds">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <SectionCard bodyClassName="p-0">
            <div className="relative aspect-video bg-[oklch(0.06_0.01_260)] overflow-hidden">
              <div className="absolute inset-0"
                style={{
                  backgroundImage:
                    "radial-gradient(ellipse at 30% 40%, oklch(0.28 0.05 260) 0, transparent 55%), radial-gradient(ellipse at 70% 60%, oklch(0.22 0.04 220) 0, transparent 50%), linear-gradient(180deg, transparent 0%, oklch(0.08 0.01 260 / 0.8) 100%)"
                }} />
              <div className="absolute inset-0 opacity-20"
                style={{ backgroundImage: "repeating-linear-gradient(0deg, transparent 0px, transparent 2px, oklch(1 0 0 / 0.04) 2px, oklch(1 0 0 / 0.04) 3px)" }} />

              {streaming && OVERLAY_BOXES.map((b, i) => {
                const unknown = b.name === "Unknown";
                return (
                  <div key={i} className="absolute animate-slide-up"
                    style={{ left: b.left, top: b.top, width: b.w, height: b.h }}>
                    <div className={`h-full w-full rounded border-2 ${unknown ? "border-rose-500 shadow-[0_0_20px_rgba(244,63,94,0.5)]" : "border-primary shadow-[0_0_20px_var(--accent-cyan)]"}`}>
                      {["tl","tr","bl","br"].map((c) => (
                        <span key={c} className={`absolute h-2 w-2 border-primary ${
                          c === "tl" ? "top-[-2px] left-[-2px] border-t-2 border-l-2" :
                          c === "tr" ? "top-[-2px] right-[-2px] border-t-2 border-r-2" :
                          c === "bl" ? "bottom-[-2px] left-[-2px] border-b-2 border-l-2" :
                          "bottom-[-2px] right-[-2px] border-b-2 border-r-2"
                        } ${unknown ? "!border-rose-500" : ""}`} />
                      ))}
                    </div>
                    <span className={`absolute -top-6 left-0 text-[10px] font-medium px-1.5 py-0.5 rounded whitespace-nowrap ${
                      unknown ? "bg-rose-500 text-white" : "bg-primary text-[oklch(0.14_0.02_260)]"
                    }`}>
                      {b.name} · {b.confidence}%
                    </span>
                  </div>
                );
              })}

              {/* Top overlay bar */}
              <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {streaming && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/90 px-2 py-0.5 text-[10px] font-semibold text-white">
                      <span className="h-1.5 w-1.5 rounded-full bg-white pulse-dot" />
                      LIVE
                    </span>
                  )}
                  <span className="rounded-md bg-black/60 backdrop-blur px-2 py-0.5 text-[11px] font-medium">{selectedCamera}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-white/70 bg-black/60 backdrop-blur rounded-md px-2 py-0.5 tabular-nums">
                  1920×1080 · 30fps · GPU 62%
                </div>
              </div>

              {/* Bottom controls */}
              <div className="absolute bottom-3 left-3 right-3 flex items-center gap-2">
                <button
                  onClick={() => setStreaming((s) => !s)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-semibold transition ${
                    streaming ? "bg-rose-500 text-white hover:brightness-110" : "bg-[var(--grad-primary)] text-[oklch(0.14_0.02_260)]"
                  }`}
                >
                  {streaming ? <><Square className="h-3.5 w-3.5" />Stop</> : <><Play className="h-3.5 w-3.5" />Start</>}
                </button>
                <div className="ml-auto flex items-center gap-1">
                  <button className="h-7 w-7 grid place-items-center rounded-md bg-black/60 backdrop-blur hover:bg-white/10">
                    <Maximize2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Camera Sources" bodyClassName="p-3">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {["Cam-01 · Lobby", "Cam-04 · Server Room", "Cam-07 · Parking", "Cam-12 · Rooftop", "Cam-03 · Main Entry", "Cam-09 · Loading Bay"].map((c) => (
                <button
                  key={c}
                  onClick={() => setSelectedCamera(c)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-[12px] transition ${
                    selectedCamera === c ? "border-primary/60 bg-primary/10 text-primary" : "border-border/60 hover:bg-white/[0.03]"
                  }`}
                >
                  <CameraIcon className="h-3.5 w-3.5" />
                  <span className="truncate">{c}</span>
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-emerald-400 pulse-dot" />
                </button>
              ))}
            </div>
          </SectionCard>
        </div>

        <SectionCard
          title="Live Events"
          subtitle="Streaming recognitions"
          actions={<span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-primary"><span className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />LIVE</span>}
          bodyClassName="p-2 max-h-[720px] overflow-y-auto"
        >
          <div className="space-y-0.5">
            {feed.map((e) => <ActivityFeedItem key={e.id} event={e} />)}
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}