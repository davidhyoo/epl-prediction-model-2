import * as React from "react";
import { cn } from "@/lib/utils";
import { readableColor } from "@/lib/format";

const SIZES = {
  xs: "size-5 text-[9px]",
  sm: "size-7 text-[10px]",
  md: "size-9 text-xs",
  lg: "size-12 text-sm",
  xl: "size-16 text-lg",
};

/**
 * A clean, crest-style club badge. We don't ship copyrighted club crests, so we
 * render a tasteful two-tone monogram from the club's official primary/secondary
 * colours and 2-3 letter code — always legal, always renders, never breaks.
 */
export function ClubBadge({
  code,
  primary,
  secondary,
  size = "md",
  className,
}: {
  code: string;
  primary: string;
  secondary: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const p = readableColor(primary || "#334155");
  const s = secondary || "#0f172a";
  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-md font-bold uppercase tracking-tight text-white shadow-sm ring-1 ring-black/10",
        SIZES[size],
        className,
      )}
      style={{ backgroundImage: `linear-gradient(135deg, ${p} 0%, ${p} 55%, ${s} 55%, ${s} 100%)` }}
      aria-hidden
    >
      <span className="drop-shadow-[0_1px_1px_rgba(0,0,0,0.4)]">{code}</span>
    </span>
  );
}
