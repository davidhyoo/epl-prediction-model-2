import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { BracketBoard } from "@/components/bracket-board";
import { Flag } from "@/components/flag";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getBracket, getSummary, getTeams } from "@/lib/data";
import { pct, readableColor } from "@/lib/format";

export const metadata: Metadata = {
  title: "Predictions & Bracket",
  description:
    "Projected 2026 World Cup knockout bracket and Monte Carlo championship odds for all 48 nations.",
};

export default async function PredictionsPage() {
  const [summary, teams, bracket] = await Promise.all([getSummary(), getTeams(), getBracket()]);

  const contenders = teams
    .slice()
    .sort((a, b) => b.championProb - a.championProb)
    .slice(0, 16);
  const maxProb = contenders[0]?.championProb || 1;

  return (
    <div className="container-page space-y-8 py-8">
      <PageHeader
        eyebrow="Forecast"
        title="Predictions & bracket"
        description="A projected path to the final built from the current knockout draw. Championship odds come from a 20,000-run Monte Carlo simulation seeded on post-group-stage strength — eliminated teams are pinned to 0%."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.35fr]">
        {/* Champion odds */}
        <Card className="h-fit">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Championship odds</CardTitle>
            <p className="text-sm text-muted-foreground">
              Simulated title probability. These are estimates, not guarantees.
            </p>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {contenders.map((t, i) => {
              const c = readableColor(t.colors.primary);
              return (
                <div key={t.code} className="flex items-center gap-3">
                  <span className="w-4 text-right text-xs font-medium tabular-nums text-muted-foreground">
                    {i + 1}
                  </span>
                  <Flag iso2={t.iso2} size="sm" title={t.name} />
                  <span className="w-28 shrink-0 truncate text-sm font-medium">{t.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(t.championProb / maxProb) * 100}%`, background: c }}
                    />
                  </div>
                  <span className="w-12 text-right text-sm font-semibold tabular-nums">
                    {pct(t.championProb)}
                  </span>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Highlights */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="sm:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Projected champion</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Flag iso2={summary.topChampion.iso2} size="xl" title={summary.topChampion.name} />
                <div>
                  <div className="text-2xl font-semibold">{summary.topChampion.name}</div>
                  <div className="text-sm text-muted-foreground">
                    Leads the field with a {pct(summary.topChampion.prob)} simulated title chance.
                  </div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {summary.topContenders.slice(1, 6).map((c) => (
                  <Badge key={c.code} variant="secondary" className="gap-1.5">
                    <Flag iso2={c.iso2} size="sm" title={c.name} />
                    {c.name} · {pct(c.prob)}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-1 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Knockout matches
              </div>
              <div className="text-2xl font-semibold tabular-nums">{summary.matchesUpcoming}</div>
              <p className="text-xs text-muted-foreground">
                Round of 32 through the final, all still to be played.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="space-y-1 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Simulations run
              </div>
              <div className="text-2xl font-semibold tabular-nums">20,000</div>
              <p className="text-xs text-muted-foreground">
                Monte Carlo tournament rollouts from the current draw.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Projected knockout bracket</h2>
          <p className="text-sm text-muted-foreground">
            Rounds fill from the most likely winner of each tie. Teams marked{" "}
            <span className="italic">(proj.)</span> depend on results not yet played, so they update
            as the tournament progresses.
          </p>
        </div>
        <BracketBoard bracket={bracket} teams={teams} />
      </section>
    </div>
  );
}
