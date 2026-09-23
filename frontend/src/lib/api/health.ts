import { apiFetch } from "./client";

export function getHealth() {
  return apiFetch<{ ok: boolean }>("/health");
}
