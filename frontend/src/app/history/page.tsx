"use client";

import { useEffect, useState, useTransition } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { AlbumArt } from "@/components/album-art";
import { EnrichArtButton } from "@/components/enrich-art-button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { listPlays, syncPlays, type Play } from "@/lib/api";
import { formatPlayedAt } from "@/lib/format";

export default function HistoryPage() {
  const [plays, setPlays] = useState<Play[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function load() {
    startTransition(async () => {
      try {
        const res = await listPlays(100);
        setPlays(res.plays);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load plays");
      } finally {
        setLoading(false);
      }
    });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSync() {
    setMessage(null);
    startTransition(async () => {
      try {
        const result = await syncPlays();
        setMessage(
          `Fetched ${result.fetched} · inserted ${result.inserted} · skipped ${result.skipped}` +
            (result.images_updated != null
              ? ` · images ${result.images_updated}`
              : ""),
        );
        const res = await listPlays(100);
        setPlays(res.plays);
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Sync failed");
      }
    });
  }

  const missingIds = plays
    .filter((p) => !p.album_image_url)
    .map((p) => p.track_id);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="meta-label">library</p>
          <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
            History
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Recent plays stored locally — sync to pull from Spotify.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <EnrichArtButton
            trackIds={missingIds}
            batches={20}
            onDone={() => load()}
          />
          <Button variant="outline" size="sm" onClick={handleSync} disabled={pending}>
            {pending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Sync Now
          </Button>
        </div>
      </div>

      {message && (
        <p className="font-mono text-[11px] text-muted-foreground animate-fade-up">
          {message}
        </p>
      )}
      {error && (
        <p className="border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-xs text-destructive">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent plays</CardTitle>
          <CardDescription>{plays.length} shown · newest first</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : plays.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No plays yet. Connect Spotify and sync, or import Extended History
              via the backend CLI.
            </p>
          ) : (
            <ScrollArea className="h-[min(70vh,560px)] pr-3">
              <ul className="divide-y divide-border">
                {plays.map((play, i) => (
                  <li
                    key={`${play.played_at}-${play.track_id}`}
                    className="flex items-center gap-3 py-2.5 animate-fade-up"
                    style={{ animationDelay: `${Math.min(i, 20) * 15}ms` }}
                  >
                    <AlbumArt
                      src={play.album_image_url}
                      alt={play.album_name}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{play.track_name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {play.artist_names}
                        {play.album_name ? ` · ${play.album_name}` : ""}
                      </p>
                    </div>
                    <time className="shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">
                      {formatPlayedAt(play.played_at)}
                    </time>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
