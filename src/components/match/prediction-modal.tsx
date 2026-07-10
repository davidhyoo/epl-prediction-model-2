"use client";

import * as React from "react";
import { ArrowRight, Info, TrendingUp, CircleCheck, CircleX, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Flag } from "@/components/flag";
import { ProbabilityBar } from "@/components/probability-bar";
import { cn } from "@/lib/utils";
import { pct, OUTCOME_LABEL } from "@/lib/format";
import type { Match, ModelInfo, ModelPrediction } from "@/lib/types";

interface PredictionModalProps {
  match: Match;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  modelMeta?: Record<string, Pick<ModelInfo, "logLoss" | "brier" | "ece" | "rank" | "weight">>;
}

export function PredictionModal({ match, open, onOpenChange, modelMeta }: PredictionModalProps) {
  const { home, away, ensemble } = match;
  // Ensemble first, then the base models by rank if we have meta.
  const ordered = React.useMemo(() => {
    const models = [...match.models];
    return models.sort((a, b) => {
      if (a.model === "ensemble") return -1;
      if (b.model === "ensemble") return 1;
      const ra = modelMeta?.[a.model]?.rank ?? 99;
      const rb = modelMeta?.[b.model]?.rank ?? 99;
      return ra - rb;
    });
  }, [match.models, modelMeta]);

  const winnerName = (m: ModelPrediction) =>
    m.predictedOutcome === "draw" ? "Draw" : m.winner;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{match.stageLabel}</Badge>
            {match.group && <span>Group {match.group}</span>}
            {match.projectedMatchup && (
              <Badge variant="outline" className="gap-1">
                <Sparkles className="size-3" /> Projected matchup
              </Badge>
            )}
          </div>
          <DialogTitle className="flex flex-wrap items-center gap-3 pt-1">
            <span className="flex items-center gap-2">
              <Flag iso2={home.iso2} size="md" />
              {home.name}
            </span>
            <span className="text-sm font-normal text-muted-foreground">vs</span>
            <span className="flex items-center gap-2">
              <Flag iso2={away.iso2} size="md" />
              {away.name}
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* Ensemble headline */}
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="size-4 text-primary" />
              Ensemble forecast
            </div>
            <span className="text-xs text-muted-foreground">
              Predicts {OUTCOME_LABEL[ensemble.predictedOutcome].toLowerCase()}
            </span>
          </div>
          <ProbabilityBar
            homeProb={ensemble.probs.home}
            drawProb={ensemble.probs.draw}
            awayProb={ensemble.probs.away}
            homeColor={home.colors.primary}
            awayColor={away.colors.primary}
            homeLabel={home.code}
            awayLabel={away.code}
            size="lg"
          />

          {match.status === "completed" && match.score && (
            <div className="mt-3 flex items-center gap-2 border-t border-border pt-3 text-sm">
              {match.correct ? (
                <CircleCheck className="size-4 text-success" />
              ) : (
                <CircleX className="size-4 text-destructive" />
              )}
              <span className="font-medium">
                Final score {match.score.home}–{match.score.away}
              </span>
              <span className="text-muted-foreground">
                · Ensemble was {match.correct ? "correct" : "incorrect"}
              </span>
            </div>
          )}
        </div>

        {/* Model breakdown */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="size-4 text-muted-foreground" />
            Model breakdown
          </div>
          <div className="space-y-2">
            {ordered.map((m) => {
              const meta = modelMeta?.[m.model];
              return (
                <div key={m.model} className="rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{m.modelName}</span>
                      {meta && (
                        <Badge variant="outline" className="text-[10px]">
                          #{meta.rank}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span>
                        Picks <span className="font-medium text-foreground">{winnerName(m)}</span>
                      </span>
                      <span>·</span>
                      <span className="tabular-nums">{pct(m.confidence)} conf.</span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <ProbabilityBar
                      homeProb={m.probs.home}
                      drawProb={m.probs.draw}
                      awayProb={m.probs.away}
                      homeColor={home.colors.primary}
                      awayColor={away.colors.primary}
                      homeLabel={home.code}
                      awayLabel={away.code}
                      showLabels={false}
                      size="sm"
                    />
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground tabular-nums">
                    <span>Accuracy {pct(m.accuracy)}</span>
                    {meta && <span>Log loss {meta.logLoss.toFixed(3)}</span>}
                    {meta && <span>Brier {meta.brier.toFixed(3)}</span>}
                    {meta && m.model !== "ensemble" && (
                      <span>Ensemble weight {pct(meta.weight)}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top contributing factors */}
        {match.factors.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Info className="size-4 text-muted-foreground" />
              Top contributing factors
            </div>
            <div className="space-y-2">
              {match.factors.slice(0, 5).map((f, i) => {
                const favorTeam =
                  f.favors === "home" ? home : f.favors === "away" ? away : null;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-44 shrink-0 text-xs font-medium">{f.label}</div>
                    <div className="flex-1">
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            f.favors === "home"
                              ? "bg-primary"
                              : f.favors === "away"
                                ? "bg-info"
                                : "bg-muted-foreground/50",
                          )}
                          style={{ width: `${Math.round(f.weight * 100)}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex w-16 shrink-0 items-center justify-end gap-1 text-[11px] text-muted-foreground">
                      {favorTeam ? (
                        <>
                          <ArrowRight className="size-3" />
                          <Flag iso2={favorTeam.iso2} size="sm" />
                        </>
                      ) : (
                        <span>Even</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Factor weights are model-derived heuristics that summarise why the forecast
              leans as it does — they explain, but do not guarantee, the outcome.
            </p>
          </div>
        )}

        <p className="flex items-center gap-1.5 rounded-md bg-muted/50 px-3 py-2 text-[11px] text-muted-foreground">
          <Info className="size-3.5 shrink-0" />
          Predictions are probabilistic estimates from models trained on generated demo
          data. They are for illustration and are not betting advice.
        </p>
      </DialogContent>
    </Dialog>
  );
}
