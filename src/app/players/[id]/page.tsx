import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Star, Shirt } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Flag } from "@/components/flag";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { getPlayerById, getTeamByCode, getTeams } from "@/lib/data";

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
    description: `${player.name} — ${player.detailedPosition} for ${player.country}. World Cup stats, match log and profile.`,
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
  const teams = await getTeams();
  const codeToTeam = new Map(teams.map((t) => [t.code, t]));

  const isGK = player.position === "GK";
  const matchLog = player.matchLog ?? [];

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
            <PlayerAvatar name={player.name} src={player.headshot} size="xl" />
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
                {player.age != null && (
                  <>
                    <span>·</span>
                    <span>Age {player.age}</span>
                  </>
                )}
                <span>·</span>
                <span>{player.club}</span>
                {player.caps != null && (
                  <>
                    <span>·</span>
                    <span>
                      {player.caps} cap{player.caps === 1 ? "" : "s"}
                      {player.intlGoals ? `, ${player.intlGoals} goal${player.intlGoals === 1 ? "" : "s"}` : ""}
                    </span>
                  </>
                )}
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
          {player.photoCredit && (
            <p className="mt-3 text-xs text-muted-foreground/70">
              Photo:{" "}
              <a
                href={player.photoCredit.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="underline hover:text-foreground"
              >
                {player.photoCredit.author}
              </a>{" "}
              · {player.photoCredit.license} · via Wikimedia Commons
            </p>
          )}
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
                    ["Clean sheets", player.stats.cleanSheets ?? 0],
                    ["Goals conceded", player.stats.goalsConceded ?? 0],
                  ]}
                />
              ) : (
                <StatGroup
                  title="Attacking"
                  stats={[
                    ["Goals", player.stats.goals],
                    ["Assists", player.stats.assists ?? "—"],
                  ]}
                />
              )}
              <p className="text-xs text-muted-foreground">
                Real tournament totals taken from the official FIFA match reports
                (via Wikipedia). Assists, expected goals (xG/xA), shots, passing and
                tackling are not published in any free World Cup data source, so they
                are shown as &ldquo;&mdash;&rdquo; rather than estimated.
              </p>
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

          {matchLog.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">World Cup match log</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {matchLog.map((m, i) => {
                  const opp = codeToTeam.get(m.opponent);
                  const res =
                    m.goalsFor > m.goalsAgainst
                      ? "W"
                      : m.goalsFor < m.goalsAgainst
                        ? "L"
                        : "D";
                  const resClass =
                    res === "W"
                      ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                      : res === "L"
                        ? "bg-red-500/15 text-red-600 dark:text-red-400"
                        : "bg-amber-500/15 text-amber-600 dark:text-amber-400";
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-sm"
                    >
                      <span
                        className={`flex size-5 shrink-0 items-center justify-center rounded text-[11px] font-bold ${resClass}`}
                        title={m.started ? "Started" : "Substitute"}
                      >
                        {res}
                      </span>
                      {opp ? <Flag iso2={opp.iso2} size="sm" /> : <span className="w-[18px]" />}
                      <span className="flex-1 truncate text-muted-foreground">
                        {opp?.name ?? m.opponent}
                      </span>
                      <span className="tabular-nums">
                        {m.goalsFor}&ndash;{m.goalsAgainst}
                      </span>
                      <span className="w-9 text-right text-xs text-muted-foreground tabular-nums">
                        {m.minutes}&rsquo;
                      </span>
                      <span className="flex w-10 items-center justify-end gap-1 text-xs">
                        {m.goals > 0 && (
                          <span className="font-semibold text-foreground">
                            {m.goals}&nbsp;G
                          </span>
                        )}
                        {m.yellow > 0 && (
                          <span className="h-3 w-2 rounded-[1px] bg-amber-400" title="Yellow card" />
                        )}
                        {m.red > 0 && (
                          <span className="h-3 w-2 rounded-[1px] bg-red-500" title="Red card" />
                        )}
                      </span>
                    </div>
                  );
                })}
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
