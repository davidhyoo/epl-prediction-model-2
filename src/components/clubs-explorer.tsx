"use client";

import * as React from "react";
import Link from "next/link";
import { Search } from "lucide-react";
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
import { ClubBadge } from "@/components/club-badge";
import { FormPills } from "@/components/form-pills";
import { EmptyState } from "@/components/empty-state";
import { oddsPct } from "@/lib/format";
import type { Club } from "@/lib/types";

type SortKey = "position" | "title" | "strength" | "name";

export function ClubsExplorer({
  clubs,
  query,
  preseason,
  format,
}: {
  clubs: Club[];
  query: string;
  preseason: boolean;
  format?: string;
}) {
  const [q, setQ] = React.useState("");
  const [sort, setSort] = React.useState<SortKey>(preseason ? "title" : "position");
  const isCup = format === "tournament";
  const titleWord = isCup ? "trophy" : "title";

  const filtered = React.useMemo(() => {
    const needle = q.trim().toLowerCase();
    let out = clubs.filter(
      (c) => !needle || c.name.toLowerCase().includes(needle) || c.code.toLowerCase().includes(needle),
    );
    out = out.slice().sort((a, b) => {
      switch (sort) {
        case "title":
          return b.odds.title - a.odds.title || b.strength.overall - a.strength.overall;
        case "strength":
          return b.strength.overall - a.strength.overall;
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return a.standing.position - b.standing.position;
      }
    });
    return out;
  }, [clubs, q, sort]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search clubs…"
            className="pl-9"
          />
        </div>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="h-9 w-[11rem] text-xs sm:ml-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="position">Sort · Position</SelectItem>
            <SelectItem value="title">Sort · Title odds</SelectItem>
            <SelectItem value="strength">Sort · Strength</SelectItem>
            <SelectItem value="name">Sort · Name</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<Search />} title="No clubs found" description="Try a different search." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <Link key={c.code} href={`/clubs/${c.code.toLowerCase()}${query}`}>
              <Card className="card-hover h-full p-4">
                <div className="flex items-center gap-3">
                  <ClubBadge code={c.code} primary={c.primary} secondary={c.secondary} size="lg" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{c.short}</p>
                    <p className="text-xs text-muted-foreground">
                      {preseason ? `${oddsPct(c.odds.title)} ${titleWord}` : `#${c.standing.position} · ${c.standing.pts} pts`}
                    </p>
                  </div>
                  {!preseason && (
                    <Badge variant={c.standing.position <= 5 ? "success" : "muted"} className="tabular-nums">
                      #{c.standing.position}
                    </Badge>
                  )}
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <Metric label="Strength" value={c.strength.overall.toFixed(0)} />
                  <Metric label={isCup ? "Trophy" : "Title"} value={oddsPct(c.odds.title)} />
                  <Metric label={isCup ? "Out" : "Relegn"} value={oddsPct(c.odds.relegation)} />
                </div>

                {!preseason && (
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Form</span>
                    <FormPills form={c.standing.form} />
                  </div>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 py-1.5">
      <p className="font-semibold tabular-nums">{value}</p>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
    </div>
  );
}
