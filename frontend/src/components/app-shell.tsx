"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState, useTransition } from "react";
import {
  History,
  LayoutDashboard,
  Loader2,
  Mic2,
  Music2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { connectSpotifyUrl, getAuthStatus, getHealth, syncPlays } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/predict", label: "Predict", icon: Sparkles },
  { href: "/tops/tracks", label: "Top tracks", icon: Music2 },
  { href: "/tops/artists", label: "Top artists", icon: Mic2 },
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
      <p className="mb-4 border border-primary/40 bg-primary/10 px-4 py-3 font-mono text-xs text-primary animate-fade-up">
        Spotify connected. Sync pulls recent plays into your library.
      </p>
    );
  }
  if (authError) {
    return (
      <p className="mb-4 border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-xs text-destructive animate-fade-up">
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
          `synced ${result.fetched} · +${result.inserted} · ${result.skipped} skip`,
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
      <aside className="sticky top-0 flex h-svh w-52 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-3 py-6">
        <Link href="/" className="mb-10 px-2">
          <p className="font-heading text-[1.65rem] leading-none tracking-tight text-foreground">
            my<span className="text-primary">spotify</span>
          </p>
          <p className="meta-label mt-2">listening · predict</p>
        </Link>

        <nav className="flex flex-1 flex-col gap-0.5">
          {nav.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 border-l-2 px-3 py-2 text-sm transition-colors",
                  active
                    ? "border-primary bg-sidebar-accent text-foreground"
                    : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
                )}
              >
                <Icon className="size-3.5 shrink-0 opacity-70" />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-border px-2 pt-3 font-mono text-[10px] tracking-wide text-muted-foreground uppercase">
          api {apiOk === null ? "…" : apiOk ? "online" : "offline"}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border bg-background/95 px-6 py-2.5">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "font-mono text-[10px] tracking-widest uppercase",
                authorized ? "text-primary" : "text-muted-foreground",
              )}
            >
              {authorized === null
                ? "status · …"
                : authorized
                  ? "status · connected"
                  : "status · offline"}
            </span>
            {syncMessage && (
              <span className="hidden font-mono text-[10px] text-muted-foreground sm:inline animate-fade-up">
                {syncMessage}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!authorized && authorized !== null && (
              <Button
                size="sm"
                nativeButton={false}
                render={<a href={connectSpotifyUrl()} />}
              >
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

        <main className="flex-1 px-6 py-8 md:px-10">
          <Suspense fallback={null}>
            <AuthBanner />
          </Suspense>
          {children}
        </main>
      </div>
    </div>
  );
}
