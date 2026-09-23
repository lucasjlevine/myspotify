import { apiFetch } from "./client";
import type {
  DayBucket,
  HourBucket,
  StatsSummary,
  TopArtist,
  TopTrack,
} from "./types";

export function getStatsSummary() {
  return apiFetch<StatsSummary>("/stats/summary");
}

export function getTopTracks(limit = 10) {
  return apiFetch<{ tracks: TopTrack[] }>(`/stats/top-tracks?limit=${limit}`);
}

export function getTopArtists(limit = 10) {
  return apiFetch<{ artists: TopArtist[] }>(
    `/stats/top-artists?limit=${limit}`,
  );
}

export function getListeningByHour() {
  return apiFetch<{ hours: HourBucket[] }>("/stats/listening-by-hour");
}

export function getListeningByDay(days = 30) {
  return apiFetch<{ days: DayBucket[] }>(
    `/stats/listening-by-day?days=${days}`,
  );
}
