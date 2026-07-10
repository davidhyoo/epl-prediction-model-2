"use client";

import * as React from "react";
import { Search, SlidersHorizontal, CalendarX2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MatchCard } from "@/components/match/match-card";
import { EmptyState } from "@/components/empty-state";
import { cn } from "@/lib/utils";
import type { Match, Team } from "@/lib/types";
import type { ModelMeta } from "@/lib/model-meta";

type StatusFilter = "all" | "upcoming" | "completed" | "live";
type PhaseFilter = "all" | "group" | "knockout";
type SortKey = "date" | "confidence" | "round" | "team";

interface MatchesExplorerProps {
  matches: Match[];
  teams: Pick<Team, "code" | "name" | "iso2">[];
  modelMeta: ModelMeta;
  initialStatus?: StatusFilter;
}

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "upcoming", label: "Upcoming" },
  { key: "completed", label: "Completed" },
  { key: "live", label: "Live" },
];

export function MatchesExplorer({
  matches,
  teams,
  modelMeta,
  initialStatus = "all",
}: MatchesExplorerProps) {
  const [status, setStatus] = React.useState<StatusFilter>(initialStatus);
  const [phase, setPhase] = React.useState<PhaseFilter>("all");
  const [country, setCountry] = React.useState<string>("all");
  const [sort, setSort] = React.useState<SortKey>("date");
  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    let list = matches.slice();

    if (status !== "all") list = list.filter((m) => m.status === status);
    if (phase === "group") list = list.filter((m) => m.stage === "group");
    if (phase === "knockout") list = list.filter((m) => m.stage !== "group");
    if (country !== "all")
      list = list.filter((m) => m.home.code === country || m.away.code === country);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (m) =>
          m.home.name.toLowerCase().includes(q) ||
          m.away.name.toLowerCase().includes(q) ||
          m.venue.toLowerCase().includes(q) ||
          m.city.toLowerCase().includes(q),
      );
    }

    list.sort((a, b) => {
      switch (sort) {
        case "confidence":
          return b.ensemble.confidence - a.ensemble.confidence;
        case "round":
          return a.round - b.round || new Date(a.datetime).getTime() - new Date(b.datetime).getTime();
        case "team":
          return a.home.name.localeCompare(b.home.name);
        default:
          return new Date(a.datetime).getTime() - new Date(b.datetime).getTime();
      }
    });
    return list;
  }, [matches, status, phase, country, sort, query]);

  const sortedTeams = React.useMemo(
    () => teams.slice().sort((a, b) => a.name.localeCompare(b.name)),
    [teams],
  );

  return (
    <div className="space-y-5">
      {/* Filter bar */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg bg-muted p-1">
            {STATUS_TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setStatus(t.key)}
                className={cn(
                  "rounded-md px-3 py-1 text-sm font-medium transition-colors",
                  status === t.key
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="relative ml-auto w-full sm:w-56">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search team, city…"
              className="pl-8"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SlidersHorizontal className="size-4 text-muted-foreground" />
          <Select value={phase} onValueChange={(v) => setPhase(v as PhaseFilter)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All stages</SelectItem>
              <SelectItem value="group">Group stage</SelectItem>
              <SelectItem value="knockout">Knockout rounds</SelectItem>
            </SelectContent>
          </Select>

          <Select value={country} onValueChange={setCountry}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All countries" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All countries</SelectItem>
              {sortedTeams.map((t) => (
                <SelectItem key={t.code} value={t.code}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Sort: Date</SelectItem>
              <SelectItem value="confidence">Sort: Confidence</SelectItem>
              <SelectItem value="round">Sort: Round</SelectItem>
              <SelectItem value="team">Sort: Team name</SelectItem>
            </SelectContent>
          </Select>

          <Badge variant="muted" className="ml-auto">
            {filtered.length} match{filtered.length === 1 ? "" : "es"}
          </Badge>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<CalendarX2 />}
          title="No matches found"
          description="Try adjusting the filters or clearing the search query."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((m) => (
            <MatchCard key={m.id} match={m} modelMeta={modelMeta} />
          ))}
        </div>
      )}
    </div>
  );
}
