"use client";

import { cn } from "@/lib/utils";

export type TimeRange = "short_term" | "medium_term" | "long_term";

const OPTIONS: { id: TimeRange; label: string; hint: string }[] = [
  { id: "short_term", label: "4 weeks", hint: "short_term" },
  { id: "medium_term", label: "6 months", hint: "medium_term" },
  { id: "long_term", label: "All time", hint: "long_term" },
];

export function TimeRangeToggle({
  value,
  onChange,
}: {
  value: TimeRange;
  onChange: (v: TimeRange) => void;
}) {
  return (
    <div className="inline-flex border border-border">
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          type="button"
          title={opt.hint}
          onClick={() => onChange(opt.id)}
          className={cn(
            "px-3 py-1.5 font-mono text-[10px] tracking-wide uppercase transition-colors",
            value === opt.id
              ? "bg-primary text-primary-foreground"
              : "bg-background text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
