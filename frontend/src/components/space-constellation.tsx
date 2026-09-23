"use client";

import { useMemo, useState } from "react";
import { AlbumArt } from "@/components/album-art";
import { formatScore } from "@/lib/format";
import type { SpaceEdge, SpacePoint } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  points: SpacePoint[];
  edges: SpaceEdge[];
  query: string;
  className?: string;
};

function toPx(v: number, size: number, pad: number) {
  return pad + ((v + 1) / 2) * (size - pad * 2);
}

export function SpaceConstellation({ points, edges, query, className }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const size = 720;
  const pad = 56;

  const byId = useMemo(() => {
    const map = new Map<string, SpacePoint>();
    for (const p of points) map.set(p.id, p);
    return map;
  }, [points]);

  const queryPoint = byId.get("__query__");
  const selected =
    (selectedId && byId.get(selectedId)) ||
    points.find((p) => p.kind === "neighbor") ||
    null;
  const focusId = hoveredId ?? selectedId;

  const neighbors = points
    .filter((p) => p.kind === "neighbor")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  return (
    <div className={cn("grid gap-4 lg:grid-cols-[1fr_280px]", className)}>
      <div
        className="relative aspect-square w-full overflow-hidden border border-border bg-[radial-gradient(ellipse_at_center,oklch(0.22_0.03_145)_0%,var(--background)_70%)]"
        style={{ maxHeight: "min(72vh, 720px)" }}
      >
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="absolute inset-0 size-full"
          aria-hidden
        >
          {/* faint grid rings */}
          {[0.25, 0.5, 0.75, 1].map((r) => (
            <circle
              key={r}
              cx={size / 2}
              cy={size / 2}
              r={((size - pad * 2) / 2) * r}
              fill="none"
              stroke="var(--border)"
              strokeWidth={1}
              strokeDasharray="2 6"
              opacity={0.5}
            />
          ))}
          {edges.map((e) => {
            const a = byId.get(e.source);
            const b = byId.get(e.target);
            if (!a || !b) return null;
            const active =
              focusId === e.target || focusId === e.source || !focusId;
            const isNeighbor = e.kind === "neighbor";
            return (
              <line
                key={`${e.source}-${e.target}`}
                x1={toPx(a.x, size, pad)}
                y1={toPx(a.y, size, pad)}
                x2={toPx(b.x, size, pad)}
                y2={toPx(b.y, size, pad)}
                stroke={isNeighbor ? "var(--primary)" : "var(--border)"}
                strokeWidth={isNeighbor ? 1.25 : 0.75}
                opacity={
                  active
                    ? isNeighbor
                      ? 0.25 + Math.max(0, e.weight) * 0.45
                      : 0.12
                    : 0.04
                }
                className="transition-opacity duration-300"
              />
            );
          })}
        </svg>

        {points.map((p, i) => {
          const left = ((p.x + 1) / 2) * 100;
          const top = ((p.y + 1) / 2) * 100;
          const isQuery = p.kind === "query";
          const isNeighbor = p.kind === "neighbor";
          const dimmed = focusId != null && focusId !== p.id && !isQuery;
          return (
            <button
              key={p.id}
              type="button"
              title={
                isQuery
                  ? query
                  : `${p.track_name ?? p.id} — ${p.artist_names ?? ""}`
              }
              onClick={() => setSelectedId(isQuery ? null : p.id)}
              onMouseEnter={() => setHoveredId(p.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={cn(
                "absolute -translate-x-1/2 -translate-y-1/2 transition-all duration-300",
                dimmed && "opacity-25 scale-90",
                isQuery && "z-20",
                isNeighbor && "z-10",
              )}
              style={{
                left: `${left}%`,
                top: `${top}%`,
                animationDelay: `${Math.min(i, 24) * 28}ms`,
              }}
            >
              {isQuery ? (
                <span className="relative flex size-14 items-center justify-center border border-primary bg-primary/15 font-mono text-[10px] uppercase tracking-wider text-primary animate-fade-up">
                  <span className="absolute inset-0 animate-ping border border-primary/40 opacity-20" />
                  prompt
                </span>
              ) : (
                <span
                  className={cn(
                    "block animate-fade-up border transition-transform hover:scale-110",
                    isNeighbor
                      ? "border-primary/50"
                      : "border-border opacity-70 hover:opacity-100",
                    selectedId === p.id && "ring-1 ring-primary",
                  )}
                >
                  <AlbumArt
                    src={p.album_image_url}
                    alt={p.album_name ?? p.track_name ?? ""}
                    size={isNeighbor ? "sm" : "sm"}
                    className={cn(!isNeighbor && "size-7 opacity-80")}
                  />
                </span>
              )}
            </button>
          );
        })}

        {!points.length && (
          <p className="absolute inset-0 flex items-center justify-center font-mono text-xs text-muted-foreground">
            Enter a mood to project the space
          </p>
        )}
      </div>

      <aside className="flex flex-col gap-4 border border-border bg-card/40 p-4">
        <div>
          <p className="meta-label">focus</p>
          {selected && selected.kind !== "query" ? (
            <div className="mt-3 flex gap-3">
              <AlbumArt
                src={selected.album_image_url}
                alt={selected.album_name ?? ""}
                size="md"
              />
              <div className="min-w-0">
                <p className="truncate font-heading text-base font-medium">
                  {selected.track_name ?? selected.id}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {selected.artist_names ?? "Unknown"}
                </p>
                <p className="mt-2 font-mono text-[10px] tabular-nums text-primary">
                  sim {formatScore(selected.score ?? 0)}
                  {selected.annotated ? " · annotated" : ""}
                </p>
              </div>
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">
              Click a neighbor to inspect. Distance ≈ embedding similarity to
              “{query || "…"}”.
            </p>
          )}
        </div>

        <div className="panel-rule pt-3">
          <p className="meta-label">nearest</p>
          <ol className="mt-2 max-h-64 space-y-1 overflow-y-auto">
            {neighbors.map((p, i) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(p.id)}
                  onMouseEnter={() => setHoveredId(p.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={cn(
                    "flex w-full items-center gap-2 px-1 py-1.5 text-left transition-colors hover:bg-muted/40",
                    selectedId === p.id && "bg-muted/50",
                  )}
                >
                  <span className="w-5 font-mono text-[10px] text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs">
                    {p.track_name ?? p.id}
                  </span>
                  <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                    {formatScore(p.score ?? 0)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </aside>
    </div>
  );
}
