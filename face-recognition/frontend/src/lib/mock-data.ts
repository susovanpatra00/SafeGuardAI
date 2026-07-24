// // Mock data + typed fetchers. Swap implementations later to hit real REST API.
// // Endpoint mapping:
// //   fetchDashboardStats  -> GET  /dashboard/stats
// //   fetchRecentActivity  -> GET  /logs?recent=1
// //   fetchRecognitionSeries -> GET /dashboard/stats?series=...
// //   fetchPeople / enrollPerson -> GET/POST /people
// //   uploadDetectionJob / fetchJob -> POST /detect/upload, GET /jobs/{id}
// //   searchByFace -> POST /search/face
// //   fetchLogs -> GET /logs

// export type Person = {
//   id: string;
//   name: string;
//   employeeId: string;
//   role: string;
//   department: string;
//   addedAt: string;
//   avatar: string;
//   notes?: string;
// };

// export type ActivityEvent = {
//   id: string;
//   personName: string;
//   avatar: string;
//   source: string;
//   timestamp: string;
//   confidence: number;
//   status: "known" | "unknown";
// };

// export type Detection = {
//   id: string;
//   name: string;
//   videoTimestamp: string;
//   confidence: number;
//   thumbnail: string;
//   bbox: { x: number; y: number; w: number; h: number };
// };

// export type LogEntry = {
//   id: string;
//   person: string;
//   timestamp: string;
//   source: string;
//   confidence: number;
//   status: "known" | "unknown";
// };

// const FIRST = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Reese", "Emerson", "Rowan", "Sage", "Blake", "Drew", "Kai"];
// const LAST = ["Chen", "Patel", "Kim", "Nguyen", "Silva", "Okafor", "Ivanov", "Rossi", "Tanaka", "Ahmed", "Cohen", "Dubois", "Reyes", "Novak"];
// const ROLES = ["Engineer", "Security Lead", "Ops Manager", "Analyst", "Contractor", "Director", "Technician"];
// const DEPTS = ["Engineering", "Security", "Operations", "Research", "Facilities", "Executive"];
// const CAMERAS = ["Cam-01 · Lobby", "Cam-04 · Server Room", "Cam-07 · Parking", "Cam-12 · Rooftop", "Cam-03 · Main Entry", "Cam-09 · Loading Bay"];

// const seed = (i: number) => {
//   const name = `${FIRST[i % FIRST.length]} ${LAST[(i * 3) % LAST.length]}`;
//   return {
//     name,
//     avatar: `https://i.pravatar.cc/120?img=${(i % 70) + 1}`,
//   };
// };

// export const MOCK_PEOPLE: Person[] = Array.from({ length: 18 }, (_, i) => {
//   const s = seed(i);
//   return {
//     id: `p_${i + 1}`,
//     name: s.name,
//     employeeId: `EMP-${String(1000 + i * 7).padStart(5, "0")}`,
//     role: ROLES[i % ROLES.length],
//     department: DEPTS[i % DEPTS.length],
//     addedAt: new Date(Date.now() - i * 86400000 * 3).toISOString(),
//     avatar: s.avatar,
//   };
// });

// function makeActivity(i: number, offsetMs: number): ActivityEvent {
//   const s = seed(i + 5);
//   const isUnknown = i % 11 === 0;
//   return {
//     id: `a_${Date.now()}_${i}`,
//     personName: isUnknown ? "Unknown Subject" : s.name,
//     avatar: s.avatar,
//     source: CAMERAS[i % CAMERAS.length],
//     timestamp: new Date(Date.now() - offsetMs).toISOString(),
//     confidence: Math.round((isUnknown ? 60 + (i % 15) : 82 + (i * 7) % 17) * 100) / 100,
//     status: isUnknown ? "unknown" : "known",
//   };
// }

// export async function fetchDashboardStats() {
//   return {
//     totalEnrolled: 1284,
//     recognitionsToday: 8432,
//     unknownFlagged: 47,
//     activeCameras: 24,
//     deltas: { totalEnrolled: 12, recognitionsToday: 8.4, unknownFlagged: -3.1, activeCameras: 0 },
//   };
// }

