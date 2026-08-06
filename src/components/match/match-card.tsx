"use client";

import * as React from "react";
import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClubBadge } from "@/components/club-badge";
import { ProbabilityBar } from "@/components/probability-bar";
import { cn } from "@/lib/utils";
import { pct, formatMatchDate } from "@/lib/format";
import type { Match, Outcome, Probabilities } from "@/lib/types";

function pick(p: Probabilities): Outcome {
  if (p.home >= p.draw && p.home >= p.away) return "home";
  if (p.away >= p.home && p.away >= p.draw) return "away";
  return "draw";
}

export const MatchCard = React.memo(function MatchCard({
  match,
  onOpenPrediction,
}: {
  match: Match;
  onOpenPrediction?: (m: Match) => void;
}) {
  const { home, away, prediction } = match;
  const completed = match.status === "completed" && match.homeGoals != null;
  const { date, time } = formatMatchDate(match.datetime);
  const p = pick(prediction.ensemble);
  const homeWon = completed && (match.homeGoals ?? 0) > (match.awayGoals ?? 0);
  const awayWon = completed && (match.awayGoals ?? 0) > (match.homeGoals ?? 0);

  return (
    <Card className="card-hover overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="font-medium text-foreground">MW {match.round}</span>
          <span>·</span>
          <span>
            {date} · {time}
          </span>
        </span>
        {match.status === "live" ? (
          <Badge variant="destructive" className="gap-1">
            <span className="live-dot inline-block size-1.5 rounded-full bg-current" /> Live
          </Badge>
        ) : completed ? (
          <Badge variant="muted">Full time</Badge>
        ) : (
          <Badge variant="info">Upcoming</Badge>
        )}
      </div>

      <div className="px-4 py-3">
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <div className={cn("flex items-center gap-2 justify-self-start", awayWon && "opacity-60")}>
            <ClubBadge code={home.code} primary={home.primary} secondary={home.secondary} size="sm" />
            <span className="truncate text-sm font-semibold">{home.short}</span>
          </div>

          <div className="px-2 text-center">
            {completed ? (
              <div className="flex items-center gap-1.5 text-lg font-bold tabular-nums">
                <span className={cn(!homeWon && "text-muted-foreground")}>{match.homeGoals}</span>
                <span className="text-muted-foreground">–</span>
                <span className={cn(!awayWon && "text-muted-foreground")}>{match.awayGoals}</span>
              </div>
            ) : (
              <span className="text-xs font-medium text-muted-foreground">vs</span>
            )}
          </div>

          <div className={cn("flex items-center gap-2 justify-self-end", homeWon && "opacity-60")}>
            <span className="truncate text-right text-sm font-semibold">{away.short}</span>
            <ClubBadge code={away.code} primary={away.primary} secondary={away.secondary} size="sm" />
          </div>
        </div>

        <button
          type="button"
          onClick={() => onOpenPrediction?.(match)}
          className="group mt-3 block w-full rounded-lg px-1 py-1 text-left transition-colors hover:bg-secondary/50"
          aria-label="View prediction detail"
        >
          <ProbabilityBar
            homeProb={prediction.ensemble.home}
            drawProb={prediction.ensemble.draw}
            awayProb={prediction.ensemble.away}
            homeColor={home.primary}
            awayColor={away.primary}
            homeLabel={home.code}
            awayLabel={away.code}
            size="md"
          />
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
            <span>
              Model tip:{" "}
              <span className="font-medium text-foreground">
                {p === "home" ? home.short : p === "away" ? away.short : "Draw"}
              </span>{" "}
              ({pct(prediction.confidence)})
              {completed && (
                <span
                  className={cn(
                    "ml-1.5 font-medium",
                    match.predictionCorrect ? "text-success" : "text-destructive",
                  )}
                >
                  {match.predictionCorrect ? "✓ hit" : "✗ miss"}
                </span>
              )}
            </span>
            <span className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
              Details <ChevronRight className="size-3" />
            </span>
          </div>
        </button>
      </div>
    </Card>
  );
});
