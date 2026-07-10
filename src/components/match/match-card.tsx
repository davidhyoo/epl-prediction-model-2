"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronRight, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Flag } from "@/components/flag";
import { ProbabilityBar } from "@/components/probability-bar";
import { PredictionModal } from "@/components/match/prediction-modal";
import { cn } from "@/lib/utils";
import { pct, formatMatchDate, STAGE_SHORT } from "@/lib/format";
import type { Match, ModelInfo } from "@/lib/types";

interface MatchCardProps {
  match: Match;
  modelMeta?: Record<string, Pick<ModelInfo, "logLoss" | "brier" | "ece" | "rank" | "weight">>;
  className?: string;
}

export function MatchCard({ match, modelMeta, className }: MatchCardProps) {
  const [open, setOpen] = React.useState(false);
  const { home, away, ensemble, status } = match;
  const dt = formatMatchDate(match.datetime);
  const completed = status === "completed";
  const homeWin = match.actualOutcome === "home";
  const awayWin = match.actualOutcome === "away";

  return (
    <>
      <Card className={cn("group flex flex-col p-4 transition-shadow hover:shadow-md", className)}>
        <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Badge variant="secondary" className="font-medium">
              {match.group ? `Group ${match.group}` : STAGE_SHORT[match.stage]}
            </Badge>
            {match.projectedMatchup && (
              <Badge variant="outline" className="gap-1 text-[10px]">
                <Sparkles className="size-2.5" /> Projected
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            {status === "live" && <span className="live-dot size-2 rounded-full bg-destructive" />}
            <span>
              {completed ? "Full time" : status === "live" ? "Live" : `${dt.weekday} ${dt.date} · ${dt.time}`}
            </span>
          </div>
        </div>

        <div className="space-y-1.5">
          <TeamRow
            iso2={home.iso2}
            name={home.name}
            code={home.code}
            score={completed && match.score ? match.score.home : null}
            win={homeWin}
            prob={ensemble.probs.home}
            showProb={!completed}
          />
          <TeamRow
            iso2={away.iso2}
            name={away.name}
            code={away.code}
            score={completed && match.score ? match.score.away : null}
            win={awayWin}
            prob={ensemble.probs.away}
            showProb={!completed}
          />
        </div>

        <button
          onClick={() => setOpen(true)}
          className="mt-3 rounded-lg border border-transparent p-1 text-left transition-colors hover:border-border hover:bg-muted/40"
          aria-label="View prediction details"
        >
          <ProbabilityBar
            homeProb={ensemble.probs.home}
            drawProb={ensemble.probs.draw}
            awayProb={ensemble.probs.away}
            homeColor={home.colors.primary}
            awayColor={away.colors.primary}
            homeLabel={home.code}
            awayLabel={away.code}
            size="sm"
          />
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Sparkles className="size-3 text-primary" />
              {completed
                ? match.correct
                  ? "Predicted correctly"
                  : "Prediction missed"
                : `Model edge: ${pct(ensemble.confidence)}`}
            </span>
            <span className="flex items-center gap-0.5 font-medium text-foreground opacity-0 transition-opacity group-hover:opacity-100">
              Details <ChevronRight className="size-3" />
            </span>
          </div>
        </button>
      </Card>

      <PredictionModal match={match} open={open} onOpenChange={setOpen} modelMeta={modelMeta} />
    </>
  );
}

function TeamRow({
  iso2,
  name,
  code,
  score,
  win,
  prob,
  showProb,
}: {
  iso2: string;
  name: string;
  code: string;
  score: number | null;
  win: boolean;
  prob: number;
  showProb: boolean;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", score !== null && !win && "opacity-60")}>
      <Flag iso2={iso2} size="md" />
      <Link
        href={`/countries/${code.toLowerCase()}`}
        className="flex-1 truncate text-sm font-medium hover:underline"
      >
        {name}
      </Link>
      {showProb ? (
        <span className="text-sm font-semibold tabular-nums text-muted-foreground">{pct(prob)}</span>
      ) : (
        <span className={cn("text-base font-bold tabular-nums", win && "text-foreground")}>
          {score}
        </span>
      )}
    </div>
  );
}
