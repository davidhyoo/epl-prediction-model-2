"use client";

import * as React from "react";
import { AlertTriangle, Info } from "lucide-react";
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { CalibrationChart } from "@/components/charts/calibration-chart";
import { ImportanceBars } from "@/components/charts/importance-bars";
import { pct } from "@/lib/format";
import type { ModelInfo } from "@/lib/types";

const TYPE_VARIANT: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
  ensemble: "default",
  boosting: "info",
  tree: "success",
  linear: "warning",
  baseline: "muted",
};

export function ModelsExplorer({ models }: { models: ModelInfo[] }) {
  const sorted = React.useMemo(() => models.slice().sort((a, b) => a.rank - b.rank), [models]);
  const [selectedId, setSelectedId] = React.useState(sorted[0]?.id);
  const selected = sorted.find((m) => m.id === selectedId) ?? sorted[0];

  return (
    <div className="space-y-6">
      {/* Leaderboard */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Model leaderboard</CardTitle>
          <p className="text-sm text-muted-foreground">
            Ranked by log loss on {selected.gamesEvaluated} completed matches. Select a row for
            calibration and feature detail.
          </p>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-10">#</TableHead>
                <TableHead>Model</TableHead>
                <MetricHead label="Accuracy" hint="Share of matches where the argmax class was correct." />
                <MetricHead label="Log loss" hint="Penalises confident wrong probabilities. Lower is better." />
                <MetricHead label="Brier" hint="Mean squared error of the probability vector. Lower is better." />
                <MetricHead label="ECE" hint="Expected calibration error — gap between confidence and accuracy." />
                <MetricHead label="Weight" hint="Share in the ensemble, set ∝ 1 / log loss." />
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((m) => (
                <TableRow
                  key={m.id}
                  onClick={() => setSelectedId(m.id)}
                  data-state={m.id === selectedId ? "selected" : undefined}
                  className="cursor-pointer"
                >
                  <TableCell className="font-semibold tabular-nums text-muted-foreground">
                    {m.rank}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{m.name}</span>
                      <Badge variant={TYPE_VARIANT[m.type]} className="text-[10px] capitalize">
                        {m.type}
                      </Badge>
                      {m.note && (
                        <Tooltip>
                          <TooltipTrigger>
                            <AlertTriangle className="size-3.5 text-warning" />
                          </TooltipTrigger>
                          <TooltipContent>{m.note}</TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">{pct(m.accuracy)}</TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {m.logLoss.toFixed(3)}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {m.brier.toFixed(3)}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {m.ece.toFixed(3)}
                  </TableCell>
                  <TableCell className="text-right text-sm font-medium tabular-nums">
                    {m.weight > 0 ? pct(m.weight) : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Selected model detail */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{selected.name}</CardTitle>
              <Badge variant={TYPE_VARIANT[selected.type]} className="capitalize">
                {selected.type}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{selected.description}</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Strengths. </span>
              {selected.strengths}
            </p>
            {selected.note && (
              <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <span>{selected.note}</span>
              </div>
            )}
            <div className="grid grid-cols-3 gap-2 text-center">
              <MiniStat label="Accuracy" value={pct(selected.accuracy)} />
              <MiniStat label="Avg. conf." value={pct(selected.avgConfidence)} />
              <MiniStat label="Games" value={String(selected.gamesEvaluated)} />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Feature importance
              </p>
              <ImportanceBars importances={selected.featureImportance} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Calibration reliability</CardTitle>
            <p className="text-sm text-muted-foreground">
              How predicted confidence compares to observed accuracy. Closer to the dashed line is
              better calibrated.
            </p>
          </CardHeader>
          <CardContent>
            {selected.calibration.length > 0 ? (
              <CalibrationChart bins={selected.calibration} />
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">
                Not enough evaluated matches to plot calibration.
              </p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              Expected calibration error (ECE): {selected.ece.toFixed(3)} · Brier score:{" "}
              {selected.brier.toFixed(3)}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricHead({ label, hint }: { label: string; hint: string }) {
  return (
    <TableHead className="text-right">
      <Tooltip>
        <TooltipTrigger className="inline-flex items-center gap-1">
          {label}
          <Info className="size-3 opacity-60" />
        </TooltipTrigger>
        <TooltipContent>{hint}</TooltipContent>
      </Tooltip>
    </TableHead>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/50 py-2">
      <div className="text-sm font-semibold tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  );
}
