import { apiFetch } from "./client";
import type { ModelsResponse, PredictResponse } from "./types";

export function listModels() {
  return apiFetch<ModelsResponse>("/predict/models");
}

export function predictNext(opts: {
  k?: number;
  model?: string;
  trackId?: string | null;
}) {
  const params = new URLSearchParams();
  params.set("k", String(opts.k ?? 5));
  if (opts.model) params.set("model", opts.model);
  if (opts.trackId) params.set("track_id", opts.trackId);
  return apiFetch<PredictResponse>(`/predict/next?${params.toString()}`);
}
