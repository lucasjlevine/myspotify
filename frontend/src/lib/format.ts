export function formatDuration(ms: number): string {
  if (!ms || ms < 0) return "0m";
  const totalMinutes = Math.round(ms / 60_000);
  if (totalMinutes < 60) return `${totalMinutes}m`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours < 24) return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  return remHours ? `${days}d ${remHours}h` : `${days}d`;
}

export function formatPlayedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatDayLabel(day: string): string {
  const date = new Date(`${day}T12:00:00`);
  if (Number.isNaN(date.getTime())) return day;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatHourLabel(hour: number): string {
  const date = new Date();
  date.setHours(hour, 0, 0, 0);
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
  });
}

export function formatScore(score: number): string {
  if (score >= 0.01) return score.toFixed(3);
  return score.toExponential(2);
}

export function spotifyTrackUrl(trackId: string): string {
  return `https://open.spotify.com/track/${trackId}`;
}

export function localTimeZoneName(): string {
  try {
    return (
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      `UTC${-new Date().getTimezoneOffset() / 60 >= 0 ? "+" : ""}${-new Date().getTimezoneOffset() / 60}`
    );
  } catch {
    return "local";
  }
}
