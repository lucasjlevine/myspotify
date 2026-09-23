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

export function getTopTracks(limit = 10) {
  return apiFetch<{ tracks: TopTrack[] }>(`/stats/top-tracks?limit=${limit}`);
}

export function getTopArtists(limit = 10) {
  return apiFetch<{ artists: TopArtist[] }>(
    `/stats/top-artists?limit=${limit}`,
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

export function enrichAlbumImages(limit = 100) {
  return apiFetch<{ fetched: number; updated: number; remaining_sample: number }>(
    `/tracks/enrich-images?limit=${limit}`,
    { method: "POST" },
  );
}
