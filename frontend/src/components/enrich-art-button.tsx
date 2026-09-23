"use client";

import { useCallback, useState, useTransition } from "react";
import { ImagePlus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  enrichAlbumImages,
  getImageCoverage,
  type ImageCoverage,
} from "@/lib/api";

type Props = {
  /** Prefer enriching these track ids first (visible list). */
  trackIds?: string[];
  /** Spotify API rounds per click (50 ids each). */
  batches?: number;
  onDone?: () => void;
  className?: string;
};

export function EnrichArtButton({
  trackIds,
  batches = 25,
  onDone,
  className,
}: Props) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<ImageCoverage | null>(null);

  const refreshCoverage = useCallback(async () => {
    try {
      setCoverage(await getImageCoverage());
    } catch {
      // ignore
    }
  }, []);

  function handleClick() {
    setMessage(null);
    startTransition(async () => {
      try {
        await refreshCoverage();
        const res = await enrichAlbumImages({
          batches,
          trackIds: trackIds?.length ? trackIds : undefined,
        });
        setCoverage({
          unique_tracks: res.unique_tracks,
          with_image: res.with_image,
          missing: res.missing,
        });
        setMessage(
          `+${res.fetched} art · ${res.with_image}/${res.unique_tracks} tracks covered` +
            (res.missing ? ` · ${res.missing} left` : " · done"),
        );
        onDone?.();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Enrich failed");
      }
    });
  }

  return (
    <div className={className}>
      <Button variant="outline" size="sm" onClick={handleClick} disabled={pending}>
        {pending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <ImagePlus className="size-4" />
        )}
        {pending ? "Fetching art…" : "Fetch art"}
      </Button>
      {(message || coverage) && (
        <p className="mt-1 font-mono text-[11px] text-muted-foreground">
          {message ??
            (coverage
              ? `${coverage.with_image}/${coverage.unique_tracks} with art`
              : null)}
        </p>
      )}
    </div>
  );
}
