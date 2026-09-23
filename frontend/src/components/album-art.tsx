import { Disc3 } from "lucide-react";
import { cn } from "@/lib/utils";

type AlbumArtProps = {
  src?: string | null;
  alt: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = {
  sm: "size-10",
  md: "size-14",
  lg: "size-20",
} as const;

export function AlbumArt({ src, alt, size = "md", className }: AlbumArtProps) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt}
        className={cn(
          "shrink-0 rounded-lg object-cover bg-muted",
          sizes[size],
          className,
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground",
        sizes[size],
        className,
      )}
      aria-hidden
    >
      <Disc3 className="size-1/2 opacity-50" />
    </div>
  );
}
