"use client";

import * as React from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Flag } from "@/components/flag";
import { RankingBars } from "@/components/charts/ranking-bars";
import { cn } from "@/lib/utils";
import type { Rankings, RankingView } from "@/lib/types";

function formatValue(v: RankingView, value: number): string {
  if (v.format === "percent") return `${value.toFixed(1)}%`;
  if (v.format === "rating") return value.toFixed(1);
  return value.toFixed(0);
}

export function RankingsExplorer({ rankings }: { rankings: Rankings }) {
  const [viewId, setViewId] = React.useState(rankings.views[0]?.id);
  const [conf, setConf] = React.useState("all");

  const view = rankings.views.find((v) => v.id === viewId) ?? rankings.views[0];

  const confederations = React.useMemo(
    () => Array.from(new Set(view.entries.map((e) => e.confederation))).sort(),
    [view],
  );

  const entries = React.useMemo(() => {
    const list =
      conf === "all" ? view.entries : view.entries.filter((e) => e.confederation === conf);
    return list.slice().sort((a, b) => b.value - a.value);
  }, [view, conf]);

  const maxValue = Math.max(...entries.map((e) => e.value), 0.0001);
  const chartData = entries.slice(0, 12).map((e) => ({ code: e.code, name: e.name, value: e.value }));

  return (
    <div className="space-y-5">
      {/* View selector */}
      <div className="flex flex-wrap gap-2">
        {rankings.views.map((v) => (
          <button
            key={v.id}
            onClick={() => setViewId(v.id)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
              v.id === viewId
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:bg-secondary",
            )}
          >
            {v.name}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chart */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{view.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{view.description}</p>
          </CardHeader>
          <CardContent>
            <RankingBars data={chartData} unit={view.unit} />
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base">Full ranking</CardTitle>
            <Select value={conf} onValueChange={setConf}>
              <SelectTrigger className="w-40">
                <SelectValue />
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
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10">#</TableHead>
                  <TableHead>Team</TableHead>
                  <TableHead className="hidden sm:table-cell">Group</TableHead>
                  <TableHead className="w-1/3">Value</TableHead>
                  <TableHead className="w-16 text-right">{view.unit || "Val"}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((e, i) => (
                  <TableRow key={e.code}>
                    <TableCell className="text-sm font-semibold text-muted-foreground tabular-nums">
                      {i + 1}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/countries/${e.code.toLowerCase()}`}
                        className="flex items-center gap-2 font-medium hover:underline"
                      >
                        <Flag iso2={e.iso2} size="sm" />
                        <span className="truncate">{e.name}</span>
                      </Link>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <Badge variant="secondary" className="text-[10px]">
                        {e.group}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary"
                          style={{ width: `${(e.value / maxValue) * 100}%` }}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-sm font-semibold tabular-nums">
                      {formatValue(view, e.value)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
