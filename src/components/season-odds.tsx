"use client";

import * as React from "react";
import Link from "next/link";
import { ClubBadge } from "@/components/club-badge";
import { cn } from "@/lib/utils";
import { oddsPct, oddsWidth } from "@/lib/format";
import { oddsLabelsFor } from "@/lib/league";

export interface OddsClub {
  code: string;
  short: string;
  primary: string;
  secondary: string;
  position: number;
  title: number;
  ucl: number;
  europa: number;
  relegation: number;
  expectedPoints: number;
  expectedPosition: number;
}

type Metric = "title" | "ucl" | "europa" | "relegation";

const METRIC_COLORS: Record<Metric, string> = {
  title: "from-primary to-accent",
  ucl: "from-primary to-primary",
  europa: "from-info to-info",
  relegation: "from-destructive to-destructive",
};

/**
 * Interactive Monte-Carlo season odds. A metric toggle re-sorts the field and
 * repaints the probability bars; every club links through to its detail page.
 * Metric labels adapt to the dataset `format` (domestic league vs UCL).
 */
export function SeasonOdds({
  clubs,
  query,
  format,
}: {
  clubs: OddsClub[];
  query: string;
  format?: string;
}) {
  const [metric, setMetric] = React.useState<Metric>("title");

  const metrics = React.useMemo(() => {
    const labels = oddsLabelsFor(format);
    return (["title", "ucl", "europa", "relegation"] as Metric[]).map((id) => ({
      id,
      label: labels[id],
      color: METRIC_COLORS[id],
    }));
  }, [format]);
  const active = metrics.find((m) => m.id === metric)!;

  const rows = React.useMemo(() => {
    return [...clubs].sort((a, b) => {
      const av = a[metric];
      const bv = b[metric];
      if (metric === "relegation") return bv - av || a.expectedPosition - b.expectedPosition;
      return bv - av || a.expectedPosition - b.expectedPosition;
    });
  }, [clubs, metric]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-card p-1">
        {metrics.map((m) => (
          <button
            key={m.id}
            onClick={() => setMetric(m.id)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              metric === m.id
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="space-y-1.5">
        {rows.map((c) => {
          const value = c[metric];
          return (
            <div
              key={c.code}
              className="flex items-center gap-3 rounded-lg border border-transparent px-2 py-1.5 transition-colors hover:border-border hover:bg-card"
            >
              <span className="w-5 text-center text-xs font-semibold text-muted-foreground tabular-nums">
                {c.position}
              </span>
              <Link
                href={`/clubs/${c.code.toLowerCase()}${query}`}
                className="flex w-40 min-w-0 items-center gap-2 hover:text-primary"
              >
                <ClubBadge code={c.code} primary={c.primary} secondary={c.secondary} size="xs" />
                <span className="truncate text-sm font-medium">{c.short}</span>
              </Link>
              <div className="flex-1">
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn("h-full rounded-full bg-gradient-to-r", active.color)}
                    style={{ width: `${oddsWidth(value)}%` }}
                  />
                </div>
              </div>
              <span className="w-14 text-right text-sm font-semibold tabular-nums">
                {oddsPct(value)}
              </span>
              <span className="hidden w-16 text-right text-xs text-muted-foreground tabular-nums sm:inline">
                {c.expectedPoints.toFixed(0)} xPts
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
