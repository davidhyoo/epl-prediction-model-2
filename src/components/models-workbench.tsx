"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { Gauge, Trophy, Sparkles, Dice5 } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ModelsExplorer } from "@/components/models-explorer";
import { ClubBadge } from "@/components/club-badge";
import type { ModelsData, TitleRace } from "@/lib/types";

// recharts is heavy — load the chart only on the client, when this tab renders.
const TitleRaceChart = dynamic(
  () => import("@/components/charts/title-race-chart").then((m) => m.TitleRaceChart),
  { ssr: false, loading: () => <Skeleton className="h-[380px] w-full rounded-xl" /> },
);

/**
 * Two prediction layers, split into tabs:
 *   • Per-game — the six classifiers that price each fixture (home/draw/away).
 *   • Final winner — the Monte-Carlo simulation that turns those game-level
 *     edges into a season-long championship probability, traced over time.
 */
export function ModelsWorkbench({
  models,
  race,
  champion,
}: {
  models: ModelsData;
  race: TitleRace;
  champion: { code: string; name: string; probability: number } | null;
}) {
  const hasTimeline = race.checkpoints.length >= 2;
  const leader = race.clubs[0];
  const champClub = champion ? race.clubs.find((c) => c.code === champion.code) : undefined;

  return (
    <Tabs defaultValue="per-game" className="space-y-4">
      <TabsList className="grid w-full grid-cols-2 sm:inline-flex sm:w-auto">
        <TabsTrigger value="per-game" className="gap-1.5">
          <Gauge className="size-3.5" /> Per-game models
        </TabsTrigger>
        <TabsTrigger value="winner" className="gap-1.5">
          <Trophy className="size-3.5" /> Final winner
        </TabsTrigger>
      </TabsList>

      <TabsContent value="per-game" className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Six models price <strong className="text-foreground">every fixture</strong> into
          home / draw / away probabilities before kickoff. The table ranks them by how well those
          probabilities held up against real results; click a row to inspect its calibration.
        </p>
        <ModelsExplorer models={models} />
      </TabsContent>

      <TabsContent value="winner" className="space-y-4">
        <p className="text-sm text-muted-foreground">
          A separate <strong className="text-foreground">Monte-Carlo simulation</strong> turns the
          game-level edges into a season-long answer: it replays the remaining fixtures thousands of
          times to estimate each club&rsquo;s chance of lifting the trophy. The chart traces how that
          championship probability has shifted <strong className="text-foreground">matchday by
          matchday</strong> — wide open early, sharpening toward the eventual winner.
        </p>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
            <div>
              <CardTitle className="text-base">Title race · championship probability</CardTitle>
              <p className="text-sm text-muted-foreground">
                One line per club, {race.clubs.length} teams over {race.lastCompletedRound} matchdays.
              </p>
            </div>
            <Badge variant="outline" className="shrink-0 gap-1.5">
              <Dice5 className="size-3" /> Monte-Carlo · 4k seasons
            </Badge>
          </CardHeader>
          <CardContent>
            <TitleRaceChart race={race} />
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Trophy className="size-4 text-warning" /> Projected champion
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {champion && leader ? (
                <div className="flex items-center gap-3">
                  <ClubBadge
                    code={champion.code}
                    primary={champClub?.primary ?? "#334155"}
                    secondary={champClub?.secondary ?? "#0f172a"}
                    size="lg"
                  />
                  <div>
                    <p className="font-semibold">{champion.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {champion.probability.toFixed(1)}% title probability
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Awaiting the first results.</p>
              )}
              {hasTimeline && (
                <div className="space-y-1.5 border-t border-border pt-3">
                  <p className="text-xs font-medium text-muted-foreground">Peaked this season</p>
                  {race.clubs.slice(0, 5).map((c) => (
                    <div key={c.code} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <ClubBadge
                          code={c.code}
                          primary={c.primary}
                          secondary={c.secondary}
                          size="xs"
                        />
                        {c.short}
                      </span>
                      <span className="tabular-nums text-muted-foreground">
                        {c.peak.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="size-4 text-primary" /> How the winner is predicted
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm text-muted-foreground">
              <p>
                <strong className="text-foreground">Points already banked</strong> are fixed to their
                real results. Every remaining fixture is sampled from an independent-Poisson score
                model whose expected goals come from the two clubs&rsquo; Elo gap (home edge included).
              </p>
              <p>
                We run <strong className="text-foreground">thousands of full seasons</strong>, rank
                each simulated table by points → goal-difference → goals-for, and count how often each
                club finishes first. That share is its championship probability.
              </p>
              <p>
                For the timeline, ratings are <strong className="text-foreground">frozen at each
                matchday</strong> — so an early-season forecast can&rsquo;t peek at later form, which
                is exactly why the lines start uncertain and converge as results land. A club that is{" "}
                <strong className="text-foreground">mathematically eliminated</strong> is hard-zeroed.
              </p>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  );
}
