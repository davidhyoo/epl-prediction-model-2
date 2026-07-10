import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Star, Shirt } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Flag } from "@/components/flag";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { TrendArea } from "@/components/charts/trend-area";
import { getPlayerById, getTeamByCode } from "@/lib/data";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const player = await getPlayerById(id);
  if (!player) return { title: "Player not found" };
  return {
    title: player.name,
    description: `${player.name} — ${player.detailedPosition} for ${player.country}. Stats, form and profile.`,
  };
}

export default async function PlayerProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const player = await getPlayerById(id);
  if (!player) notFound();
  const team = await getTeamByCode(player.countryCode);

  const isGK = player.position === "GK";
  const formData = player.form.map((f) => ({ label: f.label, value: f.rating }));

  return (
    <div className="container-page space-y-8 py-8">
      <Link
        href="/players"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> All players
      </Link>

      {/* Header */}
      <Card className="overflow-hidden">
        <div className="border-b border-border bg-muted/30 p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <PlayerAvatar name={player.name} size="xl" />
            <div className="flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{player.name}</h1>
                {player.isCaptain && <Badge variant="info">Captain</Badge>}
                {player.isKeyPlayer && (
                  <Badge variant="warning" className="gap-1">
                    <Star className="size-3" /> Key player
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                <Link
                  href={`/countries/${player.countryCode.toLowerCase()}`}
                  className="flex items-center gap-1.5 hover:text-foreground"
                >
                  <Flag iso2={player.iso2} size="sm" /> {player.country}
                </Link>
                <span>·</span>
                <span>{player.detailedPosition}</span>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <Shirt className="size-3.5" /> {player.shirtNumber}
                </span>
                <span>·</span>
                <span>Age {player.age}</span>
                <span>·</span>
                <span>{player.club}</span>
              </div>
            </div>
            <div className="flex gap-6 sm:flex-col sm:items-end sm:gap-1">
              <div className="text-center sm:text-right">
                <div className="text-3xl font-bold tabular-nums">{player.rating}</div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Rating</div>
              </div>
            </div>
          </div>
        </div>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">{player.bio}</p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Stats */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Tournament statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <StatGroup
                title="Overview"
                stats={[
                  ["Appearances", player.stats.appearances],
                  ["Minutes", player.stats.minutes.toLocaleString()],
                  ["Yellow cards", player.stats.yellowCards],
                  ["Red cards", player.stats.redCards],
                ]}
              />
              {isGK ? (
                <StatGroup
                  title="Goalkeeping"
                  stats={[
                    ["Saves", player.stats.saves ?? 0],
                    ["Clean sheets", player.stats.cleanSheets ?? 0],
                    ["Goals conceded", player.stats.goalsConceded ?? 0],
                    ["Pass accuracy", `${player.stats.passAccuracy}%`],
                  ]}
                />
              ) : (
                <>
                  <StatGroup
                    title="Attacking"
                    stats={[
                      ["Goals", player.stats.goals],
                      ["Assists", player.stats.assists],
                      ["Expected goals (xG)", player.stats.xg.toFixed(1)],
                      ["Expected assists (xA)", player.stats.xa.toFixed(1)],
                      ["Shots", player.stats.shots],
                      ["Shots on target", player.stats.shotsOnTarget],
                    ]}
                  />
                  <StatGroup
                    title="Passing & possession"
                    stats={[
                      ["Passes", player.stats.passes.toLocaleString()],
                      ["Pass accuracy", `${player.stats.passAccuracy}%`],
                      ["Key passes", player.stats.keyPasses],
                    ]}
                  />
                  <StatGroup
                    title="Defending"
                    stats={[
                      ["Tackles", player.stats.tackles],
                      ["Interceptions", player.stats.interceptions],
                      ["Duels won", player.stats.duelsWon],
                    ]}
                  />
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Side */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Team contribution score</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-bold tabular-nums">
                  {Math.round(player.contribution)}
                </span>
                <span className="text-xs text-muted-foreground">out of 100</span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${Math.min(player.contribution, 100)}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                A blend of individual rating, output and minutes that estimates how much this
                player lifts {player.country}&rsquo;s squad-strength feature — one input to the
                match models.
              </p>
            </CardContent>
          </Card>

          {formData.length > 1 && (
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm">Recent match form</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendArea
                  data={formData}
                  height={180}
                  yDomain={[4, 10]}
                  valueName="Match rating"
                />
              </CardContent>
            </Card>
          )}

          {team && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Nation</CardTitle>
              </CardHeader>
              <CardContent>
                <Link
                  href={`/countries/${team.code.toLowerCase()}`}
                  className="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted/50"
                >
                  <Flag iso2={team.iso2} size="lg" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{team.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Group {team.group} · {team.confederation}
                    </p>
                  </div>
                  <RatingPill rating={Math.round(team.strength.overall)} />
                </Link>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function StatGroup({
  title,
  stats,
}: {
  title: string;
  stats: [string, React.ReactNode][];
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {stats.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-border bg-card p-3">
            <div className="text-lg font-semibold tabular-nums">{value}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
