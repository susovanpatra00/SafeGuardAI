import type { ActivityEvent } from "@/lib/mock-data";
import { formatRelative } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export function ActivityFeedItem({ event, blurUnknown = false }: { event: ActivityEvent; blurUnknown?: boolean }) {
  const unknown = event.status === "unknown";
  return (
    <div className="animate-slide-up flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-white/[0.03] transition">
      <div className="relative">
        <img
          src={event.avatar}
          alt=""
          className={cn("h-9 w-9 rounded-full object-cover ring-1 ring-border", unknown && blurUnknown && "grayscale blur-[3px]")}
        />
        <span className={cn("absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-background",
          unknown ? "bg-rose-500" : "bg-emerald-400")} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium truncate">{event.personName}</span>
          <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wider",
            unknown ? "bg-rose-500/10 text-rose-400" : "bg-primary/10 text-primary")}>
            {event.confidence}%
          </span>
        </div>
        <div className="text-[11px] text-muted-foreground truncate">{event.source}</div>
      </div>
      <div className="text-[11px] text-muted-foreground tabular-nums shrink-0">{formatRelative(event.timestamp)}</div>
    </div>
  );
}