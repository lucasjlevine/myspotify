"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState, useTransition } from "react";
import {
  Activity,
  History,
  LayoutDashboard,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { connectSpotifyUrl, getAuthStatus, getHealth, syncPlays } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/predict", label: "Predict", icon: Sparkles },
  { href: "/history", label: "History", icon: History },
] as const;

function AuthBanner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const connected = searchParams.get("connected");
  const authError = searchParams.get("auth_error");

  useEffect(() => {
    if (!connected && !authError) return;
    const t = setTimeout(() => {
      router.replace("/");
    }, 4000);
    return () => clearTimeout(t);
  }, [connected, authError, router]);

  if (connected) {
    return (
      <p className="mb-4 rounded-2xl bg-primary/15 px-4 py-3 text-sm text-primary animate-fade-up">
        Spotify connected. Sync pulls recent plays into your library.
      </p>
    );
  }
  if (authError) {
    return (
      <p className="mb-4 rounded-2xl bg-destructive/15 px-4 py-3 text-sm text-destructive animate-fade-up">
        Connect failed: {authError}
      </p>
    );
  }
  return null;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const refreshStatus = useCallback(() => {
    startTransition(async () => {
      try {
        const [auth, health] = await Promise.all([
          getAuthStatus(),
          getHealth().catch(() => null),
        ]);
        setAuthorized(auth.authorized);
        setApiOk(health?.ok ?? false);
      } catch {
        setAuthorized(false);
        setApiOk(false);
      }
    });
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  function handleSync() {
    setSyncMessage(null);
    startTransition(async () => {
      try {
        const result = await syncPlays();
        setSyncMessage(
          `Synced ${result.fetched} · +${result.inserted} new · ${result.skipped} skipped`,
        );
        refreshStatus();
      } catch (err) {
        setSyncMessage(
          err instanceof Error ? err.message : "Sync failed — connect Spotify first",
        );
      }
    });
  }

  return (
    <div className="flex min-h-full flex-1">
      <aside className="sticky top-0 flex h-svh w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 px-3 py-6 backdrop-blur-md">
        <Link href="/" className="group mb-8 px-2">
          <p className="font-heading text-2xl font-semibold tracking-tight text-primary transition-transform duration-300 group-hover:translate-x-0.5">
            myspotify
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            listening + next-song
          </p>
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "relative flex items-center gap-2.5 rounded-2xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-primary transition-all" />
                )}
                <Icon className="size-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto space-y-2 px-1 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Activity className="size-3.5" />
            API{" "}
            {apiOk === null ? "…" : apiOk ? "online" : "offline"}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border/60 bg-background/70 px-6 py-3 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Badge variant={authorized ? "default" : "secondary"}>
              {authorized === null
                ? "Checking…"
                : authorized
                  ? "Connected"
                  : "Not connected"}
            </Badge>
            {syncMessage && (
              <span className="hidden text-xs text-muted-foreground sm:inline animate-fade-up">
                {syncMessage}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!authorized && authorized !== null && (
              <Button size="sm" render={<a href={connectSpotifyUrl()} />}>
                Connect Spotify
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={pending || !authorized}
            >
              {pending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              Sync
            </Button>
          </div>
        </header>

        <main className="flex-1 px-6 py-8">
          <Suspense fallback={null}>
            <AuthBanner />
          </Suspense>
          {children}
        </main>
      </div>
    </div>
  );
}
