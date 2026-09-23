import { apiFetch } from "./client";
import type { Play, SyncResult } from "./types";

export function listPlays(limit = 50) {
  return apiFetch<{ plays: Play[] }>(`/plays?limit=${limit}`);
}

export function syncPlays() {
  return apiFetch<SyncResult>("/sync/plays", { method: "POST" });
}
