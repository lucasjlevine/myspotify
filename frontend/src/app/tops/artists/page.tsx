"use client";

import { useEffect, useState, useTransition } from "react";
import { AlbumArt } from "@/components/album-art";
import { EnrichArtButton } from "@/components/enrich-art-button";
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
import { getTopArtists, type TopArtist } from "@/lib/api";
import { formatDuration, formatPlayedAt } from "@/lib/format";

export default function TopArtistsPage() {
  const [limit, setLimit] = useState("50");
  const [artists, setArtists] = useState<TopArtist[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [, startTransition] = useTransition();

  function load(nextLimit = limit) {
    startTransition(async () => {
      try {
        const res = await getTopArtists(Number(nextLimit));
        setArtists(res.artists);
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

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="meta-label">library</p>
          <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
            Top artists
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Ranked by total plays — cover art from a track in that set.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
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
          <EnrichArtButton batches={30} onDone={() => load()} />
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
          <CardDescription>plays · unique tracks · listen time</CardDescription>
        </CardHeader>
        <CardContent className="space-y-0 divide-y divide-border">
          {loading
            ? Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="my-2 h-16 w-full" />
              ))
            : artists.map((a, i) => (
                <div
                  key={a.artist_names}
                  className="flex items-center gap-3 py-3 animate-fade-up"
                  style={{ animationDelay: `${Math.min(i, 30) * 12}ms` }}
                >
                  <span className="w-7 text-center font-mono text-xs tabular-nums text-primary">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <AlbumArt
                    src={a.album_image_url}
                    alt={a.artist_names}
                    size="md"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{a.artist_names}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      {a.play_count} plays · {a.unique_tracks} tracks
                      {a.total_ms != null
                        ? ` · ${formatDuration(a.total_ms)}`
                        : ""}
                      {a.last_played_at
                        ? ` · last ${formatPlayedAt(a.last_played_at)}`
                        : ""}
                    </p>
                  </div>
                </div>
              ))}
        </CardContent>
      </Card>
    </div>
  );
}
