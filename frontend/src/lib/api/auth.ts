import { apiFetch } from "./client";
import type { AuthStatus } from "./types";

export function getAuthStatus() {
  return apiFetch<AuthStatus>("/auth/status");
}

/** Full-page navigation into Spotify OAuth (proxied to backend). */
export function connectSpotifyUrl() {
  return "/api/authorize";
}
