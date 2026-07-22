import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, Search, ScanFace, Edit2, Trash2, Plus, Check } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SectionCard } from "@/components/section-card";
import { fetchPeople, enrollPerson, type Person } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/enroll")({
  head: () => ({
    meta: [
      { title: "Enroll — SafeGuardAI" },
      { name: "description", content: "Enroll people into your face intelligence directory." },
      { property: "og:title", content: "Enroll · SafeGuardAI" },
      { property: "og:description", content: "Add and manage enrolled identities." },
    ],
  }),
  component: EnrollPage,
});

function EnrollPage() {
  const people = useQuery({ queryKey: ["people"], queryFn: fetchPeople });
  const [preview, setPreview] = useState<string | null>(null);
  const [processed, setProcessed] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [query, setQuery] = useState("");
  const [dept, setDept] = useState<string>("all");
  const [form, setForm] = useState({ name: "", employeeId: "", role: "", department: "", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const [added, setAdded] = useState<Person[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = useCallback((f: File) => {
    const url = URL.createObjectURL(f);
    setPreview(url);
    setProcessed(false);
    setTimeout(() => setProcessed(true), 900);
  }, []);

  const list = [...added, ...(people.data ?? [])].filter((p) => {
    const q = query.toLowerCase();
    return (
      (dept === "all" || p.department === dept) &&
      (!q || p.name.toLowerCase().includes(q) || p.employeeId.toLowerCase().includes(q))
    );
  });

  const depts = Array.from(new Set((people.data ?? []).map((p) => p.department)));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) return;
    setSubmitting(true);
    const p = await enrollPerson(form);
    setAdded((prev) => [p, ...prev]);
    setForm({ name: "", employeeId: "", role: "", department: "", notes: "" });
    setPreview(null);
    setProcessed(false);
    setSubmitting(false);
  };

  return (
    <AppShell title="Enroll" subtitle="Add new identities to the recognition directory">
      <div className="grid gap-4 lg:grid-cols-5">
        <SectionCard className="lg:col-span-2" title="Upload Photo" subtitle="Drag a clear front-facing photo">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault(); setDragOver(false);
              const f = e.dataTransfer.files?.[0]; if (f) onFile(f);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "relative aspect-square rounded-xl border border-dashed transition-all cursor-pointer overflow-hidden",
              dragOver ? "border-primary bg-primary/5 glow-ring" : "border-border/70 hover:border-primary/60 bg-white/[0.02]",
            )}
          >
            {preview ? (
              <>
                <img src={preview} alt="" className="absolute inset-0 h-full w-full object-cover" />
                {!processed && (
                  <div className="absolute inset-0 overflow-hidden">
                    <div className="scan-line absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-primary/40 to-transparent" />
                  </div>
                )}
                {processed && (
                  <>
                    <div className="absolute rounded border-2 border-primary shadow-[0_0_20px_var(--accent-cyan)]"
                      style={{ left: "22%", top: "18%", width: "56%", height: "62%" }}>
                      <span className="absolute -top-5 left-0 text-[10px] font-medium bg-primary text-[oklch(0.14_0.02_260)] px-1.5 py-0.5 rounded">
                        FACE · 98.7%
                      </span>
                    </div>
                    <div className="absolute bottom-2 left-2 flex items-center gap-1.5 text-[11px] bg-black/60 backdrop-blur rounded-full px-2 py-1">
                      <Check className="h-3 w-3 text-emerald-400" />
                      <span>Face detected</span>
                    </div>
                  </>
                )}
              </>
            ) : (
              <div className="absolute inset-0 grid place-items-center text-center p-6">
                <div>
                  <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 grid place-items-center mb-3">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  <p className="text-[13px] font-medium">Drop photo here</p>
                  <p className="text-[11px] text-muted-foreground mt-1">PNG or JPG · up to 10MB</p>
                </div>
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
            />
          </div>
        </SectionCard>

        <SectionCard className="lg:col-span-3" title="Identity Details" subtitle="These fields are indexed for search">
          <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" placeholder="Alex Chen" />
            </Field>
            <Field label="Employee ID">
              <input value={form.employeeId} onChange={(e) => setForm({ ...form, employeeId: e.target.value })} className="input" placeholder="EMP-01023" />
            </Field>
            <Field label="Role">
              <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input" placeholder="Security Lead" />
            </Field>
            <Field label="Department">
              <input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className="input" placeholder="Operations" />
            </Field>
            <Field label="Notes" className="sm:col-span-2">
              <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} className="input resize-none" placeholder="Access level, clearances, etc." />
            </Field>
            <div className="sm:col-span-2 flex items-center justify-between pt-1">
              <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                <ScanFace className="h-3.5 w-3.5 text-primary" />
                {processed ? "1 face embedding ready" : "Awaiting face detection"}
              </div>
              <button
                type="submit"
                disabled={submitting || !form.name}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--grad-primary)] px-4 py-2 text-[12px] font-semibold text-[oklch(0.14_0.02_260)] shadow-[var(--shadow-glow)] hover:brightness-110 transition disabled:opacity-40"
              >
                <Plus className="h-4 w-4" />
                {submitting ? "Enrolling…" : "Enroll Person"}
              </button>
            </div>
          </form>
          <style>{`.input{width:100%;background:rgba(255,255,255,0.03);border:1px solid oklch(0.28 0.02 260 / 0.6);border-radius:10px;padding:9px 12px;font-size:13px;color:inherit;outline:none;transition:all .15s}
          .input:focus{border-color:var(--accent-cyan);box-shadow:0 0 0 3px oklch(0.82 0.15 220 / 0.15)}
          .input::placeholder{color:oklch(0.55 0.02 250)}`}</style>
        </SectionCard>
      </div>

      <SectionCard
        className="mt-6"
        title="Enrolled People"
        subtitle={`${list.length} identities in your directory`}
        actions={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or ID…"
                className="pl-8 pr-3 py-1.5 text-[12px] rounded-lg bg-white/[0.03] border border-border/60 outline-none focus:border-primary/60 w-56" />
            </div>
            <select value={dept} onChange={(e) => setDept(e.target.value)} className="text-[12px] bg-white/[0.03] border border-border/60 rounded-lg px-2 py-1.5 outline-none">
              <option value="all">All departments</option>
              {depts.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        }
      >
        <div className="grid gap-3 grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
          {list.map((p) => (
            <div key={p.id} className="animate-slide-up group relative rounded-xl border border-border/60 bg-white/[0.02] p-4 hover:border-primary/40 hover:bg-white/[0.04] transition">
              <div className="flex items-center gap-3">
                <img src={p.avatar} alt="" className="h-12 w-12 rounded-full object-cover ring-1 ring-border" />
                <div className="min-w-0">
                  <div className="text-[13px] font-semibold truncate">{p.name}</div>
                  <div className="text-[11px] text-muted-foreground truncate">{p.role} · {p.department}</div>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="tabular-nums">{p.employeeId}</span>
                <span>{new Date(p.addedAt).toLocaleDateString()}</span>
              </div>
              <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition">
                <button className="h-6 w-6 grid place-items-center rounded-md bg-white/5 hover:bg-white/10"><Edit2 className="h-3 w-3" /></button>
                <button className="h-6 w-6 grid place-items-center rounded-md bg-white/5 hover:bg-rose-500/20 hover:text-rose-400"><Trash2 className="h-3 w-3" /></button>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </AppShell>
  );
}

function Field({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={cn("flex flex-col gap-1.5", className)}>
      <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}