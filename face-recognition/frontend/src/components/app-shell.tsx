import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  UserPlus,
  Upload,
  Radio,
  Search,
  ScrollText,
  ShieldCheck,
  Cpu,
  Bell,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV: Array<{ to: string; label: string; icon: typeof LayoutDashboard; exact?: boolean }> = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/enroll", label: "Enroll", icon: UserPlus },
  { to: "/detect/upload", label: "Detect · Upload", icon: Upload },
  { to: "/detect/live", label: "Detect · Live", icon: Radio },
  { to: "/search", label: "Search", icon: Search },
  { to: "/logs", label: "Logs & Reports", icon: ScrollText },
];

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return now;
}

export function AppShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle?: string }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const clock = useClock();

  return (
    <div className="min-h-screen w-full flex text-foreground">
      {/* Sidebar */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border/60 bg-[oklch(0.11_0.015_265)]/80 backdrop-blur-xl sticky top-0 h-screen">
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-border/60">
          <div className="relative h-8 w-8 rounded-lg grid place-items-center bg-[var(--grad-primary)] shadow-[var(--shadow-glow)]">
            <ShieldCheck className="h-4.5 w-4.5 text-[oklch(0.14_0.02_260)]" strokeWidth={2.5} />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-[13px] font-semibold tracking-tight">SafeGuardAI</span>
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Face Intelligence</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <div className="px-2 pb-2 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Workspace</div>
          {NAV.map((item) => {
            const active = item.exact ? pathname === item.to : pathname === item.to || pathname.startsWith(item.to + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to as never}
                className={cn(
                  "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-all",
                  active
                    ? "bg-[var(--accent-cyan-soft)] text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]",
                )}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[2px] rounded-r bg-primary shadow-[0_0_10px_var(--accent-cyan)]" />
                )}
                <Icon className="h-4 w-4" strokeWidth={2} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-border/60">
          <div className="glass-card p-3 text-[11px] text-muted-foreground">
            <div className="flex items-center gap-2 text-foreground text-[12px] font-medium">
              <Cpu className="h-3.5 w-3.5 text-primary" />
              GPU · NVIDIA A100
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Utilization</span>
              <span className="text-primary font-medium">62%</span>
            </div>
            <div className="mt-1 h-1 rounded-full bg-white/5 overflow-hidden">
              <div className="h-full w-[62%] bg-[var(--grad-primary)]" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-20 h-16 border-b border-border/60 bg-[oklch(0.12_0.015_265)]/70 backdrop-blur-xl">
          <div className="h-full px-6 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-[15px] font-semibold tracking-tight truncate">{title}</h1>
              {subtitle && <p className="text-[12px] text-muted-foreground truncate">{subtitle}</p>}
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inset-0 rounded-full bg-primary pulse-dot" />
                </span>
                <span className="text-foreground">Live</span>
                <span className="mx-2 h-3 w-px bg-border" />
                <span>GPU 62%</span>
                <span className="mx-2 h-3 w-px bg-border" />
                <span className="tabular-nums">
                  {clock ? clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
                </span>
              </div>
              <button className="h-8 w-8 grid place-items-center rounded-lg border border-border/60 hover:bg-white/5 transition">
                <Bell className="h-4 w-4 text-muted-foreground" />
              </button>
              <button className="h-8 w-8 grid place-items-center rounded-lg border border-border/60 hover:bg-white/5 transition">
                <Settings className="h-4 w-4 text-muted-foreground" />
              </button>
              <div className="h-8 w-8 rounded-full bg-[var(--grad-primary)] grid place-items-center text-[11px] font-semibold text-[oklch(0.14_0.02_260)]">
                SG
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 p-6 lg:p-8 animate-slide-up">{children}</main>
      </div>
    </div>
  );
}
