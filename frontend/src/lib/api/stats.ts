import { apiFetch } from "./client";
import type {
  DayBucket,
  HourBucket,
  StatsSummary,
  TopArtist,
  TopTrack,
} from "./types";

/** Minutes to add to UTC to get local time (JS getTimezoneOffset is inverted). */
export function localTzOffsetMinutes() {
  return -new Date().getTimezoneOffset();
}

export function getStatsSummary() {
  return apiFetch<StatsSummary>("/stats/summary");
}

export function getTopTracks(
  limit = 10,
  timeRange: "short_term" | "medium_term" | "long_term" = "long_term",
) {
  return apiFetch<{ tracks: TopTrack[]; time_range: string }>(
    `/stats/top-tracks?limit=${limit}&time_range=${timeRange}`,
  );
}

export function getTopArtists(
  limit = 10,
  timeRange: "short_term" | "medium_term" | "long_term" = "long_term",
) {
  return apiFetch<{ artists: TopArtist[]; time_range: string }>(
    `/stats/top-artists?limit=${limit}&time_range=${timeRange}`,
  );
}

export function getListeningByHour(tzOffsetMinutes = localTzOffsetMinutes()) {
  return apiFetch<{ hours: HourBucket[]; tz_offset_minutes: number }>(
    `/stats/listening-by-hour?tz_offset_minutes=${tzOffsetMinutes}`,
  );
}

export function getListeningByDay(
  days = 30,
  tzOffsetMinutes = localTzOffsetMinutes(),
) {
  return apiFetch<{ days: DayBucket[]; tz_offset_minutes: number }>(
    `/stats/listening-by-day?days=${days}&tz_offset_minutes=${tzOffsetMinutes}`,
  );
}

export type ImageCoverage = {
  unique_tracks: number;
  with_image: number;
  missing: number;
};

export type EnrichImagesResult = {
  fetched: number;
  updated: number;
  batches_run: number;
} & ImageCoverage;

export function getImageCoverage() {
  return apiFetch<ImageCoverage>("/tracks/image-coverage");
}

export function enrichAlbumImages(opts?: {
  limit?: number;
  batches?: number;
  trackIds?: string[];
}) {
  const limit = opts?.limit ?? 50;
  const batches = opts?.batches ?? 20;
  const params = new URLSearchParams({
    limit: String(limit),
    batches: String(batches),
  });
  return apiFetch<EnrichImagesResult>(`/tracks/enrich-images?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      track_ids: opts?.trackIds ?? null,
      limit,
      batches,
    }),
  });
}

export type MetaCoverage = {
  unique_tracks: number;
  with_meta: number;
  with_features: number;
  with_genres: number;
  missing_features: number;
};

export function getMetaCoverage() {
  return apiFetch<MetaCoverage>("/tracks/meta-coverage");
}

export function enrichTrackFeatures(opts?: { batches?: number; limit?: number }) {
  const params = new URLSearchParams({
    batches: String(opts?.batches ?? 5),
    limit: String(opts?.limit ?? 40),
  });
  return apiFetch<{ enriched: number } & MetaCoverage>(
    `/tracks/enrich-features?${params}`,
    { method: "POST" },
  );
}
