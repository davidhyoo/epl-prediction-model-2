import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Trophy,
  Shield,
  Swords,
  Flame,
  Star,
  TrendingUp,
  CircleDot,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Flag } from "@/components/flag";
import { StatCard } from "@/components/stat-card";
import { MatchCard } from "@/components/match/match-card";
import { SquadTable } from "@/components/squad-table";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { StrengthRadar } from "@/components/charts/strength-radar";
import { TrendArea } from "@/components/charts/trend-area";
import {
  getTeams,
  getTeamByCode,
  getPlayersByCountry,
  getMatchesForTeam,
  getModels,
} from "@/lib/data";
import { buildModelMeta } from "@/lib/model-meta";
import { pct } from "@/lib/format";

export async function generateStaticParams() {
  const teams = await getTeams();
  return teams.map((t) => ({ code: t.code.toLowerCase() }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ code: string }>;
}): Promise<Metadata> {
  const { code } = await params;
  const team = await getTeamByCode(code);
  if (!team) return { title: "Country not found" };
  return {
    title: team.name,
    description: `${team.name} — squad, fixtures, strengths and championship probability at the 2026 World Cup.`,
  };
}

const ADVANCE_STEPS: { key: keyof import("@/lib/types").AdvanceProbabilities; label: string }[] = [
  { key: "roundOf32", label: "Round of 32" },
  { key: "roundOf16", label: "Round of 16" },
  { key: "quarter", label: "Quarter-final" },
  { key: "semi", label: "Semi-final" },
  { key: "final", label: "Final" },
  { key: "champion", label: "Champion" },
];

export default async function CountryDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const team = await getTeamByCode(code);
  if (!team) notFound();

  const [players, matches, models] = await Promise.all([
    getPlayersByCountry(team.code),
    getMatchesForTeam(team.code),
    getModels(),
  ]);
  const modelMeta = buildModelMeta(models);

  const played = matches.filter((m) => m.status === "completed");
  const upcoming = matches.filter((m) => m.status !== "completed");
  const keyPlayers = players.filter((p) => team.keyPlayerIds.includes(p.id)).slice(0, 5);

  const radarData = [
    { metric: "Attack", value: team.strength.attack },
    { metric: "Defense", value: team.strength.defense },
    { metric: "Form", value: team.strength.form },
    { metric: "Squad", value: team.strength.squad },
    { metric: "Momentum", value: team.strength.momentum },
    { metric: "Experience", value: team.strength.experience },
  ];
  const historyData = team.championProbHistory.map((h) => ({ label: h.label, value: h.prob }));

  return (
    <div className="container-page space-y-8 py-8">
      <Link
        href="/countries"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> All countries
      </Link>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Flag iso2={team.iso2} size="xl" className="shadow-md" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{team.name}</h1>
              {team.status === "eliminated" ? (
                <Badge variant="destructive">Eliminated</Badge>
              ) : (
                <Badge variant="success">Active</Badge>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">Group {team.group}</Badge>
              <span>{team.confederation}</span>
              <span>·</span>
              <span>Elo {Math.round(team.elo)}</span>
              <span>·</span>
              <span>FIFA-style rank #{team.fifaRank}</span>
            </div>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Title probability"
          value={team.status === "eliminated" ? "0%" : pct(team.championProb)}
          sub="Monte-Carlo simulation"
          icon={<Trophy />}
          accent="warning"
        />
        <StatCard
          label="Overall strength"
          value={Math.round(team.strength.overall)}
          sub="composite 0–100"
          icon={<TrendingUp />}
          accent="primary"
        />
        <StatCard
          label="Attack / Defense"
          value={`${Math.round(team.strength.attack)} / ${Math.round(team.strength.defense)}`}
          sub="rating out of 100"
          icon={<Swords />}
          accent="info"
        />
        <StatCard
          label="Group record"
          value={`${team.record.won}-${team.record.drawn}-${team.record.lost}`}
          sub={`${team.record.points} pts · GD ${team.record.gd >= 0 ? "+" : ""}${team.record.gd}`}
          icon={<Shield />}
          accent="success"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column */}
        <div className="space-y-6 lg:col-span-2">
          {/* Advancement path */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Advancement path</CardTitle>
              <p className="text-sm text-muted-foreground">
                Simulated probability of reaching each stage.
              </p>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {ADVANCE_STEPS.map((s) => {
                const v = team.advance[s.key];
                return (
                  <div key={s.key} className="flex items-center gap-3">
                    <span className="w-28 shrink-0 text-sm text-muted-foreground">{s.label}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.max(v * 100, 1)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-sm font-semibold tabular-nums">
                      {pct(v)}
                    </span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Fixtures */}
          {upcoming.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Upcoming & projected fixtures</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {upcoming.map((m) => (
                  <MatchCard key={m.id} match={m} modelMeta={modelMeta} />
                ))}
              </div>
            </section>
          )}

          {played.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Results</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {played.map((m) => (
                  <MatchCard key={m.id} match={m} modelMeta={modelMeta} />
                ))}
              </div>
            </section>
          )}

          {/* Squad */}
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Squad ({players.length})</h2>
            <SquadTable players={players} />
          </section>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">Strength profile</CardTitle>
            </CardHeader>
            <CardContent>
              <StrengthRadar data={radarData} />
            </CardContent>
          </Card>

          {historyData.length > 1 && (
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm">Title probability trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendArea data={historyData} percent valueName="Title odds" height={180} />
              </CardContent>
            </Card>
          )}

          {/* Strengths & weaknesses */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Strengths & weaknesses</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 font-medium text-success">
                  <Flame className="size-4" /> Strengths
                </p>
                <ul className="space-y-1">
                  {team.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-muted-foreground">
                      <CircleDot className="mt-0.5 size-3 shrink-0 text-success" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 font-medium text-warning">
                  <Shield className="size-4" /> Weaknesses
                </p>
                <ul className="space-y-1">
                  {team.weaknesses.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-muted-foreground">
                      <CircleDot className="mt-0.5 size-3 shrink-0 text-warning" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Key players */}
          {keyPlayers.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-1.5 text-sm">
                  <Star className="size-4 text-warning" /> Key players
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {keyPlayers.map((p) => (
                  <Link
                    key={p.id}
                    href={`/players/${p.id}`}
                    className="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted/50"
                  >
                    <PlayerAvatar name={p.name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.detailedPosition}</p>
                    </div>
                    <RatingPill rating={p.rating} />
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
