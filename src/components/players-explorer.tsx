"use client";

import * as React from "react";
import Link from "next/link";
import { Search, Users } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Flag } from "@/components/flag";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { EmptyState } from "@/components/empty-state";
import type { Player, Position } from "@/lib/types";

type SortKey =
  | "rating"
  | "name"
  | "country"
  | "position"
  | "goals"
  | "appearances"
  | "minutes"
  | "contribution";

const POSITIONS: Position[] = ["GK", "DEF", "MID", "FWD"];
const PAGE = 40;

const SORTS: { key: SortKey; label: string }[] = [
  { key: "rating", label: "Rating" },
  { key: "contribution", label: "Contribution" },
  { key: "goals", label: "Goals" },
  { key: "appearances", label: "Appearances" },
  { key: "minutes", label: "Minutes" },
  { key: "name", label: "Name" },
  { key: "country", label: "Country" },
  { key: "position", label: "Position" },
];

export function PlayersExplorer() {
  const [players, setPlayers] = React.useState<Player[] | null>(null);
  const [query, setQuery] = React.useState("");
  const [country, setCountry] = React.useState("all");
  const [position, setPosition] = React.useState("all");
  const [sort, setSort] = React.useState<SortKey>("rating");
  const [visible, setVisible] = React.useState(PAGE);

  React.useEffect(() => {
    let active = true;
    fetch("/data/players.json")
      .then((r) => r.json())
      .then((data: Player[]) => {
        if (active) setPlayers(data);
      })
      .catch(() => active && setPlayers([]));
    return () => {
      active = false;
    };
  }, []);

  // Reset pagination whenever the filters change, using the React-recommended
  // "adjust state during render" pattern instead of an effect.
  const filterKey = `${query}|${country}|${position}|${sort}`;
  const [prevFilterKey, setPrevFilterKey] = React.useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setVisible(PAGE);
  }

  const countries = React.useMemo(() => {
    if (!players) return [];
    const map = new Map<string, { code: string; name: string; iso2: string }>();
    for (const p of players) {
      if (!map.has(p.countryCode))
        map.set(p.countryCode, { code: p.countryCode, name: p.country, iso2: p.iso2 });
    }
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [players]);

  const filtered = React.useMemo(() => {
    if (!players) return [];
    let list = players.slice();
    if (country !== "all") list = list.filter((p) => p.countryCode === country);
    if (position !== "all") list = list.filter((p) => p.position === position);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (p) => p.name.toLowerCase().includes(q) || p.club.toLowerCase().includes(q),
      );
    }
    list.sort((a, b) => {
      switch (sort) {
        case "name":
          return a.name.localeCompare(b.name);
        case "country":
          return a.country.localeCompare(b.country) || b.rating - a.rating;
        case "position":
          return (
            POSITIONS.indexOf(a.position) - POSITIONS.indexOf(b.position) || b.rating - a.rating
          );
        case "goals":
          return b.stats.goals - a.stats.goals;
        case "appearances":
          return b.stats.appearances - a.stats.appearances || b.stats.minutes - a.stats.minutes;
        case "minutes":
          return b.stats.minutes - a.stats.minutes;
        case "contribution":
          return b.contribution - a.contribution;
        default:
          return b.rating - a.rating;
      }
    });
    return list;
  }, [players, country, position, query, sort]);

  if (!players) return <PlayersSkeleton />;

  const shown = filtered.slice(0, visible);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-60">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search players or clubs…"
            className="pl-8"
          />
        </div>
        <Select value={country} onValueChange={setCountry}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All countries" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All countries</SelectItem>
            {countries.map((c) => (
              <SelectItem key={c.code} value={c.code}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={position} onValueChange={setPosition}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Position" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All positions</SelectItem>
            {POSITIONS.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORTS.map((s) => (
              <SelectItem key={s.key} value={s.key}>
                Sort: {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Badge variant="muted" className="ml-auto">
          {filtered.length} players
        </Badge>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={<Users />}
          title="No players found"
          description="Adjust the filters or search for a different name or club."
        />
      ) : (
        <>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead className="hidden sm:table-cell">Country</TableHead>
                  <TableHead className="w-14">Pos</TableHead>
                  <TableHead className="hidden lg:table-cell">Club</TableHead>
                  <TableHead className="hidden w-12 text-right md:table-cell">Age</TableHead>
                  <TableHead className="w-12 text-right">G</TableHead>
                  <TableHead className="w-12 text-right">Apps</TableHead>
                  <TableHead className="hidden w-16 text-right sm:table-cell">Min</TableHead>
                  <TableHead className="w-16 text-right">Rating</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((p, i) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">
                      {i + 1}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/players/${p.id}`}
                        className="flex items-center gap-2.5 font-medium hover:underline"
                      >
                        <PlayerAvatar name={p.name} src={p.headshot} size="sm" />
                        <span className="truncate">{p.name}</span>
                      </Link>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <Link
                        href={`/countries/${p.countryCode.toLowerCase()}`}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                      >
                        <Flag iso2={p.iso2} size="sm" />
                        <span className="hidden truncate lg:inline">{p.country}</span>
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-[10px]">
                        {p.position}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden text-sm text-muted-foreground lg:table-cell">
                      {p.club}
                    </TableCell>
                    <TableCell className="hidden text-right text-sm tabular-nums md:table-cell">
                      {p.age ?? "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">{p.stats.goals}</TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {p.stats.appearances}
                    </TableCell>
                    <TableCell className="hidden text-right text-sm tabular-nums sm:table-cell">
                      {p.stats.minutes.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <RatingPill rating={p.rating} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
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

function PlayersSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-9 w-60" />
        <Skeleton className="h-9 w-44" />
        <Skeleton className="h-9 w-36" />
        <Skeleton className="h-9 w-48" />
      </div>
      <div className="space-y-2 rounded-lg border border-border p-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="size-8 rounded-full" />
            <Skeleton className="h-4 w-40" />
            <Skeleton className="ml-auto h-4 w-10" />
          </div>
        ))}
      </div>
    </div>
  );
}
