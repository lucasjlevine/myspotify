import { apiFetch } from "./client";
import type {
  ModelsResponse,
  PredictResponse,
  PromptSearchResponse,
  WindowPreset,
} from "./types";

export function listModels() {
  return apiFetch<ModelsResponse>("/predict/models");
}

export function listWindows() {
  return apiFetch<{ windows: WindowPreset[] }>("/predict/windows");
}

export function predictNext(opts: {
  k?: number;
  model?: string;
  trackId?: string | null;
  window?: string;
  tzOffsetMinutes?: number;
}) {
  const params = new URLSearchParams();
  params.set("k", String(opts.k ?? 5));
  if (opts.model) params.set("model", opts.model);
  if (opts.trackId && (opts.window ?? "latest") === "latest") {
    params.set("track_id", opts.trackId);
  }
  if (opts.window) params.set("window", opts.window);
  if (opts.tzOffsetMinutes != null) {
    params.set("tz_offset_minutes", String(opts.tzOffsetMinutes));
  }
  return apiFetch<PredictResponse>(`/predict/next?${params.toString()}`);
}

export function searchByPrompt(opts: {
  q: string;
  k?: number;
  model?: string;
}) {
  const params = new URLSearchParams();
  params.set("q", opts.q);
  params.set("k", String(opts.k ?? 10));
  params.set("model", opts.model ?? "embedding");
  return apiFetch<PromptSearchResponse>(`/predict/prompt?${params.toString()}`);
}
