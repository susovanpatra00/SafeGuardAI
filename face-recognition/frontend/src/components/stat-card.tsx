import { useEffect, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

function useCountUp(target: number, duration = 900) {
  const [value, setValue] = useState(0);
  const startRef = useRef<number | null>(null);
  useEffect(() => {
    let raf = 0;
    const step = (t: number) => {
      if (startRef.current === null) startRef.current = t;
      const p = Math.min(1, (t - startRef.current) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: number;
  delta?: number;
  icon: LucideIcon;
  accent?: boolean;
}) {
  const count = useCountUp(value);
  const up = (delta ?? 0) >= 0;
  return (
    <div className="glass-card relative overflow-hidden p-5 group transition-all hover:-translate-y-0.5 hover:border-primary/30">
      <div className="pointer-events-none absolute -top-16 -right-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
          <div className={cn("text-3xl font-semibold tabular-nums tracking-tight", accent && "text-gradient")}>
            {count.toLocaleString()}
          </div>
        </div>
        <div className="h-9 w-9 grid place-items-center rounded-lg bg-white/[0.03] border border-border/60 text-primary">
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {delta !== undefined && (
        <div className="mt-3 flex items-center gap-1 text-[11px]">
          <span className={cn("inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-medium",
            up ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400")}>
            {up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta)}%
          </span>
          <span className="text-muted-foreground">vs last period</span>
        </div>
      )}
    </div>
  );
}