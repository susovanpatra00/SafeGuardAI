// src/lib/api-config.ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Backend static files are mounted at /files, serving the `data/` directory.
// Stored paths in the DB look like "data/enrolled/x.jpg" or
// "data/uploads/outputs/y.mp4" -- strip the leading "data/" and prefix
// with the API base + /files to get a real, browser-loadable URL.
export function toFileUrl(storedPath: string | null | undefined): string | null {
  if (!storedPath) return null;
  const relative = storedPath.startsWith("data/") ? storedPath.slice(5) : storedPath;
  return `${API_BASE_URL}/files/${relative}`;
}

// Fallback avatar for people/events without a real photo on file --
// deterministic per-name so the same person always gets the same avatar.
export function initialsAvatar(name: string): string {
  return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}&backgroundType=gradientLinear`;
}