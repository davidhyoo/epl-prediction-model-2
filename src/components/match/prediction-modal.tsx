"use client";

import * as React from "react";
import { Info, TrendingUp, CircleCheck, CircleX, Sparkles, Trophy, ArrowRight } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ClubBadge } from "@/components/club-badge";
import { ProbabilityBar } from "@/components/probability-bar";
import { cn } from "@/lib/utils";
import { pct, OUTCOME_LABEL } from "@/lib/format";
import type { Match, Outcome, Probabilities } from "@/lib/types";
import type { ModelMeta } from "@/lib/model-meta";

/** Argmax outcome for a probability triple. */
function pick(p: Probabilities): Outcome {
  if (p.home >= p.draw && p.home >= p.away) return "home";
  if (p.away >= p.home && p.away >= p.draw) return "away";
  return "draw";
}

/** Order the models: ensemble first, then market, then by leaderboard rank. */
const MODEL_ORDER = ["ensemble", "market", "elo", "logreg", "forest", "xgb"];

export function PredictionModal({
  match,
  open,
  onOpenChange,
  modelMeta,
}: {
  match: Match;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  modelMeta: ModelMeta;
}) {
  const { home, away, prediction } = match;

  const winnerName = (o: Outcome) =>
    o === "home" ? home.short : o === "away" ? away.short : "Draw";

  const rows = React.useMemo(() => {
    const entries: Array<{ id: string; probs: Probabilities }> = [
      { id: "ensemble", probs: prediction.ensemble },
      ...Object.entries(prediction.models).map(([id, probs]) => ({ id, probs })),
    ];
    return entries
      .filter((e, i, arr) => arr.findIndex((x) => x.id === e.id) === i)
      .sort((a, b) => {
        const ia = MODEL_ORDER.indexOf(a.id);
        const ib = MODEL_ORDER.indexOf(b.id);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      });
  }, [prediction]);

  const ensPick = pick(prediction.ensemble);
  const homeScorers = match.scorers.filter((s) => s.team === home.code);
  const awayScorers = match.scorers.filter((s) => s.team === away.code);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">Matchweek {match.round}</Badge>
            <span className="capitalize">{match.status}</span>
          </div>
          <DialogTitle className="flex flex-wrap items-center gap-3 pt-1">
            <span className="flex items-center gap-2">
              <ClubBadge code={home.code} primary={home.primary} secondary={home.secondary} size="sm" />
              {home.name}
            </span>
            <span className="text-sm font-normal text-muted-foreground">vs</span>
            <span className="flex items-center gap-2">
              <ClubBadge code={away.code} primary={away.primary} secondary={away.secondary} size="sm" />
              {away.name}
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* Ensemble headline */}
        <div className="rounded-xl border border-border bg-muted/40 p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="size-4 text-primary" />
              Ensemble forecast
            </div>
            <span className="text-xs text-muted-foreground">
              Predicts {OUTCOME_LABEL[ensPick].toLowerCase()}
            </span>
          </div>
          <ProbabilityBar
            homeProb={prediction.ensemble.home}
            drawProb={prediction.ensemble.draw}
            awayProb={prediction.ensemble.away}
            homeColor={home.primary}
            awayColor={away.primary}
            homeLabel={home.short}
            awayLabel={away.short}
            size="lg"
          />

          {match.status === "completed" && match.homeGoals != null && (
            <div className="mt-3 space-y-2 border-t border-border pt-3">
              <div className="flex items-center gap-2 text-sm">
                {match.predictionCorrect ? (
                  <CircleCheck className="size-4 text-success" />
                ) : (
                  <CircleX className="size-4 text-destructive" />
                )}
                <span className="font-semibold tabular-nums">
                  Final {match.homeGoals}–{match.awayGoals}
                </span>
                <span className="text-muted-foreground">
                  · Ensemble was {match.predictionCorrect ? "correct" : "incorrect"}
                </span>
              </div>
              {match.scorers.length > 0 && (
                <div className="grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
                  <ScorerList label={home.short} scorers={homeScorers} />
                  <ScorerList label={away.short} scorers={awayScorers} align="right" />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Model breakdown */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="size-4 text-muted-foreground" />
            Top models & their forecasts
          </div>
          <div className="space-y-2">
            {rows.map(({ id, probs }) => {
              const meta = modelMeta[id];
              const o = pick(probs);
              return (
                <div key={id} className="rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{meta?.name ?? id}</span>
                      {meta && meta.rank > 0 && (
                        <Badge variant="outline" className="text-[10px]">#{meta.rank}</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span>
                        Picks <span className="font-medium text-foreground">{winnerName(o)}</span>
                      </span>
                      <span>·</span>
                      <span className="tabular-nums">{pct(probs[o])} conf.</span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <ProbabilityBar
                      homeProb={probs.home}
                      drawProb={probs.draw}
                      awayProb={probs.away}
                      homeColor={home.primary}
                      awayColor={away.primary}
                      homeLabel={home.short}
                      awayLabel={away.short}
                      showLabels={false}
                      size="sm"
                    />
                  </div>
                  {meta && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground tabular-nums">
                      {meta.accuracy != null && <span>Accuracy {pct(meta.accuracy)}</span>}
                      {meta.logLoss != null && <span>Log loss {meta.logLoss.toFixed(3)}</span>}
                      {meta.brier != null && <span>Brier {meta.brier.toFixed(3)}</span>}
                      {id !== "ensemble" && id !== "market" && meta.weight > 0 && (
                        <span>Ensemble weight {pct(meta.weight)}</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Top contributing factors */}
        {prediction.topFactors.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Info className="size-4 text-muted-foreground" />
              Top contributing factors
            </div>
            <div className="space-y-2">
              {prediction.topFactors.slice(0, 5).map((f, i) => {
                const favor = f.direction;
                const width = Math.min(100, Math.round(Math.abs(f.impact) * 140) + 8);
                return (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-40 shrink-0 text-xs font-medium">{f.label}</div>
                    <div className="flex-1">
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${width}%`,
                            background:
                              favor === "home"
                                ? home.primary
                                : favor === "away"
                                  ? away.primary
                                  : "hsl(var(--muted-foreground))",
                          }}
                        />
                      </div>
                    </div>
                    <div className="flex w-16 shrink-0 items-center justify-end gap-1 text-[11px] text-muted-foreground">
                      <ArrowRight className="size-3" />
                      <span className="font-medium">
                        {favor === "home" ? home.code : favor === "away" ? away.code : "Even"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Factor impacts are model-derived contributions (logistic-regression log-odds) that
              summarise why the forecast leans as it does — they explain, but do not guarantee, the
              outcome.
            </p>
          </div>
        )}

        <p className="flex items-center gap-1.5 rounded-md bg-muted/50 px-3 py-2 text-[11px] text-muted-foreground">
          <Trophy className="size-3.5 shrink-0" />
          Predictions are probabilistic estimates from models trained without seeing the target
          season. They are for illustration and analytics, not betting advice.
        </p>
      </DialogContent>
    </Dialog>
  );
}

function ScorerList({
  label,
  scorers,
  align = "left",
}: {
  label: string;
  scorers: Match["scorers"];
  align?: "left" | "right";
}) {
  if (scorers.length === 0) return <div />;
  return (
    <div className={cn(align === "right" && "sm:text-right")}>
      <span className="font-medium text-foreground">{label}</span>{" "}
      {scorers.map((s, i) => (
        <span key={i}>
          {s.player.split(" ").slice(-1)[0]} {s.minute}
          {s.penalty ? " (P)" : ""}
          {s.ownGoal ? " (OG)" : ""}
          {i < scorers.length - 1 ? ", " : ""}
        </span>
      ))}
    </div>
  );
}
