"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { ExternalLink, Sparkles } from "lucide-react";
import { AlbumArt } from "@/components/album-art";
import { EnrichArtButton } from "@/components/enrich-art-button";
import {
  TimeRangeToggle,
  type TimeRange,
} from "@/components/time-range-toggle";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getTopTracks, type TopTrack } from "@/lib/api";
import {
  formatDuration,
  formatPlayedAt,
  spotifyTrackUrl,
} from "@/lib/format";

export default function TopTracksPage() {
  const [limit, setLimit] = useState("50");
  const [timeRange, setTimeRange] = useState<TimeRange>("medium_term");
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [, startTransition] = useTransition();

  function load(nextLimit = limit, nextRange = timeRange) {
    startTransition(async () => {
      try {
        const res = await getTopTracks(Number(nextLimit), nextRange);
        setTracks(res.tracks);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    });
  }

  useEffect(() => {
    setLoading(true);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange]);

  const missingIds = tracks
    .filter((t) => !t.album_image_url)
    .map((t) => t.track_id);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="meta-label">library</p>
          <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
            Top tracks
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Affinity score caps repeats at 3 plays/day so overnight loops do not
            dominate. Switch the window like Spotify&apos;s short / medium / long
            term.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <TimeRangeToggle
            value={timeRange}
            onChange={(v) => {
              setTimeRange(v);
            }}
          />
          <Select
            value={limit}
            onValueChange={(v) => {
              if (!v) return;
              setLimit(v);
              setLoading(true);
              load(v, timeRange);
            }}
          >
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["25", "50", "100"].map((n) => (
                <SelectItem key={n} value={n}>
                  Top {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <EnrichArtButton
            trackIds={missingIds}
            batches={30}
            onDone={() => load()}
          />
        </div>
      </div>

      {error && (
        <p className="border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-xs text-destructive">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Leaderboard</CardTitle>
          <CardDescription>
            affinity (capped) · raw plays shown when different
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-0 divide-y divide-border">
          {loading
            ? Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="my-2 h-16 w-full" />
              ))
            : tracks.map((t, i) => (
                <div
                  key={t.track_id}
                  className="flex items-center gap-3 py-3 animate-fade-up"
                  style={{ animationDelay: `${Math.min(i, 30) * 12}ms` }}
                >
                  <span className="w-7 text-center font-mono text-xs tabular-nums text-primary">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <AlbumArt src={t.album_image_url} alt={t.album_name} size="md" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{t.track_name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {t.artist_names}
                      {t.album_name ? ` · ${t.album_name}` : ""}
                    </p>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      score {t.play_count}
                      {t.raw_play_count != null &&
                      t.raw_play_count !== t.play_count
                        ? ` · raw ${t.raw_play_count}`
                        : ""}
                      {t.total_ms != null ? ` · ${formatDuration(t.total_ms)}` : ""}
                      {t.last_played_at
                        ? ` · last ${formatPlayedAt(t.last_played_at)}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      nativeButton={false}
                      render={
                        <Link
                          href={`/predict?track_id=${t.track_id}&window=latest`}
                        />
                      }
                      title="Predict from this track"
                    >
                      <Sparkles className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      nativeButton={false}
                      render={
                        <a
                          href={spotifyTrackUrl(t.track_id)}
                          target="_blank"
                          rel="noreferrer"
                        />
                      }
                      title="Open in Spotify"
                    >
                      <ExternalLink className="size-4" />
                    </Button>
                  </div>
                </div>
              ))}
        </CardContent>
      </Card>
    </div>
  );
}