// export async function fetchRecognitionSeries(range: "24h" | "7d") {
//   const points = range === "24h" ? 24 : 7 * 4;
//   const now = Date.now();
//   const step = range === "24h" ? 3600_000 : 6 * 3600_000;
//   return Array.from({ length: points }, (_, i) => {
//     const t = new Date(now - (points - i) * step);
//     const base = range === "24h" ? 220 : 900;
//     const wave = Math.sin(i / 3) * (base * 0.35) + (Math.cos(i / 2) * base * 0.15);
//     const noise = (i * 37) % 60;
//     return {
//       label: range === "24h"
//         ? t.getHours().toString().padStart(2, "0") + ":00"
//         : t.toLocaleDateString(undefined, { weekday: "short" }),
//       recognitions: Math.max(20, Math.round(base + wave + noise)),
//       unknown: Math.max(1, Math.round(((base + wave) / 20) + (i % 5))),
//     };
//   });
// }

// export async function fetchRecentActivity(count = 12): Promise<ActivityEvent[]> {
//   return Array.from({ length: count }, (_, i) => makeActivity(i, i * 45_000));
// }

// export function generateActivityEvent(idx: number): ActivityEvent {
//   return makeActivity(idx, 0);
// }

// export async function fetchMostRecognized() {
//   return MOCK_PEOPLE.slice(0, 6).map((p, i) => ({
//     person: p,
//     count: 342 - i * 34 - (i * 7) % 10,
//   }));
// }

// export async function fetchPeople(): Promise<Person[]> {
//   return MOCK_PEOPLE;
// }

// export async function enrollPerson(_input: Omit<Person, "id" | "addedAt" | "avatar"> & { photo?: File | null }): Promise<Person> {
//   const id = `p_${Date.now()}`;
//   return {
//     id,
//     name: _input.name,
//     employeeId: _input.employeeId,
//     role: _input.role,
//     department: _input.department,
//     addedAt: new Date().toISOString(),
//     avatar: `https://i.pravatar.cc/120?u=${id}`,
//     notes: _input.notes,
//   };
// }

// export async function uploadDetectionJob(_file: File): Promise<{ jobId: string }> {
//   return { jobId: `job_${Date.now()}` };
// }

// export async function fetchDetections(): Promise<Detection[]> {
//   return Array.from({ length: 8 }, (_, i) => {
//     const s = seed(i + 2);
//     return {
//       id: `d_${i}`,
//       name: i % 6 === 0 ? "Unknown" : s.name,
//       videoTimestamp: `00:${String(Math.floor(i * 12 + 5)).padStart(2, "0")}:${String((i * 17) % 60).padStart(2, "0")}`,
//       confidence: Math.round((72 + (i * 13) % 27) * 100) / 100,
//       thumbnail: s.avatar,
//       bbox: { x: 10 + (i * 60) % 400, y: 40 + (i * 40) % 200, w: 90, h: 110 },
//     };
//   });
// }

// export async function searchByFace(): Promise<Array<{ id: string; person: string; source: string; timestamp: string; confidence: number; thumbnail: string; }>> {
//   return Array.from({ length: 12 }, (_, i) => {
//     const s = seed(i + 1);
//     return {
//       id: `m_${i}`,
//       person: s.name,
//       source: CAMERAS[i % CAMERAS.length],
//       timestamp: new Date(Date.now() - i * 3_600_000 * 5).toISOString(),
//       confidence: Math.round((78 + (i * 11) % 21) * 100) / 100,
//       thumbnail: s.avatar,
//     };
//   });
// }

// export async function fetchLogs(): Promise<LogEntry[]> {
//   return Array.from({ length: 42 }, (_, i) => {
//     const s = seed(i);
//     const unk = i % 9 === 0;
//     return {
//       id: `l_${i}`,
//       person: unk ? "Unknown" : s.name,
//       timestamp: new Date(Date.now() - i * 1_800_000).toISOString(),
//       source: CAMERAS[i % CAMERAS.length],
//       confidence: Math.round((unk ? 55 + (i % 15) : 82 + (i * 5) % 17) * 100) / 100,
//       status: unk ? "unknown" : "known",
//     };
//   });
// }

// export function formatRelative(iso: string): string {
//   const diff = Date.now() - new Date(iso).getTime();
//   const s = Math.floor(diff / 1000);
//   if (s < 60) return `${s}s ago`;
//   const m = Math.floor(s / 60);
//   if (m < 60) return `${m}m ago`;
//   const h = Math.floor(m / 60);
//   if (h < 24) return `${h}h ago`;
//   return `${Math.floor(h / 24)}d ago`;
// }










