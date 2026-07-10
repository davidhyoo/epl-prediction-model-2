import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { pct, readableColor } from "@/lib/format";
import { Flag } from "@/components/flag";
import { Badge } from "@/components/ui/badge";
import type { Bracket, BracketMatch, Team } from "@/lib/types";

const NEUTRAL = { primary: "#64748b", secondary: "#94a3b8" };

interface Resolved {
  name: string;
  iso2: string;
  color: string;
}

function makeResolver(teams: Team[]) {
  const map = new Map(teams.map((t) => [t.code, t]));
  return (code: string | null): Resolved | null => {
    if (!code) return null;
    const t = map.get(code);
    if (!t) return { name: code, iso2: "", color: NEUTRAL.primary };
    return { name: t.name, iso2: t.iso2, color: t.colors.primary };
  };
}

function TeamRow({
  team,
  prob,
  isWinner,
  projected,
}: {
  team: Resolved | null;
  prob: number | null;
  isWinner: boolean;
  projected: boolean;
}) {
  if (!team) {
    return (
      <div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
        <span className="h-4 w-6 shrink-0 rounded-[3px] border border-dashed border-border" />
        <span className="italic">To be decided</span>
      </div>
    );
  }
  return (
    <div className={cn("flex items-center gap-2 py-1 text-sm", isWinner && "font-semibold")}>
      <Flag iso2={team.iso2} size="sm" title={team.name} />
      <span className="min-w-0 flex-1 truncate">
        {team.name}
        {projected && <span className="ml-1 text-[10px] text-muted-foreground">(proj.)</span>}
      </span>
      {isWinner && <Check className="size-3.5 text-success" />}
      {prob != null && <span className="tabular-nums text-muted-foreground">{pct(prob)}</span>}
    </div>
  );
}

function MatchCard({ match, resolve }: { match: BracketMatch; resolve: (c: string | null) => Resolved | null }) {
  const home = resolve(match.home);
  const away = resolve(match.away);
  const homeWin = match.winner != null && match.winner === match.home;
  const awayWin = match.winner != null && match.winner === match.away;

  const hp = match.homeProb ?? 0.5;
  const ap = match.awayProb ?? 0.5;
  const homeC = readableColor(home?.color ?? NEUTRAL.primary);
  const awayC = readableColor(away?.color ?? NEUTRAL.secondary);

  return (
    <div className="rounded-lg border bg-card p-2.5 shadow-sm">
      <TeamRow team={home} prob={match.homeProb} isWinner={homeWin} projected={match.homeProjected} />
      {match.score ? (
        <div className="my-1 flex items-center justify-center gap-2 text-xs font-semibold tabular-nums text-muted-foreground">
          <span>
            {match.score.home}–{match.score.away}
          </span>
          {match.penalties && (
            <span className="text-[10px] font-normal">
              (pens {match.penalties.home}–{match.penalties.away})
            </span>
          )}
        </div>
      ) : (
        <div className="my-1 flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div style={{ width: `${(hp / (hp + ap)) * 100}%`, background: homeC }} />
          <div style={{ width: `${(ap / (hp + ap)) * 100}%`, background: awayC }} />
        </div>
      )}
      <TeamRow team={away} prob={match.awayProb} isWinner={awayWin} projected={match.awayProjected} />
    </div>
  );
}

export function BracketBoard({ bracket, teams }: { bracket: Bracket; teams: Team[] }) {
  const resolve = makeResolver(teams);
  const mainRounds = bracket.rounds.filter((r) => r.stage !== "third-place");
  const thirdPlace = bracket.rounds.find((r) => r.stage === "third-place");

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto pb-2">
        <div className="flex min-w-max gap-4">
          {mainRounds.map((round) => (
            <div key={round.stage} className="flex w-64 shrink-0 flex-col gap-3">
              <div className="sticky top-0 flex items-center justify-between">
                <h3 className="text-sm font-semibold">{round.label}</h3>
                <Badge variant="muted" className="text-[10px]">
                  {round.matches.length}
                </Badge>
              </div>
              <div
                className="flex flex-1 flex-col justify-around gap-3"
                style={{ minHeight: round.stage === "final" ? undefined : "auto" }}
              >
                {round.matches.map((m) => (
                  <MatchCard key={m.id} match={m} resolve={resolve} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {thirdPlace && thirdPlace.matches.length > 0 && (
        <div className="max-w-xs">
          <div className="mb-2 flex items-center gap-2">
            <h3 className="text-sm font-semibold">{thirdPlace.label}</h3>
          </div>
          <MatchCard match={thirdPlace.matches[0]} resolve={resolve} />
        </div>
      )}
    </div>
  );
}
