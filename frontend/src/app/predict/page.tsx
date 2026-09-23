"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";
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
  predictNext,
  type ModelInfo,
  type Play,
  type PredictResponse,
} from "@/lib/api";
import { formatPlayedAt, formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";

const scoreConfig = {
  score: { label: "Score", color: "var(--chart-1)" },
} satisfies ChartConfig;

export default function PredictPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultModel, setDefaultModel] = useState("markov");
  const [model, setModel] = useState("markov");
  const [k, setK] = useState(5);
  const [plays, setPlays] = useState<Play[]>([]);
  const [seedId, setSeedId] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [pending, startTransition] = useTransition();

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
        setDefaultModel(modelsRes.default);
        setModel(modelsRes.default);
        setPlays(playsRes.plays);
        if (playsRes.plays[0]) setSeedId(playsRes.plays[0].track_id);
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
  }, []);

  const runPredict = useCallback(() => {
    setError(null);
    startTransition(async () => {
      try {
        const res = await predictNext({
          k,
          model,
          trackId: seedId,
        });
        setResult(res);
      } catch (err) {
        setResult(null);
        setError(err instanceof Error ? err.message : "Prediction failed");
      }
    });
  }, [k, model, seedId]);

  useEffect(() => {
    if (loadingMeta) return;
    const trained = models.some((m) => m.id === model && m.trained);
    if (!trained) return;
    runPredict();
    // Intentionally only re-run when controls change — not when runPredict identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingMeta, model, k, seedId, models]);

  const chartData =
    result?.predictions.map((p) => ({
      name: p.track_name
        ? p.track_name.length > 16
          ? `${p.track_name.slice(0, 14)}…`
          : p.track_name
        : p.track_id.slice(0, 8),
      score: p.score,
    })) ?? [];

  const uniqueSeeds = Array.from(
    new Map(plays.map((p) => [p.track_id, p])).values(),
  ).slice(0, 25);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 animate-fade-up">
      <div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Predict
        </h1>
        <p className="mt-1 text-muted-foreground">
          Compare next-song models against a seed from your history.
        </p>
      </div>

      {error && (
        <p className="rounded-2xl bg-destructive/15 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loadingMeta
          ? Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-4xl" />
            ))
          : models.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setModel(m.id)}
                className={cn(
                  "rounded-4xl bg-card p-4 text-left ring-1 ring-foreground/10 transition-all",
                  model === m.id && "ring-2 ring-primary",
                  !m.trained && "opacity-60",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-heading font-medium">{m.id}</span>
                  <Badge variant={m.trained ? "default" : "secondary"}>
                    {m.trained ? "trained" : "missing"}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {m.n_plays != null
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
          <CardTitle>Controls</CardTitle>
          <CardDescription>
            Seed defaults to your latest play; pick another track to explore.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground">Seed track</label>
            <Select
              value={seedId ?? undefined}
              onValueChange={(v) => setSeedId(v)}
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
            <CardTitle>Context</CardTitle>
            <CardDescription>
              {result
                ? `Model ${result.model.id}`
                : "Waiting for a prediction"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pending && !result ? (
              <Skeleton className="h-24 w-full rounded-3xl" />
            ) : result ? (
              <div className="space-y-1 animate-fade-up">
                <p className="font-heading text-lg font-medium">
                  {result.context.track_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {result.context.artist_names}
                </p>
                <p className="text-xs text-muted-foreground">
                  {result.context.album_name} ·{" "}
                  {formatPlayedAt(result.context.played_at)}
                </p>
              </div>
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
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer
                config={scoreConfig}
                className="aspect-[16/9] w-full animate-fade-up"
              >
                <BarChart data={chartData} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} width={40} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="score"
                    fill="var(--color-score)"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
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
