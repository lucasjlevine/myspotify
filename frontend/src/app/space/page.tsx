"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { Loader2, Orbit, RefreshCw } from "lucide-react";
import { SpaceConstellation } from "@/components/space-constellation";
import { Button } from "@/components/ui/button";
import {
  enrichTrackFeatures,
  getMetaCoverage,
  projectPromptSpace,
  type MetaCoverage,
  type SpaceResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const PRESETS = [
  "Rainy fall day",
  "indie folk calm",
  "late night drive",
  "energetic dance workout",
  "sunday morning acoustic",
  "melancholy winter",
] as const;

export default function SpacePage() {
  const [prompt, setPrompt] = useState("Rainy fall day");
  const [space, setSpace] = useState<SpaceResponse | null>(null);
  const [coverage, setCoverage] = useState<MetaCoverage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [enriching, startEnrich] = useTransition();

  const refreshCoverage = useCallback(() => {
    getMetaCoverage()
      .then(setCoverage)
      .catch(() => setCoverage(null));
  }, []);

  useEffect(() => {
    refreshCoverage();
  }, [refreshCoverage]);

  function run(q = prompt) {
    const text = q.trim();
    if (!text) return;
    startTransition(async () => {
      try {
        const res = await projectPromptSpace({ q: text, k: 28, context: 56 });
        setSpace(res);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Space projection failed — train embedding first",
        );
      }
    });
  }

  useEffect(() => {
    run("Rainy fall day");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function enrichMore() {
    startEnrich(async () => {
      try {
        const res = await enrichTrackFeatures({
          batches: 12,
          limit: 40,
          genresOnly: false,
        });
        setCoverage(res);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Enrich failed");
      }
    });
  }

  const metaPct = coverage
    ? Math.round((coverage.with_meta / Math.max(1, coverage.unique_tracks)) * 100)
    : 0;
  const featPct = coverage
    ? Math.round(
        (coverage.with_features / Math.max(1, coverage.unique_tracks)) * 100,
      )
    : 0;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="meta-label">embedding</p>
          <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
            Song space
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            A PCA slice of your hybrid song-space. Scroll to zoom, drag to pan.
            Neighbors orbit by cosine similarity; annotated tracks (genres +
            audio moods) pull the map into focus.
          </p>
        </div>
        <div className="min-w-[220px] border border-border bg-card/50 p-3">
          <p className="meta-label">catalog meta</p>
          {coverage ? (
            <>
              <p className="mt-1 font-mono text-xs tabular-nums">
                {coverage.with_meta.toLocaleString()} /{" "}
                {coverage.unique_tracks.toLocaleString()}{" "}
                <span className="text-muted-foreground">unique tracks</span>
              </p>
              <div className="mt-2 h-1.5 w-full bg-muted">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${metaPct}%` }}
                />
              </div>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                features {coverage.with_features.toLocaleString()} ({featPct}%)
                · genres {coverage.with_genres.toLocaleString()}
              </p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full"
                onClick={enrichMore}
                disabled={enriching}
              >
                {enriching ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                Enrich +480
              </Button>
            </>
          ) : (
            <p className="mt-2 font-mono text-[10px] text-muted-foreground">
              loading coverage…
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") run();
          }}
          placeholder='e.g. "Rainy fall day"'
          className="min-w-[240px] flex-1 border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-primary"
        />
        <Button onClick={() => run()} disabled={pending || !prompt.trim()}>
          {pending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Orbit className="size-4" />
          )}
          Project
        </Button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => {
              setPrompt(p);
              run(p);
            }}
            className={cn(
              "border border-border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground transition-colors hover:border-primary hover:text-foreground",
              prompt === p && "border-primary text-primary",
            )}
          >
            {p}
          </button>
        ))}
      </div>

      {error && (
        <p className="border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-xs text-destructive">
          {error}
        </p>
      )}

      {space && (
        <>
          <p className="font-mono text-[10px] text-muted-foreground">
            {space.model.backend ?? "embedding"}
            {space.model.dim != null ? ` · ${space.model.dim}d` : ""}
            {space.model.n_tracks != null
              ? ` · ${space.model.n_tracks.toLocaleString()} indexed`
              : ""}
            {" · "}
            {space.points.filter((p) => p.kind === "neighbor").length} neighbors
            {" · "}
            {space.points.filter((p) => p.kind === "context").length} context
          </p>
          <SpaceConstellation
            points={space.points}
            edges={space.edges}
            query={space.query}
          />
        </>
      )}
    </div>
  );
}
