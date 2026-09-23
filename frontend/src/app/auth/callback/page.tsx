"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Suspense } from "react";

function AuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const status = searchParams.get("status") ?? "";
    const reason = searchParams.get("reason") ?? undefined;
    const qs = new URLSearchParams();
    if (status === "authorized") qs.set("connected", "1");
    else if (status === "error") qs.set("auth_error", reason ?? "1");
    router.replace(`/?${qs.toString()}`);
  }, [router, searchParams]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 animate-fade-up">
      <Loader2 className="size-8 animate-spin text-primary" />
      <p className="font-heading text-lg">Finishing Spotify connect…</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <Loader2 className="size-8 animate-spin text-primary" />
        </div>
      }
    >
      <AuthCallbackInner />
    </Suspense>
  );
}
