"use client";

import { Suspense, useCallback, useEffect, useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";
import { AlbumArt } from "@/components/album-art";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listModels,
  listPlays,
  localTzOffsetMinutes,
  predictNext,
  searchByPrompt,
  type ModelInfo,
  type Play,
  type PredictResponse,
  type Prediction,
  type WindowPreset,
} from "@/lib/api";
import { formatPlayedAt, formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";

const scoreConfig = {
  score: { label: "Score", color: "var(--chart-1)" },
} satisfies ChartConfig;

const DEFAULT_WINDOWS: WindowPreset[] = [
  { id: "latest", label: "Latest track", description: "Single most recent play" },
  {
    id: "hours_4",
    label: "Last 4 hours",
    description: "Everything played in the last 4 hours",
  },
  { id: "today", label: "Today", description: "Plays since local midnight" },
  { id: "plays_10", label: "Last 10 plays", description: "Recent session slice" },
  {
    id: "plays_20",
    label: "Last 20 plays",
    description: "Longer session context",
  },
];

function PredictInner() {
  const searchParams = useSearchParams();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [windows, setWindows] = useState<WindowPreset[]>(DEFAULT_WINDOWS);
  const [defaultModel, setDefaultModel] = useState("markov");
  const [model, setModel] = useState("markov");
  const [windowId, setWindowId] = useState(
    searchParams.get("window") ?? "hours_4",
  );
  const [k, setK] = useState(8);
  const [plays, setPlays] = useState<Play[]>([]);
  const [seedId, setSeedId] = useState<string>(
    searchParams.get("track_id") ?? "",
  );
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [prompt, setPrompt] = useState("Rainy fall day");
  const [promptHits, setPromptHits] = useState<Prediction[] | null>(null);
  const [promptMeta, setPromptMeta] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [pending, startTransition] = useTransition();
  const [promptPending, startPrompt] = useTransition();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [modelsRes, playsRes] = await Promise.all([
          listModels(),
          listPlays(40),
        ]);
        if (cancelled) return;
        setModels(modelsRes.models);
        if (modelsRes.windows?.length) setWindows(modelsRes.windows);
        setDefaultModel(modelsRes.default);
        const preferred =
          modelsRes.models.find((m) => m.id === "embedding" && m.trained)?.id ??
          modelsRes.models.find((m) => m.id === "prompted" && m.trained)?.id ??
          modelsRes.default;
        setModel(preferred);
        setPlays(playsRes.plays);
        if (!seedId && playsRes.plays[0]) {
          setSeedId(playsRes.plays[0].track_id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      } finally {
        if (!cancelled) setLoadingMeta(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runPredict = useCallback(() => {
    setError(null);
    startTransition(async () => {
      try {
        const res = await predictNext({
          k,
          model,
          trackId: windowId === "latest" ? seedId || null : null,
          window: windowId,
          tzOffsetMinutes: localTzOffsetMinutes(),
        });
        setResult(res);
      } catch (err) {
        setResult(null);
        setError(err instanceof Error ? err.message : "Prediction failed");
      }
    });
  }, [k, model, seedId, windowId]);

  function runPromptSearch() {
    setError(null);
    startPrompt(async () => {
      try {
        const res = await searchByPrompt({
          q: prompt,
          k,
          model: "embedding",
        });
        setPromptHits(res.predictions);
        setPromptMeta(
          res.model.dim
            ? `${res.model.backend} · ${res.model.dim}-d · ${res.model.n_tracks?.toLocaleString()} tracks`
            : null,
        );
      } catch (err) {
        setPromptHits(null);
        setError(
          err instanceof Error
            ? err.message
            : "Prompt search failed — train embedding model first",
        );
      }
    });
  }

  useEffect(() => {
    if (loadingMeta) return;
    const trained = models.some((m) => m.id === model && m.trained);
    if (!trained) return;
    runPredict();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingMeta, model, k, seedId, windowId, models]);

  const chartData =
    result?.predictions.map((p) => ({
      name: p.track_name
        ? p.track_name.length > 14
          ? `${p.track_name.slice(0, 12)}…`
          : p.track_name
        : p.track_id.slice(0, 8),
      score: p.score,
    })) ?? [];

  const uniqueSeeds = Array.from(
    new Map(plays.map((p) => [p.track_id, p])).values(),
  ).slice(0, 25);

  const seedCount = result?.seeds?.length ?? 0;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 animate-fade-up">
      <div>
        <p className="meta-label">models</p>
        <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
          Predict
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Seed from a listening window, or describe a mood —{" "}
          <span className="text-primary">embedding</span> maps tracks into a
          local vector space for neighbors and phrase search.
        </p>
      </div>

      {error && (
        <p className="border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-xs text-destructive">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Mood prompt</CardTitle>
          <CardDescription>
            free-text → nearest tracks in embedding space (local ONNX)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runPromptSearch();
              }}
              placeholder='e.g. "Rainy fall day" or "late night drive"'
              className="min-w-[240px] flex-1 border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-primary"
            />
            <Button onClick={runPromptSearch} disabled={promptPending || !prompt.trim()}>
              {promptPending && <Loader2 className="size-4 animate-spin" />}
              Search space
            </Button>
          </div>
          {promptMeta && (
            <p className="font-mono text-[10px] text-muted-foreground">{promptMeta}</p>
          )}
          {promptHits && (
            <ul className="divide-y divide-border border border-border">
              {promptHits.map((p, i) => (
                <li
                  key={`${p.track_id}-${i}`}
                  className="flex items-center gap-3 px-3 py-2.5"
                >
                  <span className="w-6 font-mono text-xs text-primary">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <AlbumArt
                    src={p.album_image_url}
                    alt={p.album_name ?? ""}
                    size="sm"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {p.track_name ?? p.track_id}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {p.artist_names ?? "Unknown"}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                    {formatScore(p.score)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {loadingMeta
          ? Array.from({ length: 7 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))
          : models.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setModel(m.id)}
                className={cn(
                  "border border-border bg-card p-4 text-left transition-colors",
                  model === m.id && "border-primary",
                  !m.trained && "opacity-55",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-heading text-sm font-medium">{m.id}</span>
                  <Badge variant={m.trained ? "default" : "secondary"}>
                    {m.trained ? "ok" : "—"}
                  </Badge>
                </div>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {m.backend
                    ? `${m.backend}${m.dim ? ` · ${m.dim}d` : ""}`
                    : m.n_plays != null
                      ? `${m.n_plays.toLocaleString()} plays`
                      : m.id === defaultModel
                        ? "default"
                        : "—"}
                </p>
              </button>
            ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Listening window</CardTitle>
          <CardDescription>
            Multi-track windows blend classical models; prompted ranks against
            the whole session prompt.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground">Window</label>
            <Select value={windowId} onValueChange={(v) => v && setWindowId(v)}>
              <SelectTrigger className="min-w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {windows.map((w) => (
                  <SelectItem key={w.id} value={w.id}>
                    {w.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {windowId === "latest" && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-foreground">Seed track</label>
              <Select
                value={seedId || undefined}
                onValueChange={(v) => v && setSeedId(v)}
              >
                <SelectTrigger className="min-w-[220px] max-w-sm">
                  <SelectValue placeholder="Latest play" />
                </SelectTrigger>
                <SelectContent>
                  {uniqueSeeds.map((p) => (
                    <SelectItem key={p.track_id} value={p.track_id}>
                      {p.track_name} — {p.artist_names}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground" htmlFor="k-range">
              Top k: {k}
            </label>
            <input
              id="k-range"
              type="range"
              min={1}
              max={15}
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-40 accent-primary"
            />
          </div>

          <Button onClick={runPredict} disabled={pending}>
            {pending && <Loader2 className="size-4 animate-spin" />}
            Run prediction
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Seed context</CardTitle>
            <CardDescription>
              {result
                ? `${seedCount} play${seedCount === 1 ? "" : "s"} · model ${result.model.id}${
                    result.model.backend ? ` (${result.model.backend})` : ""
                  }`
                : "Waiting for a prediction"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pending && !result ? (
              <Skeleton className="h-32 w-full rounded-3xl" />
            ) : result?.seeds?.length ? (
              <ul className="max-h-56 space-y-2 overflow-y-auto animate-fade-up">
                {result.seeds.map((p, i) => (
                  <li key={`${p.played_at}-${p.track_id}`} className="flex items-center gap-3">
                    <span className="w-5 text-xs tabular-nums text-muted-foreground">
                      {i + 1}
                    </span>
                    <AlbumArt
                      src={p.album_image_url}
                      alt={p.album_name}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{p.track_name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {p.artist_names} · {formatPlayedAt(p.played_at)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Train a model and sync plays to get started.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Score distribution</CardTitle>
            <CardDescription>Relative confidence of each pick</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <Skeleton className="aspect-video w-full" />
            ) : (
              <>
                <ChartContainer
                  config={scoreConfig}
                  className="aspect-[16/9] w-full animate-fade-up"
                >
                  <BarChart
                    data={chartData}
                    margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
                  >
                    <CartesianGrid
                      vertical={false}
                      strokeDasharray="2 4"
                      stroke="var(--border)"
                    />
                    <XAxis
                      dataKey="name"
                      tickLine={false}
                      axisLine={false}
                      tickMargin={8}
                      tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      width={40}
                      tickMargin={6}
                      tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar
                      dataKey="score"
                      fill="var(--color-score)"
                      radius={[1, 1, 0, 0]}
                    />
                  </BarChart>
                </ChartContainer>
                <p className="meta-label mt-3">x · track &nbsp;·&nbsp; y · score</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ranked predictions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {result?.predictions.map((p, i) => (
            <div
              key={p.track_id}
              className="flex items-center gap-4 rounded-2xl bg-muted/40 px-4 py-3 animate-fade-up"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <span className="w-6 font-heading text-lg text-primary tabular-nums">
                {i + 1}
              </span>
              <AlbumArt
                src={p.album_image_url}
                alt={p.album_name ?? p.track_name ?? ""}
                size="sm"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {p.track_name ?? p.track_id}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {p.artist_names ?? "Unknown artist"}
                </p>
              </div>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {formatScore(p.score)}
              </span>
            </div>
          ))}
          {!result && !pending && (
            <p className="text-sm text-muted-foreground">No predictions yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function PredictPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <Loader2 className="size-8 animate-spin text-primary" />
        </div>
      }
    >
      <PredictInner />
    </Suspense>
  );
}