// src/lib/mock-data.ts
//
// Originally pure mock data. Now wired to the real SafeGuardAI backend --
// filename kept as-is so the 6 files importing from "@/lib/mock-data"
// don't need path changes. Endpoint mapping:
//
//   fetchDashboardStats    -> GET  /dashboard/stats
//   fetchRecentActivity    -> GET  /logs (mapped to activity feed shape)
//   fetchRecognitionSeries -> GET  /logs, bucketed client-side (no dedicated
//                              aggregation endpoint on the backend yet)
//   fetchPeople            -> GET  /people
//   enrollPerson           -> POST /people (multipart: fields + photo)
//   uploadDetectionJob     -> POST /detect/upload (synchronous; for video
//                              uploads we follow up with GET /logs?source=...
//                              since the backend doesn't return per-frame
//                              bboxes for video, only aggregate counts)
//   fetchLogs              -> GET  /logs
//
//   NOT YET WIRED (backend endpoint doesn't exist -- still mocked):
//   searchByFace            -- needs POST /search/face on the backend
//   generateActivityEvent   -- used only by the Detect·Live mock stream,
//                              which is still a UI mock (no real RTSP yet)

import { API_BASE_URL, toFileUrl, initialsAvatar } from "@/lib/api-config";

export type Person = {
  id: string;
  name: string;
  employeeId: string;
  role: string;
  department: string;
  addedAt: string;
  avatar: string;
  notes?: string;
};

export type ActivityEvent = {
  id: string;
  personName: string;
  avatar: string;
  source: string;
  timestamp: string;
  confidence: number; // 0-100
  status: "known" | "unknown";
};

export type Detection = {
  id: string;
  name: string;
  videoTimestamp: string;
  confidence: number; // 0-100
  thumbnail: string;
  bbox: { x: number; y: number; w: number; h: number };
};

export type LogEntry = {
  id: string;
  person: string;
  timestamp: string;
  source: string;
  confidence: number; // 0-100
  status: "known" | "unknown";
};

// ---------- internal helpers ----------

type BackendPerson = {
  id: number;
  name: string;
  employee_id: string | null;
  role: string | null;
  department: string | null;
  notes: string | null;
  photo_path: string | null;
  created_at: string;
};

type BackendLogEntry = {
  id: number;
  person_id: number | null;
  person_name: string | null;
  source: string;
  timestamp_in_video: number | null;
  confidence: number; // 0-1 cosine similarity
  status: "known" | "unknown" | "spoof";
  created_at: string;
};

function toPercent(similarity: number): number {
  return Math.max(0, Math.round(similarity * 100));
}

function mapBackendPerson(p: BackendPerson): Person {
  return {
    id: String(p.id),
    name: p.name,
    employeeId: p.employee_id ?? "—",
    role: p.role ?? "—",
    department: p.department ?? "—",
    addedAt: p.created_at,
    avatar: toFileUrl(p.photo_path) ?? initialsAvatar(p.name),
    notes: p.notes ?? undefined,
  };
}

// Cached lookup of person photos, used to give logs/activity real avatars
// instead of generic placeholders. Re-fetched each call for simplicity --
// fine at current scale; revisit with real caching if /people grows large.
async function getPersonPhotoMap(): Promise<Map<number, string>> {
  const people = await fetchPeopleRaw();
  const map = new Map<number, string>();
  for (const p of people) {
    const url = toFileUrl(p.photo_path);
    if (url) map.set(p.id, url);
  }
  return map;
}

async function fetchPeopleRaw(): Promise<BackendPerson[]> {
  const res = await fetch(`${API_BASE_URL}/people`);
  if (!res.ok) throw new Error(`Failed to fetch people: ${res.status}`);
  return res.json();
}

