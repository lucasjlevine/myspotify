"use client";

import Link from "next/link";
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
import { ArrowRight } from "lucide-react";
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
import { Button } from "@/components/ui/button";
import { AlbumArt } from "@/components/album-art";
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
import {
  formatDayLabel,
  formatDuration,
  formatHourLabel,
  formatPlayedAt,
  localTimeZoneName,
} from "@/lib/format";

const hourConfig = {
  play_count: { label: "Plays", color: "var(--chart-1)" },
} satisfies ChartConfig;

const dayConfig = {
  play_count: { label: "Plays", color: "var(--chart-2)" },
} satisfies ChartConfig;

export default function OverviewPage() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [hours, setHours] = useState<HourBucket[]>([]);
  const [days, setDays] = useState<DayBucket[]>([]);
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [artists, setArtists] = useState<TopArtist[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const tzName = localTimeZoneName();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, h, d, t, a] = await Promise.all([
          getStatsSummary(),
          getListeningByHour(),
          getListeningByDay(30),
          getTopTracks(5),
          getTopArtists(5),
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
    label: formatHourLabel(h.hour),
  }));

  const dayData = days.map((d) => ({
    ...d,
    label: formatDayLabel(d.day),
  }));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 animate-fade-up">
      <div>
        <p className="meta-label">dashboard</p>
        <h1 className="font-heading mt-1 text-4xl font-medium tracking-tight sm:text-5xl">
          Overview
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Listening shape in your local clock — {tzName}.
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
        <Card className="animate-fade-up">
          <CardHeader>
            <CardTitle>By hour of day</CardTitle>
            <CardDescription>Local time ({tzName})</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full rounded-3xl" />
            ) : (
              <ChartContainer config={hourConfig} className="aspect-[16/9] w-full">
                <BarChart
                  data={hourData}
                  margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
                >
                  <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    interval={3}
                    tickMargin={8}
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={36}
                    tickMargin={6}
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="play_count"
                    fill="var(--color-play_count)"
                    radius={[1, 1, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            )}
            <p className="meta-label mt-3">x · hour &nbsp;·&nbsp; y · plays</p>
          </CardContent>
        </Card>

        <Card className="animate-fade-up" style={{ animationDelay: "80ms" }}>
          <CardHeader>
            <CardTitle>Last 30 days</CardTitle>
            <CardDescription>Daily play volume ({tzName})</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="aspect-video w-full" />
            ) : (
              <ChartContainer config={dayConfig} className="aspect-[16/9] w-full">
                <LineChart
                  data={dayData}
                  margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
                >
                  <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                    tickMargin={8}
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={36}
                    tickMargin={6}
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line
                    type="monotone"
                    dataKey="play_count"
                    stroke="var(--color-play_count)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ChartContainer>
            )}
            <p className="meta-label mt-3">x · date &nbsp;·&nbsp; y · plays</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-2">
            <div>
              <CardTitle>Top tracks</CardTitle>
              <CardDescription>Most played in your library</CardDescription>
            </div>
            <Button variant="ghost" size="sm" render={<Link href="/tops/tracks" />}>
              See all
              <ArrowRight className="size-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-2xl" />
                ))
              : tracks.map((t, i) => (
                  <div
                    key={t.track_id}
                    className="flex items-center gap-3 rounded-2xl px-2 py-1.5"
                  >
                    <span className="w-5 text-sm tabular-nums text-muted-foreground">
                      {i + 1}
                    </span>
                    <AlbumArt
                      src={t.album_image_url}
                      alt={t.album_name}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{t.track_name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {t.artist_names}
                      </p>
                    </div>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {t.play_count}
                    </span>
                  </div>
                ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-start justify-between gap-2">
            <div>
              <CardTitle>Top artists</CardTitle>
              <CardDescription>Who you return to most</CardDescription>
            </div>
            <Button variant="ghost" size="sm" render={<Link href="/tops/artists" />}>
              See all
              <ArrowRight className="size-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-2xl" />
                ))
              : artists.map((a, i) => (
                  <div
                    key={a.artist_names}
                    className="flex items-center gap-3 rounded-2xl px-2 py-1.5"
                  >
                    <span className="w-5 text-sm tabular-nums text-muted-foreground">
                      {i + 1}
                    </span>
                    <AlbumArt
                      src={a.album_image_url}
                      alt={a.artist_names}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{a.artist_names}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {a.unique_tracks} tracks · {a.play_count} plays
                      </p>
                    </div>
                  </div>
                ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
