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

const MIN_SCALE = 0.4;
const MAX_SCALE = 5;

function clampScale(s: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));
}

/** Map PCA coords [-1, 1] → viewport pixels. Art stays 1:1 (no CSS scale). */
function project(
  wx: number,
  wy: number,
  opts: {
    width: number;
    height: number;
    scale: number;
    panX: number;
    panY: number;
  },
) {
  const radius = Math.min(opts.width, opts.height) * 0.4 * opts.scale;
  return {
    x: opts.width / 2 + opts.panX + wx * radius,
    y: opts.height / 2 + opts.panY + wy * radius,
  };
}

export function SpaceConstellation({ points, edges, query, className }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [grabbing, setGrabbing] = useState(false);

  const viewportRef = useRef<HTMLDivElement>(null);
  const scaleRef = useRef(scale);
  const panRef = useRef(pan);
  const dragging = useRef(false);
  const dragOrigin = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const skipClick = useRef(false);

  scaleRef.current = scale;
  panRef.current = pan;

  const byId = useMemo(() => {
    const map = new Map<string, SpacePoint>();
    for (const p of points) map.set(p.id, p);
    return map;
  }, [points]);

  const neighbors = useMemo(
    () =>
      points
        .filter((p) => p.kind === "neighbor")
        .sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
    [points],
  );

  const screenOf = useCallback(
    (wx: number, wy: number) =>
      project(wx, wy, {
        width: size.w,
        height: size.h,
        scale,
        panX: pan.x,
        panY: pan.y,
      }),
    [size.w, size.h, scale, pan.x, pan.y],
  );

  useEffect(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
    setSelectedId(null);
  }, [query]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setSize({ w: width, h: height });
    });
    ro.observe(el);
    const rect = el.getBoundingClientRect();
    setSize({ w: rect.width, h: rect.height });
    return () => ro.disconnect();
  }, []);

  const zoomAt = useCallback((nextScale: number, clientX: number, clientY: number) => {
    const el = viewportRef.current;
    const prev = scaleRef.current;
    const clamped = clampScale(nextScale);
    if (!el || prev === 0) {
      setScale(clamped);
      return;
    }
    const rect = el.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const mx = clientX - rect.left;
    const my = clientY - rect.top;
    const { x: panX, y: panY } = panRef.current;
    const ratio = clamped / prev;
    // Keep the world point under the cursor fixed in screen space
    setPan({
      x: mx - w / 2 - (mx - w / 2 - panX) * ratio,
      y: my - h / 2 - (my - h / 2 - panY) * ratio,
    });
    setScale(clamped);
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheelNative = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      zoomAt(scaleRef.current * factor, e.clientX, e.clientY);
    };
    el.addEventListener("wheel", onWheelNative, { passive: false });
    return () => el.removeEventListener("wheel", onWheelNative);
  }, [zoomAt]);

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest("[data-space-node]")) return;
    dragging.current = true;
    skipClick.current = false;
    setGrabbing(true);
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
    setGrabbing(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* already released */
    }
    // Clear after the click event so a finished pan doesn't poison later node clicks
    window.setTimeout(() => {
      skipClick.current = false;
    }, 0);
  }

  function resetView() {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }

  function focusPoint(p: SpacePoint) {
    if (p.kind === "query") {
      setSelectedId(null);
      return;
    }
    setSelectedId(p.id);
    // Center the track in the viewport (pixel projection, no CSS transform)
    const radius = Math.min(size.w, size.h) * 0.4 * scaleRef.current;
    if (radius > 0 && size.w > 0 && size.h > 0) {
      setPan({
        x: -p.x * radius,
        y: -p.y * radius,
      });
    }
  }

  const ready = size.w > 0 && size.h > 0;

  // Only show an explicit selection in the focus panel — don't fake the top neighbor
  const selected =
    selectedId != null ? byId.get(selectedId) ?? null : null;
  const focusId = hoveredId ?? selectedId;

  return (
    <div className={cn("grid gap-4 lg:grid-cols-[1fr_280px]", className)}>
      <div className="relative">
        <div
          ref={viewportRef}
          className={cn(
            "relative aspect-square w-full overflow-hidden border border-border bg-[radial-gradient(ellipse_at_center,oklch(0.22_0.03_145)_0%,var(--background)_70%)]",
            grabbing ? "cursor-grabbing" : "cursor-grab",
          )}
          style={{ maxHeight: "min(72vh, 720px)" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        >
          {ready && (
            <>
              <svg
                width={size.w}
                height={size.h}
                className="pointer-events-none absolute inset-0 block"
                aria-hidden
              >
                {[0.25, 0.5, 0.75, 1].map((r) => {
                  const c = screenOf(0, 0);
                  const rad = Math.min(size.w, size.h) * 0.4 * scale * r;
                  return (
                    <circle
                      key={r}
                      cx={c.x}
                      cy={c.y}
                      r={rad}
                      fill="none"
                      stroke="var(--border)"
                      strokeWidth={1}
                      strokeDasharray="2 6"
                      opacity={0.45}
                    />
                  );
                })}
                {edges.map((e) => {
                  const a = byId.get(e.source);
                  const b = byId.get(e.target);
                  if (!a || !b) return null;
                  const pa = screenOf(a.x, a.y);
                  const pb = screenOf(b.x, b.y);
                  const active =
                    focusId === e.target || focusId === e.source || !focusId;
                  const isNeighbor = e.kind === "neighbor";
                  return (
                    <line
                      key={`${e.source}-${e.target}`}
                      x1={pa.x}
                      y1={pa.y}
                      x2={pb.x}
                      y2={pb.y}
                      stroke={isNeighbor ? "var(--primary)" : "var(--border)"}
                      strokeWidth={isNeighbor ? 1.25 : 0.75}
                      opacity={
                        active
                          ? isNeighbor
                            ? 0.25 + Math.max(0, e.weight) * 0.45
                            : 0.12
                          : 0.04
                      }
                    />
                  );
                })}
              </svg>

              {points.map((p) => {
                const { x, y } = screenOf(p.x, p.y);
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
                    onClick={(e) => {
                      e.stopPropagation();
                      if (skipClick.current) return;
                      focusPoint(p);
                    }}
                    onPointerDown={(e) => {
                      // Don't let the viewport start a pan when pressing a node
                      e.stopPropagation();
                      skipClick.current = false;
                    }}
                    onMouseEnter={() => setHoveredId(p.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    className={cn(
                      "absolute z-10 cursor-pointer transition-opacity duration-200",
                      dimmed && "opacity-25",
                      isQuery && "z-20",
                      (selectedId === p.id || hoveredId === p.id) && "z-30",
                    )}
                    style={{
                      left: x,
                      top: y,
                      transform: "translate(-50%, -50%)",
                    }}
                  >
                    {isQuery ? (
                      <span className="relative flex size-14 items-center justify-center border border-primary bg-primary/15 font-mono text-[10px] uppercase tracking-wider text-primary">
                        <span className="absolute inset-0 animate-ping border border-primary/40 opacity-20" />
                        prompt
                      </span>
                    ) : (
                      <span
                        className={cn(
                          "block border",
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
            </>
          )}

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
              Click a track to center it and inspect. Distance ≈ embedding
              similarity to “{query || "…"}”.
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
                  onClick={() => focusPoint(p)}
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