function formatVideoTimestamp(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `00:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

// ---------- Dashboard ----------

export async function fetchDashboardStats() {
  const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
  if (!res.ok) throw new Error(`Failed to fetch dashboard stats: ${res.status}`);
  const s = await res.json();
  return {
    totalEnrolled: s.total_enrolled_faces,
    recognitionsToday: s.recognitions_today,
    unknownFlagged: s.unknown_faces_flagged_today,
    activeCameras: s.active_sources_today,
    // Backend doesn't compute trend deltas yet -- zeroed rather than faked.
    deltas: { totalEnrolled: 0, recognitionsToday: 0, unknownFlagged: 0, activeCameras: 0 },
  };
}

export async function fetchRecognitionSeries(range: "24h" | "7d") {
  const points = range === "24h" ? 24 : 7 * 4;
  const stepMs = range === "24h" ? 3600_000 : 6 * 3600_000;
  const now = Date.now();

  // Pull a generous batch of recent logs and bucket client-side. No dedicated
  // aggregation endpoint exists on the backend yet -- fine at current scale,
  // but worth moving server-side (a GROUP BY query) once log volume grows.
  const res = await fetch(`${API_BASE_URL}/logs?limit=2000`);
  if (!res.ok) throw new Error(`Failed to fetch logs for series: ${res.status}`);
  const { events } = (await res.json()) as { events: BackendLogEntry[] };

  return Array.from({ length: points }, (_, i) => {
    const bucketEnd = now - (points - 1 - i) * stepMs;
    const bucketStart = bucketEnd - stepMs;
    const inBucket = events.filter((e) => {
      const t = new Date(e.created_at).getTime();
      return t >= bucketStart && t < bucketEnd;
    });
    const label =
      range === "24h"
        ? new Date(bucketEnd).getHours().toString().padStart(2, "0") + ":00"
        : new Date(bucketEnd).toLocaleDateString(undefined, { weekday: "short" });

    return {
      label,
      recognitions: inBucket.length,
      unknown: inBucket.filter((e) => e.status === "unknown").length,
    };
  });
}

export async function fetchRecentActivity(count = 12): Promise<ActivityEvent[]> {
  const res = await fetch(`${API_BASE_URL}/logs?limit=${count}`);
  if (!res.ok) throw new Error(`Failed to fetch recent activity: ${res.status}`);
  const { events } = (await res.json()) as { events: BackendLogEntry[] };
  const photoMap = await getPersonPhotoMap();

  return events.map((e) => ({
    id: String(e.id),
    personName: e.person_name ?? "Unknown Subject",
    avatar: (e.person_id && photoMap.get(e.person_id)) || initialsAvatar(e.person_name ?? "Unknown"),
    source: e.source,
    timestamp: e.created_at,
    confidence: toPercent(e.confidence),
    status: e.status === "spoof" ? "unknown" : e.status, // UI doesn't have a spoof state yet
  }));
}

// Still used only by the Detect·Live mock stream (no real camera feed wired
// up yet) -- kept as a pure client-side generator, not a backend call.
const FIRST = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Reese"];
const LAST = ["Chen", "Patel", "Kim", "Nguyen", "Silva", "Okafor", "Ivanov", "Rossi", "Tanaka", "Ahmed"];
const CAMERAS = ["Cam-01 · Lobby", "Cam-04 · Server Room", "Cam-07 · Parking", "Cam-12 · Rooftop"];

export function generateActivityEvent(idx: number): ActivityEvent {
  const name = `${FIRST[idx % FIRST.length]} ${LAST[(idx * 3) % LAST.length]}`;
  const isUnknown = idx % 11 === 0;
  return {
    id: `sim_${Date.now()}_${idx}`,
    personName: isUnknown ? "Unknown Subject" : name,
    avatar: initialsAvatar(name),
    source: CAMERAS[idx % CAMERAS.length],
    timestamp: new Date().toISOString(),
    confidence: isUnknown ? 60 + (idx % 15) : 82 + ((idx * 7) % 17),
    status: isUnknown ? "unknown" : "known",
  };
}

export async function fetchMostRecognized() {
  const [people, logsRes] = await Promise.all([
    fetchPeopleRaw(),
    fetch(`${API_BASE_URL}/logs?status=known&limit=2000`),
  ]);
  if (!logsRes.ok) throw new Error(`Failed to fetch logs for leaderboard: ${logsRes.status}`);
  const { events } = (await logsRes.json()) as { events: BackendLogEntry[] };

  const counts = new Map<number, number>();
  for (const e of events) {
    if (e.person_id === null) continue;
    counts.set(e.person_id, (counts.get(e.person_id) ?? 0) + 1);
  }

  const peopleById = new Map(people.map((p) => [p.id, p]));

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([personId, count]) => {
      const p = peopleById.get(personId);
      return {
        person: p ? mapBackendPerson(p) : { id: String(personId), name: "Unknown", employeeId: "—", role: "—", department: "—", addedAt: "", avatar: initialsAvatar("?") },
        count,
      };
    });
}

// ---------- People ----------

export async function fetchPeople(): Promise<Person[]> {
  const people = await fetchPeopleRaw();
  return people.map(mapBackendPerson);
}

export async function enrollPerson(
  input: { name: string; employeeId: string; role: string; department: string; notes: string; photo?: File | null },
): Promise<Person> {
  if (!input.photo) throw new Error("A photo is required to enroll a person");

  const form = new FormData();
  form.append("name", input.name);
  if (input.employeeId) form.append("employee_id", input.employeeId);
  if (input.role) form.append("role", input.role);
  if (input.department) form.append("department", input.department);
  if (input.notes) form.append("notes", input.notes);
  form.append("photo", input.photo);

  const res = await fetch(`${API_BASE_URL}/people`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Enrollment failed: ${res.status}`);
  }
  const data = await res.json();
  return mapBackendPerson(data.person);
}

