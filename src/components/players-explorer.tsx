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
import type { Player, Position, Selection } from "@/lib/types";

type SortKey = "rating" | "goals" | "assists" | "name" | "club" | "position" | "nation" | "number";

const POSITIONS: Position[] = ["GK", "DEF", "MID", "FWD"];
const PAGE = 40;

const SORTS: { key: SortKey; label: string }[] = [
  { key: "rating", label: "Rating" },
  { key: "goals", label: "Goals" },
  { key: "assists", label: "Assists" },
  { key: "name", label: "Name" },
  { key: "club", label: "Club" },
  { key: "position", label: "Position" },
  { key: "nation", label: "Nation" },
  { key: "number", label: "Shirt number" },
];

export function PlayersExplorer({
  selection,
  query,
  clubs,
}: {
  selection: Selection;
  query: string;
  clubs: { code: string; short: string }[];
}) {
  const [players, setPlayers] = React.useState<Player[] | null>(null);
  const [loadedKey, setLoadedKey] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [club, setClub] = React.useState("all");
  const [position, setPosition] = React.useState("all");
  const [sort, setSort] = React.useState<SortKey>("rating");
  const [visible, setVisible] = React.useState(PAGE);

  const selKey = `${selection.league}/${selection.season}`;

  React.useEffect(() => {
    let active = true;
    fetch(`/data/${selection.league}/${selection.season}/players.json`)
      .then((r) => r.json())
      .then((data: { players: Player[] }) => {
        if (!active) return;
        setPlayers(data.players);
        setLoadedKey(selKey);
      })
      .catch(() => {
        if (!active) return;
        setPlayers([]);
        setLoadedKey(selKey);
      });
    return () => {
      active = false;
    };
  }, [selKey, selection.league, selection.season]);

  const filterKey = `${search}|${club}|${position}|${sort}`;
  const [prevKey, setPrevKey] = React.useState(filterKey);
  if (filterKey !== prevKey) {
    setPrevKey(filterKey);
    setVisible(PAGE);
  }

  const filtered = React.useMemo(() => {
    if (!players) return [];
    let list = players.slice();
    if (club !== "all") list = list.filter((p) => p.club === club);
    if (position !== "all") list = list.filter((p) => p.position === position);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.clubName.toLowerCase().includes(q) ||
          p.nationName.toLowerCase().includes(q),
      );
    }
    list.sort((a, b) => {
      switch (sort) {
        case "goals":
          return b.goals - a.goals || b.rating - a.rating;
        case "assists":
          return (b.assists ?? -1) - (a.assists ?? -1) || b.goals - a.goals || b.rating - a.rating;
        case "name":
          return a.name.localeCompare(b.name);
        case "club":
          return a.clubName.localeCompare(b.clubName) || b.rating - a.rating;
        case "position":
          return POSITIONS.indexOf(a.position) - POSITIONS.indexOf(b.position) || b.rating - a.rating;
        case "nation":
          return a.nationName.localeCompare(b.nationName) || b.rating - a.rating;
        case "number":
          return (a.shirtNumber ?? 99) - (b.shirtNumber ?? 99);
        default:
          return b.rating - a.rating;
      }
    });
    return list;
  }, [players, club, position, search, sort]);

  if (!players || loadedKey !== selKey) return <PlayersSkeleton />;

  const shown = filtered.slice(0, visible);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search players, clubs or nations…"
            className="pl-8"
          />
        </div>
        <Select value={club} onValueChange={setClub}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All clubs" />
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
          <SelectTrigger className="w-44">
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
          description="Adjust the filters or search for a different name, club or nation."
        />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead className="w-14">Pos</TableHead>
                  <TableHead className="hidden lg:table-cell">Club</TableHead>
                  <TableHead className="hidden sm:table-cell">Nation</TableHead>
                  <TableHead className="w-12 text-right">G</TableHead>
                  <TableHead className="w-12 text-right">A</TableHead>
                  <TableHead className="w-16 text-right">Rating</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((p, i) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">{i + 1}</TableCell>
                    <TableCell>
                      <Link
                        href={`/players/${p.id}${query}`}
                        className="flex items-center gap-2.5 font-medium hover:text-primary"
                      >
                        <PlayerAvatar name={p.name} src={p.headshot} size="sm" />
                        <span className="truncate">{p.name}</span>
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-[10px]">
                        {p.position}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden text-sm text-muted-foreground lg:table-cell">
                      {p.clubName}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <span className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Flag iso2={p.nationIso2} size="sm" />
                        <span className="hidden truncate xl:inline">{p.nationName}</span>
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium tabular-nums">
                      {p.goals}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                      {p.assists ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <RatingPill rating={Math.round(p.rating)} />
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
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-36" />
        <Skeleton className="h-9 w-44" />
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
