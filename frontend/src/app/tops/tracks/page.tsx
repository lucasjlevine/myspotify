"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { ExternalLink, ImagePlus, Loader2, Sparkles } from "lucide-react";
import { AlbumArt } from "@/components/album-art";
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
import {
  enrichAlbumImages,
  getTopTracks,
  type TopTrack,
} from "@/lib/api";
import {
  formatDuration,
  formatPlayedAt,
  spotifyTrackUrl,
} from "@/lib/format";

export default function TopTracksPage() {
  const [limit, setLimit] = useState("50");
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, startTransition] = useTransition();
  const [enrichMsg, setEnrichMsg] = useState<string | null>(null);

  function load(nextLimit = limit) {
    startTransition(async () => {
      try {
        const res = await getTopTracks(Number(nextLimit));
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
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleEnrich() {
    setEnrichMsg(null);
    startTransition(async () => {
      try {
        const res = await enrichAlbumImages(100);
        setEnrichMsg(
          `Fetched ${res.fetched} images · updated ${res.updated} rows`,
        );
        load();
      } catch (err) {
        setEnrichMsg(err instanceof Error ? err.message : "Enrich failed");
      }
    });
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Top tracks
          </h1>
          <p className="mt-1 text-muted-foreground">
            Ranked by play count across your full history.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={limit}
            onValueChange={(v) => {
              if (!v) return;
              setLimit(v);
              setLoading(true);
              load(v);
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
          <Button variant="outline" size="sm" onClick={handleEnrich} disabled={pending}>
            {pending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <ImagePlus className="size-4" />
            )}
            Fetch art
          </Button>
        </div>
      </div>

      {enrichMsg && (
        <p className="text-sm text-muted-foreground animate-fade-up">{enrichMsg}</p>
      )}
      {error && (
        <p className="rounded-2xl bg-destructive/15 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Leaderboard</CardTitle>
          <CardDescription>
            Open in Spotify or seed a prediction from a track.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          {loading
            ? Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-2xl" />
              ))
            : tracks.map((t, i) => (
                <div
                  key={t.track_id}
                  className="flex items-center gap-3 rounded-2xl px-2 py-2 transition-colors hover:bg-muted/40 animate-fade-up"
                  style={{ animationDelay: `${Math.min(i, 30) * 15}ms` }}
                >
                  <span className="w-7 text-center font-heading tabular-nums text-primary">
                    {i + 1}
                  </span>
                  <AlbumArt src={t.album_image_url} alt={t.album_name} size="md" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{t.track_name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {t.artist_names}
                      {t.album_name ? ` · ${t.album_name}` : ""}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t.play_count} plays
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