// ---------- Detect / Upload ----------
// NOTE: signature changed from the original mock (which only returned
// {jobId} for a fake job-polling flow) to return the full result directly,
// since the backend processes uploads synchronously. detect.upload.tsx was
// updated accordingly -- see that file for the corresponding UI changes.

export type UploadDetectionResult = {
  mediaType: "image" | "video";
  outputUrl: string | null;
  totalDetections: number;
  knownCount: number;
  unknownCount: number;
  detections: Detection[];
};

export async function uploadDetectionJob(
  file: File,
  options?: { confidenceThreshold?: number; sourceLabel?: string },
): Promise<UploadDetectionResult> {
  const sourceLabel = options?.sourceLabel ?? `Upload · ${file.name} · ${Date.now()}`;

  const form = new FormData();
  form.append("file", file);
  form.append("confidence_threshold", String((options?.confidenceThreshold ?? 40) / 100));
  form.append("source_label", sourceLabel);

  const res = await fetch(`${API_BASE_URL}/detect/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Upload failed: ${res.status}`);
  }
  const data = await res.json();

  if (data.media_type === "image") {
    const detections: Detection[] = data.detections.map((d: any, i: number) => ({
      id: `img_${i}`,
      name: d.person_name ?? "Unknown",
      videoTimestamp: "—",
      confidence: toPercent(d.confidence),
      thumbnail: initialsAvatar(d.person_name ?? "Unknown"),
      bbox: { x: d.bbox[0], y: d.bbox[1], w: d.bbox[2] - d.bbox[0], h: d.bbox[3] - d.bbox[1] },
    }));
    return {
      mediaType: "image",
      outputUrl: toFileUrl(data.output_path),
      totalDetections: data.total_detections,
      knownCount: data.known_count,
      unknownCount: data.unknown_count,
      detections,
    };
  }

  // Video: backend only returns aggregate counts, not per-frame bboxes.
  // Follow up with a logs query filtered to this exact source label to get
  // row-level detail (timestamp, confidence, status, person) for the table.
  const logsRes = await fetch(`${API_BASE_URL}/logs?source=${encodeURIComponent(sourceLabel)}&limit=500`);
  const logsData = logsRes.ok ? await logsRes.json() : { events: [] };
  const detections: Detection[] = (logsData.events as BackendLogEntry[]).map((e) => ({
    id: String(e.id),
    name: e.person_name ?? "Unknown",
    videoTimestamp: formatVideoTimestamp(e.timestamp_in_video),
    confidence: toPercent(e.confidence),
    thumbnail: initialsAvatar(e.person_name ?? "Unknown"),
    bbox: { x: 0, y: 0, w: 0, h: 0 }, // not used by the table UI for video rows
  }));

  return {
    mediaType: "video",
    outputUrl: toFileUrl(data.output_path),
    totalDetections: data.total_detections,
    knownCount: data.known_count,
    unknownCount: data.unknown_count,
    detections,
  };
}

// ---------- Search (NOT YET WIRED -- backend endpoint doesn't exist) ----------

export async function searchByFace(): Promise<
  Array<{ id: string; person: string; source: string; timestamp: string; confidence: number; thumbnail: string }>
> {
  // TODO: replace with POST /search/face once that endpoint is built.
  // Left as mock data so the Search page doesn't break in the meantime.
  return Array.from({ length: 12 }, (_, i) => {
    const name = `${FIRST[i % FIRST.length]} ${LAST[(i * 3) % LAST.length]}`;
    return {
      id: `m_${i}`,
      person: name,
      source: CAMERAS[i % CAMERAS.length],
      timestamp: new Date(Date.now() - i * 3_600_000 * 5).toISOString(),
      confidence: Math.round((78 + (i * 11) % 21) * 100) / 100,
      thumbnail: initialsAvatar(name),
    };
  });
}

// ---------- Logs ----------

export async function fetchLogs(): Promise<LogEntry[]> {
  const res = await fetch(`${API_BASE_URL}/logs?limit=200`);
  if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`);
  const { events } = (await res.json()) as { events: BackendLogEntry[] };

  return events.map((e) => ({
    id: String(e.id),
    person: e.person_name ?? "Unknown",
    timestamp: e.created_at,
    source: e.source,
    confidence: toPercent(e.confidence),
    status: e.status === "spoof" ? "unknown" : e.status,
  }));
}

// ---------- Shared helpers ----------

export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}