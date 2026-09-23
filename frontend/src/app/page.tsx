"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  getListeningByDay,
  getListeningByHour,
  getStatsSummary,
  getTopArtists,
  getTopTracks,
  type DayBucket,
  type HourBucket,
  type StatsSummary,
  type TopArtist,
  type TopTrack,
} from "@/lib/api";
import { formatDayLabel, formatDuration, formatPlayedAt } from "@/lib/format";

const hourConfig = {
  play_count: { label: "Plays", color: "var(--chart-1)" },
} satisfies ChartConfig;

const dayConfig = {
  play_count: { label: "Plays", color: "var(--chart-2)" },
} satisfies ChartConfig;

const topConfig = {
  play_count: { label: "Plays", color: "var(--chart-1)" },
} satisfies ChartConfig;

export default function OverviewPage() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [hours, setHours] = useState<HourBucket[]>([]);
  const [days, setDays] = useState<DayBucket[]>([]);
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [artists, setArtists] = useState<TopArtist[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, h, d, t, a] = await Promise.all([
          getStatsSummary(),
          getListeningByHour(),
          getListeningByDay(30),
          getTopTracks(8),
          getTopArtists(8),
        ]);
        if (cancelled) return;
        setSummary(s);
        setHours(h.hours);
        setDays(d.days);
        setTracks(t.tracks);
        setArtists(a.artists);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load stats");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const hourData = hours.map((h) => ({
    ...h,
    label: `${String(h.hour).padStart(2, "0")}`,
  }));

  const dayData = days.map((d) => ({
    ...d,
    label: formatDayLabel(d.day),
  }));

  const trackChart = tracks.map((t) => ({
    name:
      t.track_name.length > 18
        ? `${t.track_name.slice(0, 16)}…`
        : t.track_name,
    play_count: t.play_count,
  }));

  const artistChart = artists.map((a) => ({
    name:
      a.artist_names.length > 18
        ? `${a.artist_names.slice(0, 16)}…`
        : a.artist_names,
    play_count: a.play_count,
  }));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 animate-fade-up">
      <div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Overview
        </h1>
        <p className="mt-1 text-muted-foreground">
          Your listening shape — totals, rhythms, and favorites.
        </p>
      </div>

      {error && (
        <p className="rounded-2xl bg-destructive/15 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading || !summary
          ? Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-4xl" />
            ))
          : (
              [
                {
                  label: "Plays",
                  value: summary.total_plays.toLocaleString(),
                },
                {
                  label: "Tracks",
                  value: summary.unique_tracks.toLocaleString(),
                },
                {
                  label: "Artists",
                  value: summary.unique_artists.toLocaleString(),
                },
                {
                  label: "Listened",
                  value: formatDuration(summary.total_ms),
                },
              ] as const
            ).map((kpi) => (
              <Card key={kpi.label} size="sm" className="animate-fade-up">
                <CardHeader className="pb-0">
                  <CardDescription>{kpi.label}</CardDescription>
                  <CardTitle className="font-heading text-2xl tabular-nums">
                    {kpi.value}
                  </CardTitle>
                </CardHeader>
                {summary.last_played_at && kpi.label === "Plays" && (
                  <CardContent className="text-xs text-muted-foreground">
                    Last play {formatPlayedAt(summary.last_played_at)}
                  </CardContent>
                )}
              </Card>
            ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="animate-fade-up" style={{ animationDelay: "60ms" }}>
          <CardHeader>
            <CardTitle>By hour of day</CardTitle>
            <CardDescription>When you press play (UTC)</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer config={hourConfig} className="aspect-[16/9] w-full">
                <BarChart data={hourData} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} width={32} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="play_count"
                    fill="var(--color-play_count)"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card className="animate-fade-up" style={{ animationDelay: "120ms" }}>
          <CardHeader>
            <CardTitle>Last 30 days</CardTitle>
            <CardDescription>Daily play volume</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer config={dayConfig} className="aspect-[16/9] w-full">
                <LineChart data={dayData} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis tickLine={false} axisLine={false} width={32} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line
                    type="monotone"
                    dataKey="play_count"
                    stroke="var(--color-play_count)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card className="animate-fade-up" style={{ animationDelay: "180ms" }}>
          <CardHeader>
            <CardTitle>Top tracks</CardTitle>
            <CardDescription>Most played in your library</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer config={topConfig} className="aspect-[16/9] w-full">
                <BarChart
                  data={trackChart}
                  layout="vertical"
                  margin={{ left: 8, right: 8 }}
                >
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                  <XAxis type="number" tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tickLine={false}
                    axisLine={false}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="play_count"
                    fill="var(--color-play_count)"
                    radius={[0, 6, 6, 0]}
                  />
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card className="animate-fade-up" style={{ animationDelay: "240ms" }}>
          <CardHeader>
            <CardTitle>Top artists</CardTitle>
            <CardDescription>Who you return to most</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer config={topConfig} className="aspect-[16/9] w-full">
                <BarChart
                  data={artistChart}
                  layout="vertical"
                  margin={{ left: 8, right: 8 }}
                >
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                  <XAxis type="number" tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tickLine={false}
                    axisLine={false}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="play_count"
                    fill="var(--color-play_count)"
                    radius={[0, 6, 6, 0]}
                  />
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
