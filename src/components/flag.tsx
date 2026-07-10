import * as React from "react";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-4 w-6 text-[10px]",
  md: "h-5 w-7 text-xs",
  lg: "h-7 w-10 text-sm",
  xl: "h-10 w-14 text-base",
};

interface FlagProps {
  /** ISO 3166-1 alpha-2 (lowercase), e.g. "us"; England uses "gb-eng". */
  iso2: string;
  size?: keyof typeof SIZES;
  className?: string;
  title?: string;
  rounded?: boolean;
}

/**
 * Country flag rendered via the open-source `flag-icons` library
 * (public-domain SVG sprites). Falls back gracefully to a neutral
 * block if the code is unknown so the UI never breaks.
 */
export function Flag({ iso2, size = "md", className, title, rounded = true }: FlagProps) {
  const code = (iso2 || "").toLowerCase();
  return (
    <span
      title={title}
      className={cn(
        "relative inline-block shrink-0 overflow-hidden bg-muted shadow-[inset_0_0_0_1px_rgba(0,0,0,0.08)]",
        rounded ? "rounded-[3px]" : "",
        SIZES[size],
        className,
      )}
    >
      {code ? (
        <span
          className={cn("fi absolute inset-0 !h-full !w-full bg-cover bg-center", `fi-${code}`)}
        />
      ) : null}
    </span>
  );
}
