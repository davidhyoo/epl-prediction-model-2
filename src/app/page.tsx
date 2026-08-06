import Link from "next/link";
import {
  CalendarCheck2,
  CalendarClock,
  Trophy,
  Flame,
  Brain,
  ArrowUpRight,
  Target,
} from "lucide-react";
import { StatCard } from "@/components/stat-card";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClubBadge } from "@/components/club-badge";
import { FormPills } from "@/components/form-pills";
import { MatchList } from "@/components/match/match-list";
import { buildModelMeta } from "@/lib/model-meta";
import { getSelection, getDataset, getIndex } from "@/lib/data";
import { queryFor } from "@/lib/league";
import { pct, pctRaw, oddsPct, oddsWidth, formatDateTime } from "@/lib/format";
import type { SearchParams } from "@/lib/league";
import type { Club } from "@/lib/types";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [index, data] = await Promise.all([getIndex(), getDataset(sel)]);
  const { summary, clubs, matches, models, topScorers, players } = data;
  const query = queryFor(sel);
  const modelMeta = buildModelMeta(models.leaderboard);
  const preseason = summary.played === 0;

  const clubMap = new Map(clubs.map((c) => [c.code, c]));
  const league = index.leagues.find((l) => l.id === sel.league);

  // Title race: clubs by title odds (fallback to strength for a complete season).
  const titleRace = [...clubs]
    .sort((a, b) => b.odds.title - a.odds.title || b.strength.overall - a.strength.overall)
    .slice(0, 6);

  // Recent results + next fixtures.
  const completed = matches.filter((m) => m.status === "completed");
  const recent = completed.slice(-6).reverse();
  const upcoming = matches.filter((m) => m.status !== "completed").slice(0, 6);
  const showcase = (upcoming.length ? upcoming : recent).slice(0, 6);

  const scorerRows = topScorers
    .map((id) => players.find((p) => p.id === id))
    .filter((p): p is NonNullable<typeof p> => Boolean(p))
    .slice(0, 6);

  const hc = summary.highestConfidence;

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="app-aura absolute inset-0" />
        <div className="bg-grid absolute inset-0 opacity-60" />
        <div className="container-page relative py-12 sm:py-16">
          <div className="animate-fade-up space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="outline" className="gap-1.5">
                <span className="inline-block size-1.5 rounded-full bg-primary" />
                {league?.name}
              </Badge>
              <Badge variant="secondary">{summary.season.label}</Badge>
              <Badge variant={summary.season.role === "deliverable" ? "info" : "muted"}>
                {summary.season.role === "deliverable" ? "Pre-season forecast" : "Validation season"}
              </Badge>
            </div>
            <h1 className="max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
              <span className="text-gradient">{league?.short}</span> predictions,
              <br className="hidden sm:block" /> powered by machine learning.
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground sm:text-base">
              Live standings, per-match win probabilities from six models, and Monte-Carlo season
              simulations for the title, Europe and relegation — rebuilt from open data every time you
              refresh. Results loaded through {formatDateTime(summary.lastUpdated)}.
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <Link
                href={`/table${query}`}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                View the table <ArrowUpRight className="size-4" />
              </Link>
              <Link
                href={`/predictions${query}`}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:bg-secondary"
              >
                Season simulation
              </Link>
            </div>
          </div>
        </div>
      </section>

      <div className="container-page space-y-10 py-8">
        {/* Summary cards */}
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            label="Matches completed"
            value={summary.played}
            sub={`of ${summary.totalMatches} this season`}
            icon={<CalendarCheck2 />}
            accent="success"
          />
          <StatCard
            label="Matches upcoming"
            value={summary.upcoming}
            sub={preseason ? "Season not started" : "Still to play"}
            icon={<CalendarClock />}
            accent="info"
          />
          <StatCard
            label="Predicted champion"
            value={summary.champion ? clubMap.get(summary.champion.code)?.short ?? summary.champion.name : "—"}
            sub={summary.champion ? `${pctRaw(summary.champion.probability)} title chance` : "TBD"}
            icon={<Trophy />}
            accent="warning"
          />
          <StatCard
            label="Highest-confidence pick"
            value={hc ? `${pctRaw(hc.confidence)}` : "—"}
            sub={hc ? `${hc.home} vs ${hc.away}` : "Season complete"}
            icon={<Target />}
            accent="primary"
          />
          <StatCard
            label="Best model so far"
            value={summary.bestModel ? summary.bestModel.name : "—"}
            sub={summary.bestModel ? `${pct(summary.bestModel.accuracy)} accuracy` : "Awaiting results"}
            icon={<Brain />}
            accent="muted"
          />
        </section>

        {/* Title race + top scorers */}
        <section className="grid gap-6 lg:grid-cols-3">
          <Card className="p-5 lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Trophy className="size-4 text-warning" /> Title race
              </h2>
              <Link href={`/rankings${query}`} className="text-xs text-muted-foreground hover:text-foreground">
                All rankings →
              </Link>
            </div>
            <div className="space-y-2.5">
              {titleRace.map((c) => (
                <TitleRow key={c.code} club={c} query={query} preseason={preseason} />
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Flame className="size-4 text-destructive" /> Top scorers
              </h2>
              <Link href={`/players${query}`} className="text-xs text-muted-foreground hover:text-foreground">
                All players →
              </Link>
            </div>
            {scorerRows.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No goals recorded yet this season.
              </p>
            ) : (
              <ol className="space-y-2.5">
                {scorerRows.map((p, i) => (
                  <li key={p.id} className="flex items-center gap-3">
                    <span className="w-4 text-center text-xs font-semibold text-muted-foreground tabular-nums">
                      {i + 1}
                    </span>
                    <ClubBadge
                      code={p.club}
                      primary={clubMap.get(p.club)?.primary ?? "#334155"}
                      secondary={clubMap.get(p.club)?.secondary ?? "#0f172a"}
                      size="xs"
                    />
                    <Link
                      href={`/players/${p.id}${query}`}
                      className="min-w-0 flex-1 truncate text-sm font-medium hover:text-primary"
                    >
                      {p.name}
                    </Link>
                    <span className="text-sm font-bold tabular-nums">{p.goals}</span>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </section>

        {/* Matches showcase */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">
              {upcoming.length ? "Next fixtures" : "Recent results"}
            </h2>
            <Link href={`/matches${query}`} className="text-sm text-muted-foreground hover:text-foreground">
              View all matches →
            </Link>
          </div>
          <MatchList matches={showcase} modelMeta={modelMeta} />
        </section>
      </div>
    </div>
  );
}

function TitleRow({ club, query, preseason }: { club: Club; query: string; preseason: boolean }) {
  void preseason;
  const value = club.odds.title;
  return (
    <div className="flex items-center gap-3">
      <Link
        href={`/clubs/${club.code.toLowerCase()}${query}`}
        className="flex min-w-0 flex-1 items-center gap-2.5 hover:text-primary"
      >
        <ClubBadge code={club.code} primary={club.primary} secondary={club.secondary} size="sm" />
        <span className="truncate text-sm font-medium">{club.short}</span>
      </Link>
      <div className="hidden w-28 sm:block">
        <FormPills form={club.standing.form} />
      </div>
      <div className="w-40">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Title</span>
          <span className="font-semibold tabular-nums">{oddsPct(value)}</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
            style={{ width: `${oddsWidth(value, 2)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
