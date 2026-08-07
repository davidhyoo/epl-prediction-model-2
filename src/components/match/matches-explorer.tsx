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
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MatchList } from "@/components/match/match-list";
import { EmptyState } from "@/components/empty-state";
import type { Match, Outcome, Probabilities, Selection } from "@/lib/types";
import type { ModelMeta } from "@/lib/model-meta";

type StatusFilter = "all" | "upcoming" | "live" | "completed";
type SortKey = "date" | "confidence" | "round" | "team";

const PAGE = 24; // cards rendered before "Show more" — keeps the DOM light

function pick(p: Probabilities): Outcome {
  if (p.home >= p.draw && p.home >= p.away) return "home";
  if (p.away >= p.home && p.away >= p.draw) return "away";
  return "draw";
}

/**
 * Matches explorer. The full fixture list (~730 KB) is fetched **client-side**
 * so it never bloats the server-rendered payload, and only a page of cards is
 * rendered at a time. Filters, sorting and the shared prediction modal all
 * operate on the in-memory list, so nothing needs a round-trip.
 */
export function MatchesExplorer({
  selection,
  clubs,
  modelMeta,
}: {
  selection: Selection;
  clubs: { code: string; short: string }[];
  modelMeta: ModelMeta;
}) {
  const [matches, setMatches] = React.useState<Match[] | null>(null);
  const [loadedKey, setLoadedKey] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<StatusFilter>("all");
  const [club, setClub] = React.useState<string>("all");
  const [sort, setSort] = React.useState<SortKey>("date");
  const [visible, setVisible] = React.useState(PAGE);

  const selKey = `${selection.league}/${selection.season}`;

  React.useEffect(() => {
    let active = true;
    fetch(`/data/${selection.league}/${selection.season}/matches.json`)
      .then((r) => r.json())
      .then((data: Match[]) => {
        if (!active) return;
        setMatches(data);
        setLoadedKey(selKey);
      })
      .catch(() => {
        if (!active) return;
        setMatches([]);
        setLoadedKey(selKey);
      });
    return () => {
      active = false;
    };
  }, [selKey, selection.league, selection.season]);

  // Reset pagination whenever the filter/sort set changes.
  const filterKey = `${status}|${club}|${sort}`;
  const [prevKey, setPrevKey] = React.useState(filterKey);
  if (filterKey !== prevKey) {
    setPrevKey(filterKey);
    setVisible(PAGE);
  }

  const filtered = React.useMemo(() => {
    if (!matches) return [];
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
    const src = matches ?? [];
    return {
      all: src.length,
      upcoming: src.filter((m) => m.status === "upcoming").length,
      live: src.filter((m) => m.status === "live").length,
      completed: src.filter((m) => m.status === "completed").length,
    };
  }, [matches]);

  if (!matches || loadedKey !== selKey) return <MatchesSkeleton />;

  const statusOptions: { id: StatusFilter; label: string }[] = [
    { id: "all", label: `All (${counts.all})` },
    { id: "completed", label: `Completed (${counts.completed})` },
    { id: "upcoming", label: `Upcoming (${counts.upcoming})` },
  ];
  if (counts.live > 0) statusOptions.splice(1, 0, { id: "live", label: `Live (${counts.live})` });

  const shown = filtered.slice(0, visible);

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
          title={counts.all === 0 ? "Fixtures not published yet" : "No matches match these filters"}
          description={
            counts.all === 0
              ? "The league-phase draw hasn't been made yet, so there are no fixtures to show. Refresh once the draw lands to pull the real schedule."
              : "Try widening the status filter or clearing the club selection."
          }
        />
      ) : (
        <>
          <MatchList matches={shown} modelMeta={modelMeta} />
          {visible < filtered.length && (
            <div className="flex justify-center">
              <Button variant="outline" onClick={() => setVisible((v) => v + PAGE)}>
                Show more ({filtered.length - visible} remaining)
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MatchesSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Skeleton className="h-10 w-64" />
        <div className="ml-auto flex gap-2">
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-9 w-44" />
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 9 }).map((_, i) => (
          <Skeleton key={i} className="h-[132px] rounded-xl" />
        ))}
      </div>
    </div>
  );
}

export { pick };
