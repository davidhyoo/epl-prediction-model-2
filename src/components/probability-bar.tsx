import * as React from "react";
import { cn } from "@/lib/utils";
import { pct, readableColor } from "@/lib/format";

interface ProbabilityBarProps {
  homeProb: number;
  drawProb?: number;
  awayProb: number;
  homeColor: string;
  awayColor: string;
  homeLabel?: string;
  awayLabel?: string;
  /** Show the small labels row above the bar. */
  showLabels?: boolean;
  /** Hide the draw segment (knockout two-way view). */
  twoWay?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const HEIGHT = { sm: "h-2", md: "h-2.5", lg: "h-3.5" };

/**
 * Horizontal win-probability bar. Home segment uses the home team's primary
 * colour, away segment the away team's, with a neutral draw slice between.
 * Colours are contrast-adjusted so pale flags stay legible.
 */
export function ProbabilityBar({
  homeProb,
  drawProb = 0,
  awayProb,
  homeColor,
  awayColor,
  homeLabel,
  awayLabel,
  showLabels = true,
  twoWay = false,
  size = "md",
  className,
}: ProbabilityBarProps) {
  const total = homeProb + drawProb + awayProb || 1;
  const h = (homeProb / total) * 100;
  const d = (drawProb / total) * 100;
  const a = (awayProb / total) * 100;
  const homeC = readableColor(homeColor);
  const awayC = readableColor(awayColor);

  return (
    <div className={cn("w-full", className)}>
      {showLabels && (
        <div className="mb-1 flex items-center justify-between text-xs font-medium tabular-nums">
          <span className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-full" style={{ background: homeC }} />
            <span className="text-muted-foreground">{homeLabel}</span>
            <span className="font-semibold">{pct(homeProb)}</span>
          </span>
          {!twoWay && (
            <span className="text-muted-foreground">Draw {pct(drawProb)}</span>
          )}
          <span className="flex items-center gap-1.5">
            <span className="font-semibold">{pct(awayProb)}</span>
            <span className="text-muted-foreground">{awayLabel}</span>
            <span className="inline-block size-2 rounded-full" style={{ background: awayC }} />
          </span>
        </div>
      )}
      <div
        className={cn(
          "flex w-full overflow-hidden rounded-full bg-muted",
          HEIGHT[size],
        )}
      >
        <div
          className="h-full transition-all"
          style={{ width: `${h}%`, background: homeC }}
        />
        {!twoWay && (
          <div
            className="h-full bg-muted-foreground/35 transition-all"
            style={{ width: `${d}%` }}
          />
        )}
        <div
          className="h-full transition-all"
          style={{ width: `${a}%`, background: awayC }}
        />
      </div>
    </div>
  );
}
