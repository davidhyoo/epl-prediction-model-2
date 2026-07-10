"use client";

import * as React from "react";
import Link from "next/link";
import { Search, Globe2, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Flag } from "@/components/flag";
import { EmptyState } from "@/components/empty-state";
import { cn } from "@/lib/utils";
import { pct } from "@/lib/format";
import type { Team } from "@/lib/types";

type SortKey = "champion" | "elo" | "name" | "group";

export function CountriesExplorer({ teams }: { teams: Team[] }) {
  const [query, setQuery] = React.useState("");
  const [conf, setConf] = React.useState("all");
  const [group, setGroup] = React.useState("all");
  const [sort, setSort] = React.useState<SortKey>("champion");

  const confederations = React.useMemo(
    () => Array.from(new Set(teams.map((t) => t.confederation))).sort(),
    [teams],
  );
  const groups = React.useMemo(
    () => Array.from(new Set(teams.map((t) => t.group))).sort(),
    [teams],
  );
  const maxProb = Math.max(...teams.map((t) => t.championProb), 0.01);

  const filtered = React.useMemo(() => {
    let list = teams.slice();
    if (conf !== "all") list = list.filter((t) => t.confederation === conf);
    if (group !== "all") list = list.filter((t) => t.group === group);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter((t) => t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      switch (sort) {
        case "elo":
          return b.elo - a.elo;
        case "name":
          return a.name.localeCompare(b.name);
        case "group":
          return a.group.localeCompare(b.group) || b.championProb - a.championProb;
        default:
          return b.championProb - a.championProb;
      }
    });
    return list;
  }, [teams, conf, group, query, sort]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-60">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search countries…"
            className="pl-8"
          />
        </div>
        <Select value={conf} onValueChange={setConf}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Confederation" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All confederations</SelectItem>
            {confederations.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={group} onValueChange={setGroup}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Group" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All groups</SelectItem>
            {groups.map((g) => (
              <SelectItem key={g} value={g}>
                Group {g}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="champion">Sort: Title odds</SelectItem>
            <SelectItem value="elo">Sort: Elo rating</SelectItem>
            <SelectItem value="group">Sort: Group</SelectItem>
            <SelectItem value="name">Sort: Name</SelectItem>
          </SelectContent>
        </Select>
        <Badge variant="muted" className="ml-auto">
          {filtered.length} teams
        </Badge>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Globe2 />}
          title="No countries match"
          description="Try a different confederation, group or search term."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((t) => (
            <Link key={t.code} href={`/countries/${t.code.toLowerCase()}`}>
              <Card
                className={cn(
                  "group h-full p-4 transition-all hover:-translate-y-0.5 hover:shadow-md",
                  t.status === "eliminated" && "opacity-70",
                )}
              >
                <div className="flex items-center gap-3">
                  <Flag iso2={t.iso2} size="lg" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate font-semibold">{t.name}</span>
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span>Group {t.group}</span>
                      <span>·</span>
                      <span>{t.confederation}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Title odds</span>
                  {t.status === "eliminated" ? (
                    <Badge variant="destructive">Eliminated</Badge>
                  ) : (
                    <span className="font-semibold tabular-nums">{pct(t.championProb)}</span>
                  )}
                </div>
                <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(t.championProb / maxProb) * 100}%` }}
                  />
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
                  <span>Elo {Math.round(t.elo)}</span>
                  <span className="tabular-nums">
                    {t.record.won}W · {t.record.drawn}D · {t.record.lost}L
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
