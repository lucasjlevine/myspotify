"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import { AlbumArt } from "@/components/album-art";
import { Button } from "@/components/ui/button";
import { formatScore } from "@/lib/format";
import type { SpaceEdge, SpacePoint } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  points: SpacePoint[];
  edges: SpaceEdge[];
  query: string;
  className?: string;
};

const MIN_SCALE = 0.35;
const MAX_SCALE = 4;
const SIZE = 720;
const PAD = 56;

function toPx(v: number) {
  return PAD + ((v + 1) / 2) * (SIZE - PAD * 2);
}

function clampScale(s: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));
}

export function SpaceConstellation({ points, edges, query, className }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const viewportRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const dragOrigin = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const skipClick = useRef(false);

  const byId = useMemo(() => {
    const map = new Map<string, SpacePoint>();
    for (const p of points) map.set(p.id, p);
    return map;
  }, [points]);

  const selected =
    (selectedId && byId.get(selectedId)) ||
    points.find((p) => p.kind === "neighbor") ||
    null;
  const focusId = hoveredId ?? selectedId;

  const neighbors = points
    .filter((p) => p.kind === "neighbor")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  // Reset view when the projected set changes
  useEffect(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
    setSelectedId(null);
  }, [query, points]);

  // Non-passive wheel so we can prevent page scroll while zooming
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheelNative = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      const next = clampScale(scale * factor);
      const rect = el.getBoundingClientRect();
      const cx = e.clientX - rect.left - rect.width / 2;
      const cy = e.clientY - rect.top - rect.height / 2;
      const ratio = next / scale;
      setPan((p) => ({
        x: cx - (cx - p.x) * ratio,
        y: cy - (cy - p.y) * ratio,
      }));
      setScale(next);
    };
    el.addEventListener("wheel", onWheelNative, { passive: false });
    return () => el.removeEventListener("wheel", onWheelNative);
  }, [scale]);

  const zoomAt = useCallback(
    (nextScale: number, clientX: number, clientY: number) => {
      const el = viewportRef.current;
      if (!el) {
        setScale(clampScale(nextScale));
        return;
      }
      const rect = el.getBoundingClientRect();
      const cx = clientX - rect.left - rect.width / 2;
      const cy = clientY - rect.top - rect.height / 2;
      const clamped = clampScale(nextScale);
      const ratio = clamped / scale;
      setPan((p) => ({
        x: cx - (cx - p.x) * ratio,
        y: cy - (cy - p.y) * ratio,
      }));
      setScale(clamped);
    },
    [scale],
  );

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    // Don't pan when interacting with a node
    if ((e.target as HTMLElement).closest("[data-space-node]")) return;
    dragging.current = true;
    skipClick.current = false;
    dragOrigin.current = {
      x: e.clientX,
      y: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    const dx = e.clientX - dragOrigin.current.x;
    const dy = e.clientY - dragOrigin.current.y;
    if (Math.hypot(dx, dy) > 3) skipClick.current = true;
    setPan({
      x: dragOrigin.current.panX + dx,
      y: dragOrigin.current.panY + dy,
    });
  }

  function onPointerUp(e: ReactPointerEvent<HTMLDivElement>) {
    dragging.current = false;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* already released */
    }
  }

  function resetView() {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }

  return (
    <div className={cn("grid gap-4 lg:grid-cols-[1fr_280px]", className)}>
      <div className="relative">
        <div
          ref={viewportRef}
          className={cn(
            "relative aspect-square w-full overflow-hidden border border-border bg-[radial-gradient(ellipse_at_center,oklch(0.22_0.03_145)_0%,var(--background)_70%)]",
            dragging.current ? "cursor-grabbing" : "cursor-grab",
          )}
          style={{ maxHeight: "min(72vh, 720px)" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        >
          <div
            className="absolute inset-0 origin-center will-change-transform"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            }}
          >
            <svg
              viewBox={`0 0 ${SIZE} ${SIZE}`}
              className="absolute inset-0 size-full"
              aria-hidden
            >
              {[0.25, 0.5, 0.75, 1].map((r) => (
                <circle
                  key={r}
                  cx={SIZE / 2}
                  cy={SIZE / 2}
                  r={((SIZE - PAD * 2) / 2) * r}
                  fill="none"
                  stroke="var(--border)"
                  strokeWidth={1 / scale}
                  strokeDasharray={`${2 / scale} ${6 / scale}`}
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
                    x1={toPx(a.x)}
                    y1={toPx(a.y)}
                    x2={toPx(b.x)}
                    y2={toPx(b.y)}
                    stroke={isNeighbor ? "var(--primary)" : "var(--border)"}
                    strokeWidth={(isNeighbor ? 1.25 : 0.75) / scale}
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
                  data-space-node
                  title={
                    isQuery
                      ? query
                      : `${p.track_name ?? p.id} — ${p.artist_names ?? ""}`
                  }
                  onClick={() => {
                    if (skipClick.current) return;
                    setSelectedId(isQuery ? null : p.id);
                  }}
                  onMouseEnter={() => setHoveredId(p.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={cn(
                    "absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-opacity duration-300",
                    dimmed && "opacity-25",
                    isQuery && "z-20",
                    isNeighbor && "z-10",
                  )}
                  style={{
                    left: `${left}%`,
                    top: `${top}%`,
                    // Counter-scale so album art stays readable while zoomed
                    transform: `translate(-50%, -50%) scale(${1 / Math.sqrt(scale)})`,
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
                        size="sm"
                        className={cn(!isNeighbor && "size-7 opacity-80")}
                      />
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {!points.length && (
            <p className="absolute inset-0 flex items-center justify-center font-mono text-xs text-muted-foreground">
              Enter a mood to project the space
            </p>
          )}
        </div>

        <div className="absolute bottom-3 left-3 flex items-center gap-1 border border-border bg-background/90 p-1">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="size-8 p-0"
            onClick={() => {
              const el = viewportRef.current;
              if (!el) return;
              const r = el.getBoundingClientRect();
              zoomAt(scale * 1.2, r.left + r.width / 2, r.top + r.height / 2);
            }}
            aria-label="Zoom in"
          >
            <Plus className="size-3.5" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="size-8 p-0"
            onClick={() => {
              const el = viewportRef.current;
              if (!el) return;
              const r = el.getBoundingClientRect();
              zoomAt(scale / 1.2, r.left + r.width / 2, r.top + r.height / 2);
            }}
            aria-label="Zoom out"
          >
            <Minus className="size-3.5" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="size-8 p-0"
            onClick={resetView}
            aria-label="Reset view"
          >
            <RotateCcw className="size-3.5" />
          </Button>
          <span className="px-2 font-mono text-[10px] tabular-nums text-muted-foreground">
            {Math.round(scale * 100)}%
          </span>
        </div>
        <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
          scroll to zoom · drag to pan
        </p>
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
