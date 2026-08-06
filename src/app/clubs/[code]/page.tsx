import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowLeft,
  Trophy,
  ShieldCheck,
  TrendingDown,
  Star,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ClubBadge } from "@/components/club-badge";
import { FormPills } from "@/components/form-pills";
import { StatCard } from "@/components/stat-card";
import { SquadTable } from "@/components/squad-table";
import { MatchList } from "@/components/match/match-list";
import { StrengthRadar } from "@/components/charts/strength-radar";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { Flag } from "@/components/flag";
import { buildModelMeta } from "@/lib/model-meta";
import {
  getSelection,
  getClubByCode,
  getPlayersByClub,
  getMatchesForClub,
  getModels,
} from "@/lib/data";
import { queryFor } from "@/lib/league";
import { oddsPct } from "@/lib/format";
import type { SearchParams } from "@/lib/league";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ code: string }>;
}): Promise<Metadata> {
  const { code } = await params;
  return { title: code.toUpperCase() };
}

export default async function ClubDetail({
  params,
  searchParams,
}: {
  params: Promise<{ code: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { code } = await params;
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const club = await getClubByCode(sel, code);
  if (!club) notFound();

  const [squad, clubMatches, models] = await Promise.all([
    getPlayersByClub(sel, club.code),
    getMatchesForClub(sel, club.code),
    getModels(sel),
  ]);
  const query = queryFor(sel);
  const modelMeta = buildModelMeta(models.leaderboard);
  const preseason = club.standing.played === 0;

  const played = clubMatches.filter((m) => m.status === "completed").slice(-6).reverse();
  const upcoming = clubMatches.filter((m) => m.status !== "completed").slice(0, 6);

  const keyPlayers = club.keyPlayers
    .map((id) => squad.find((p) => p.id === id))
    .filter((p): p is NonNullable<typeof p> => Boolean(p));

  const radar = [
    { metric: "Attack", value: club.strength.attack },
    { metric: "Defense", value: club.strength.defense },
    { metric: "Form", value: club.strength.form },
    { metric: "Overall", value: club.strength.overall },
    { metric: "PPG", value: Math.min(100, (club.strength.ppg / 3) * 100) },
  ];

  return (
    <div className="container-page space-y-6 py-8">
      <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit">
        <Link href={`/clubs${query}`}>
          <ArrowLeft className="mr-1.5 size-4" /> All clubs
        </Link>
      </Button>

      {/* Hero */}
      <Card className="glass overflow-hidden">
        <div className="app-aura h-20 w-full" />
        <CardContent className="-mt-10 flex flex-col gap-4 sm:flex-row sm:items-end">
          <ClubBadge code={club.code} primary={club.primary} secondary={club.secondary} size="xl" />
          <div className="flex-1 space-y-2">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{club.name}</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              {!preseason && (
                <Badge variant={club.standing.position <= 5 ? "success" : "muted"}>
                  #{club.standing.position} · {club.standing.pts} pts
                </Badge>
              )}
              <Badge variant="outline">{oddsPct(club.odds.title)} title</Badge>
              <Badge variant="secondary">{club.squadSize} players</Badge>
              {!preseason && <FormPills form={club.standing.form} />}
            </div>
          </div>
          {club.wiki && (
            <Button asChild variant="outline" size="sm">
              <a
                href={`https://en.wikipedia.org/wiki/${encodeURIComponent(club.wiki)}`}
                target="_blank"
                rel="noreferrer noopener"
              >
                Wikipedia <ExternalLink className="ml-1.5 size-3.5" />
              </a>
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Stat cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={preseason ? "Projected finish" : "League position"}
          value={preseason ? `#${club.odds.expectedPosition.toFixed(0)}` : `#${club.standing.position}`}
          sub={preseason ? `${club.odds.expectedPoints.toFixed(0)} projected pts` : `${club.standing.pts} points`}
          icon={<Trophy />}
          accent="warning"
        />
        <StatCard
          label="Title chance"
          value={oddsPct(club.odds.title)}
          sub="Monte-Carlo (10k)"
          icon={<Trophy />}
          accent="primary"
        />
        <StatCard
          label="Champions League"
          value={oddsPct(club.odds.ucl)}
          sub={`Europa ${oddsPct(club.odds.europa)}`}
          icon={<ShieldCheck />}
          accent="info"
        />
        <StatCard
          label="Relegation risk"
          value={oddsPct(club.odds.relegation)}
          sub={`Elo ${club.strength.elo.toFixed(0)}`}
          icon={<TrendingDown />}
          accent={club.odds.relegation > 0.25 ? "warning" : "muted"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Strength radar */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Strength profile</CardTitle>
          </CardHeader>
          <CardContent>
            <StrengthRadar data={radar} color={club.primary} />
          </CardContent>
        </Card>

        {/* SWOT */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Strengths &amp; weaknesses</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-success">
                <ThumbsUp className="size-4" /> Strengths
              </p>
              <ul className="space-y-1.5 text-sm text-muted-foreground">
                {club.strengthsText.map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-success" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-destructive">
                <ThumbsDown className="size-4" /> Weaknesses
              </p>
              <ul className="space-y-1.5 text-sm text-muted-foreground">
                {club.weaknessesText.map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-destructive" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Key players */}
      {keyPlayers.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Star className="size-4 text-warning" /> Key players
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {keyPlayers.map((p) => (
              <Link key={p.id} href={`/players/${p.id}${query}`}>
                <Card className="card-hover flex flex-col items-center gap-2 p-4 text-center">
                  <PlayerAvatar name={p.name} src={p.headshot} size="lg" />
                  <div>
                    <p className="truncate text-sm font-semibold">{p.name}</p>
                    <p className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                      <Flag iso2={p.nationIso2} size="sm" /> {p.position}
                    </p>
                  </div>
                  <RatingPill rating={Math.round(p.rating)} />
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Matches */}
      {(played.length > 0 || upcoming.length > 0) && (
        <section className="space-y-6">
          {upcoming.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold tracking-tight">Upcoming fixtures</h2>
              <MatchList matches={upcoming} modelMeta={modelMeta} />
            </div>
          )}
          {played.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold tracking-tight">Recent results</h2>
              <MatchList matches={played} modelMeta={modelMeta} />
            </div>
          )}
        </section>
      )}

      {/* Squad */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Squad</h2>
        <SquadTable players={squad} query={query} keyPlayerIds={club.keyPlayers} />
      </section>
    </div>
  );
}
