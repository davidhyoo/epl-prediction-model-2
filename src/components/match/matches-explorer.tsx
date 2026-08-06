"use client";

import * as React from "react";
import { CalendarX2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MatchList } from "@/components/match/match-list";
import { EmptyState } from "@/components/empty-state";
import type { Match, Outcome, Probabilities } from "@/lib/types";
import type { ModelMeta } from "@/lib/model-meta";

type StatusFilter = "all" | "upcoming" | "live" | "completed";
type SortKey = "date" | "confidence" | "round" | "team";

function pick(p: Probabilities): Outcome {
  if (p.home >= p.draw && p.home >= p.away) return "home";
  if (p.away >= p.home && p.away >= p.draw) return "away";
  return "draw";
}

export function MatchesExplorer({
  matches,
  clubs,
  modelMeta,
}: {
  matches: Match[];
  clubs: { code: string; short: string }[];
  modelMeta: ModelMeta;
}) {
  const [status, setStatus] = React.useState<StatusFilter>("all");
  const [club, setClub] = React.useState<string>("all");
  const [sort, setSort] = React.useState<SortKey>("date");

  const filtered = React.useMemo(() => {
    let out = matches.slice();
    if (status !== "all") out = out.filter((m) => m.status === status);
    if (club !== "all") out = out.filter((m) => m.home.code === club || m.away.code === club);
    out.sort((a, b) => {
      switch (sort) {
        case "confidence":
          return b.prediction.confidence - a.prediction.confidence;
        case "round":
          return a.round - b.round || a.datetime.localeCompare(b.datetime);
        case "team":
          return a.home.short.localeCompare(b.home.short);
        default:
          return a.datetime.localeCompare(b.datetime);
      }
    });
    return out;
  }, [matches, status, club, sort]);

  const counts = React.useMemo(() => {
    return {
      all: matches.length,
      upcoming: matches.filter((m) => m.status === "upcoming").length,
      live: matches.filter((m) => m.status === "live").length,
      completed: matches.filter((m) => m.status === "completed").length,
    };
  }, [matches]);

  const statusOptions: { id: StatusFilter; label: string }[] = [
    { id: "all", label: `All (${counts.all})` },
    { id: "completed", label: `Completed (${counts.completed})` },
    { id: "upcoming", label: `Upcoming (${counts.upcoming})` },
  ];
  if (counts.live > 0) statusOptions.splice(1, 0, { id: "live", label: `Live (${counts.live})` });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-card p-1">
          {statusOptions.map((o) => (
            <button
              key={o.id}
              onClick={() => setStatus(o.id)}
              className={
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors " +
                (status === o.id
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {o.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Select value={club} onValueChange={setClub}>
            <SelectTrigger className="h-9 w-[10rem] text-xs">
              <SelectValue placeholder="Club" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All clubs</SelectItem>
              {clubs.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.short}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
            <SelectTrigger className="h-9 w-[11rem] text-xs">
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Sort · Date</SelectItem>
              <SelectItem value="confidence">Sort · Confidence</SelectItem>
              <SelectItem value="round">Sort · Matchweek</SelectItem>
              <SelectItem value="team">Sort · Home team</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<CalendarX2 />}
          title="No matches match these filters"
          description="Try widening the status filter or clearing the club selection."
        />
      ) : (
        <MatchList matches={filtered} modelMeta={modelMeta} />
      )}
    </div>
  );
}

export { pick };
