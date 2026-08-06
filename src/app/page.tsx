import Link from "next/link";
import {
  CalendarCheck,
  CalendarClock,
  Trophy,
  Target,
  Brain,
  ArrowRight,
  Sparkles,
  Database,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/stat-card";
import { Flag } from "@/components/flag";
import { MatchCard } from "@/components/match/match-card";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { getSummary, getMatches, getModels } from "@/lib/data";
import { pct, formatDateTime, formatMatchDate } from "@/lib/format";
import { buildModelMeta } from "@/lib/model-meta";

export default async function HomePage() {
  const [summary, matches, models] = await Promise.all([
    getSummary(),
    getMatches(),
    getModels(),
  ]);

  const modelMeta = buildModelMeta(models);
  const bestModel = models.find((m) => m.id === summary.bestModel.id) ?? models[0];
  const hiMatch = matches.find((m) => m.id === summary.highestConfidenceMatchId);

  const upcoming = matches
    .filter((m) => m.status === "upcoming")
    .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime())
    .slice(0, 3);
  const recent = matches
    .filter((m) => m.status === "completed")
    .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime())
    .slice(0, 3);

  const maxProb = Math.max(...summary.topContenders.map((c) => c.prob), 0.01);

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="bg-grid pointer-events-none absolute inset-0 opacity-70" />
        <div className="container-page relative py-14 md:py-20">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="default" className="gap-1.5">
              <Sparkles className="size-3" /> {summary.tournament}
            </Badge>
            <Badge variant="muted" className="gap-1.5">
              <Database className="size-3" /> Real open data · CC0 sources
            </Badge>
          </div>
          <h1 className="mt-4 max-w-3xl text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Predicting the {summary.tournament}, powered by machine learning.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-muted-foreground md:text-lg">
            Live-style forecasts across all {summary.totalMatches} matches — combining an Elo
            baseline, logistic regression, random forest and XGBoost into a calibrated ensemble,
            with tournament simulation for championship odds.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link href="/predictions">
                View predictions <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/matches">Explore all matches</Link>
            </Button>
            <span className="text-xs text-muted-foreground">
              Data as of {formatDateTime(summary.asOf)} · hosted by {summary.host}
            </span>
          </div>
        </div>
      </section>

      <div className="container-page space-y-10 py-10">
        {/* KPI cards */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard
            label="Matches completed"
            value={summary.matchesCompleted}
            sub={`of ${summary.totalMatches} scheduled`}
            icon={<CalendarCheck />}
            accent="success"
          />
          <StatCard
            label="Matches upcoming"
            value={summary.matchesUpcoming}
            sub={summary.matchesUpcoming > 0 ? "still to be played" : "tournament complete"}
            icon={<CalendarClock />}
            accent="info"
          />
          <StatCard
            label="Top predicted champion"
            value={
              <span className="flex items-center gap-2">
                <Flag iso2={summary.topChampion.iso2} size="md" />
                <span className="truncate">{summary.topChampion.name}</span>
              </span>
            }
            sub={`${pct(summary.topChampion.prob)} title probability`}
            icon={<Trophy />}
            accent="warning"
          />
          <StatCard
            label="Highest-confidence pick"
            value={hiMatch ? pct(hiMatch.ensemble.confidence) : "—"}
            sub={
              hiMatch
                ? `${hiMatch.home.code} vs ${hiMatch.away.code} · ${hiMatch.stageLabel}`
                : undefined
            }
            icon={<Target />}
            accent="primary"
          />
          <StatCard
            label="Best model so far"
            value={summary.bestModel.name}
            sub={`${pct(summary.bestModel.accuracy)} acc · ${summary.bestModel.logLoss.toFixed(
              3,
            )} log loss`}
            icon={<Brain />}
            accent="muted"
          />
        </section>

        {/* Championship race + side cards */}
        <section className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Championship race</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {summary.matchesUpcoming > 0
                    ? `Title probabilities from ${summary.matchesUpcoming} simulated knockout matches.`
                    : `Final standings — ${summary.topChampion.name} are world champions.`}
                </p>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link href="/rankings">
                  All rankings <ChevronRight className="size-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {summary.topContenders.map((c, i) => (
                <Link
                  key={c.code}
                  href={`/countries/${c.code.toLowerCase()}`}
                  className="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted/50"
                >
                  <span className="w-4 text-sm font-semibold text-muted-foreground">{i + 1}</span>
                  <Flag iso2={c.iso2} size="md" />
                  <span className="w-32 shrink-0 truncate text-sm font-medium">{c.name}</span>
                  <div className="flex-1">
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${(c.prob / maxProb) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="w-12 text-right text-sm font-semibold tabular-nums">
                    {pct(c.prob)}
                  </span>
                </Link>
              ))}
            </CardContent>
          </Card>

          <div className="space-y-6">
            {/* Highest confidence pick */}
            {hiMatch && (
              <Card>
                <CardHeader className="space-y-0 pb-3">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Target className="size-4 text-primary" /> Highest-confidence upcoming pick
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Flag iso2={hiMatch.home.iso2} size="md" />
                      <span className="text-sm font-semibold">{hiMatch.home.code}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{hiMatch.stageLabel}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{hiMatch.away.code}</span>
                      <Flag iso2={hiMatch.away.iso2} size="md" />
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <ConfidenceBadge value={hiMatch.ensemble.confidence} />
                    <span className="text-muted-foreground">
                      {formatMatchDate(hiMatch.datetime).date}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    The ensemble most strongly favours{" "}
                    <span className="font-medium text-foreground">
                      {hiMatch.ensemble.winner}
                    </span>{" "}
                    in this fixture.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Best model */}
            <Card>
              <CardHeader className="space-y-0 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Brain className="size-4 text-primary" /> Best-performing model
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{bestModel.name}</span>
                  <Badge variant="success">Rank #{bestModel.rank}</Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Metric label="Accuracy" value={pct(bestModel.accuracy)} />
                  <Metric label="Log loss" value={bestModel.logLoss.toFixed(3)} />
                  <Metric label="Brier" value={bestModel.brier.toFixed(3)} />
                </div>
                <Button asChild variant="ghost" size="sm" className="w-full">
                  <Link href="/models">
                    Compare all models <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Upcoming + recent */}
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Upcoming fixtures</h2>
              <Button asChild variant="ghost" size="sm">
                <Link href="/matches?status=upcoming">
                  All <ChevronRight className="size-4" />
                </Link>
              </Button>
            </div>
            <div className="space-y-3">
              {upcoming.length > 0 ? (
                upcoming.map((m) => (
                  <MatchCard key={m.id} match={m} modelMeta={modelMeta} />
                ))
              ) : (
                <Card className="flex flex-col items-center gap-2 p-8 text-center">
                  <Trophy className="size-8 text-warning" />
                  <p className="text-sm font-medium">The tournament is complete.</p>
                  <p className="text-xs text-muted-foreground">
                    {summary.topChampion.name} are the {summary.tournament} champions.
                  </p>
                </Card>
              )}
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Recent results</h2>
              <Button asChild variant="ghost" size="sm">
                <Link href="/matches?status=completed">
                  All <ChevronRight className="size-4" />
                </Link>
              </Button>
            </div>
            <div className="space-y-3">
              {recent.map((m) => (
                <MatchCard key={m.id} match={m} modelMeta={modelMeta} />
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/50 py-2">
      <div className="text-sm font-semibold tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  );
}
