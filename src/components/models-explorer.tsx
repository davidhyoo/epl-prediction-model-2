"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { pct } from "@/lib/format";
import type { ModelsData } from "@/lib/types";

// recharts is heavy — load the calibration chart lazily on the client.
const CalibrationChart = dynamic(
  () => import("@/components/charts/calibration-chart").then((m) => m.CalibrationChart),
  { ssr: false, loading: () => <Skeleton className="h-[240px] w-full rounded-xl" /> },
);

const fmt = (v: number | null, digits = 3) => (v == null ? "—" : v.toFixed(digits));

export function ModelsExplorer({ models }: { models: ModelsData }) {
  const board = models.leaderboard;
  const evaluated = models.meta.evaluated;
  const [selected, setSelected] = React.useState(board[0]?.id ?? "");
  const active = board.find((m) => m.id === selected) ?? board[0];

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-8">#</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="text-right">Accuracy</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Log loss</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Brier</TableHead>
                <TableHead className="hidden text-right md:table-cell">ECE</TableHead>
                <TableHead className="hidden text-right md:table-cell">Avg conf</TableHead>
                <TableHead className="text-right">Weight</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {board.map((m) => (
                <TableRow
                  key={m.id}
                  onClick={() => setSelected(m.id)}
                  className={cn(
                    "cursor-pointer",
                    m.id === selected && "bg-secondary/60 hover:bg-secondary/60",
                  )}
                >
                  <TableCell className="text-xs font-semibold text-muted-foreground tabular-nums">
                    {m.rank}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{m.name}</span>
                      {m.rank === 1 && evaluated > 0 && <Badge variant="success">Best</Badge>}
                      {m.id === "ensemble" && <Badge variant="info">Ensemble</Badge>}
                    </div>
                    <p className="mt-0.5 hidden max-w-md text-xs text-muted-foreground lg:block">
                      {m.blurb}
                    </p>
                  </TableCell>
                  <TableCell className="text-right font-semibold tabular-nums">
                    {m.accuracy == null ? "—" : pct(m.accuracy, 1)}
                  </TableCell>
                  <TableCell className="hidden text-right text-sm tabular-nums sm:table-cell">
                    {fmt(m.logLoss)}
                  </TableCell>
                  <TableCell className="hidden text-right text-sm tabular-nums sm:table-cell">
                    {fmt(m.brier)}
                  </TableCell>
                  <TableCell className="hidden text-right text-sm tabular-nums md:table-cell">
                    {fmt(m.ece)}
                  </TableCell>
                  <TableCell className="hidden text-right text-sm tabular-nums md:table-cell">
                    {m.avgConfidence == null ? "—" : pct(m.avgConfidence, 1)}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {(m.weight * 100).toFixed(0)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Calibration · {active?.name}</CardTitle>
            <p className="text-sm text-muted-foreground">
              How predicted confidence (x) compares with the observed hit-rate (y). Points on the
              dashed line are perfectly calibrated.
            </p>
          </CardHeader>
          <CardContent>
            {active && active.calibration.length > 0 && evaluated > 0 ? (
              <CalibrationChart bins={active.calibration} />
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No completed matches to evaluate yet — calibration appears once results arrive.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Ensemble weights</CardTitle>
            <p className="text-sm text-muted-foreground">
              The ensemble blends its base learners in proportion to recent accuracy. Weak or
              redundant models are down-weighted automatically.
            </p>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {Object.entries(models.weights)
              .sort((a, b) => b[1] - a[1])
              .map(([id, w]) => {
                const model = board.find((m) => m.id === id);
                return (
                  <div key={id}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium">{model?.name ?? id}</span>
                      <span className="tabular-nums text-muted-foreground">
                        {(w * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                        style={{ width: `${w * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            <p className="pt-1 text-xs text-muted-foreground">
              Evaluated on {evaluated.toLocaleString()} completed matches.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
