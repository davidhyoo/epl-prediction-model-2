"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ClubBadge } from "@/components/club-badge";
import { RANKING_META, RANKING_ORDER } from "@/lib/format";
import type { RankingKey, Rankings } from "@/lib/types";

// recharts is heavy — load the ranking bar chart lazily on the client.
const RankingBars = dynamic(
  () => import("@/components/charts/ranking-bars").then((m) => m.RankingBars),
  { ssr: false, loading: () => <Skeleton className="h-[360px] w-full rounded-xl" /> },
);

export interface RankingClub {
  code: string;
  short: string;
  primary: string;
  secondary: string;
}

function formatValue(value: number, unit: "percent" | "index" | "rating"): string {
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "rating") return value.toFixed(0);
  return value.toFixed(1);
}

export function RankingsExplorer({
  rankings,
  clubs,
  query,
}: {
  rankings: Rankings;
  clubs: RankingClub[];
  query: string;
}) {
  const [key, setKey] = React.useState<RankingKey>("title");
  const meta = RANKING_META[key];
  const clubMap = React.useMemo(() => new Map(clubs.map((c) => [c.code, c])), [clubs]);

  const rows = React.useMemo(() => {
    const list = [...(rankings[key] ?? [])].sort((a, b) => b.value - a.value);
    return list.map((r, i) => ({ ...r, rank: i + 1 }));
  }, [rankings, key]);

  const chartData = rows.slice(0, 12).map((r) => ({
    code: r.code,
    name: clubMap.get(r.code)?.short ?? r.code,
    value: r.value,
  }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1.5">
        {RANKING_ORDER.map((k) => (
          <button
            key={k}
            onClick={() => setKey(k)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              key === k
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
            )}
          >
            {RANKING_META[k].label}
          </button>
        ))}
      </div>

      <p className="text-sm text-muted-foreground">{meta.description}</p>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <RankingBars data={chartData} unit={meta.unit === "percent" ? "%" : ""} />
        </Card>

        <Card className="p-0">
          <div className="max-h-[360px] divide-y divide-border overflow-auto">
            {rows.map((r) => {
              const club = clubMap.get(r.code);
              return (
                <Link
                  key={r.code}
                  href={`/clubs/${r.code.toLowerCase()}${query}`}
                  className="flex items-center gap-3 px-4 py-2 transition-colors hover:bg-secondary/50"
                >
                  <span className="w-5 text-center text-xs font-semibold text-muted-foreground tabular-nums">
                    {r.rank}
                  </span>
                  <ClubBadge
                    code={r.code}
                    primary={club?.primary ?? "#334155"}
                    secondary={club?.secondary ?? "#0f172a"}
                    size="xs"
                  />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">
                    {club?.short ?? r.code}
                  </span>
                  <span className="text-sm font-semibold tabular-nums">
                    {formatValue(r.value, meta.unit)}
                  </span>
                </Link>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
