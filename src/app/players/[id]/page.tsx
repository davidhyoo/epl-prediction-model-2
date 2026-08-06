import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { ArrowLeft, ExternalLink, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PlayerAvatar } from "@/components/player-avatar";
import { Flag } from "@/components/flag";
import { ClubBadge } from "@/components/club-badge";
import { RatingPill } from "@/components/rating-pill";
import { StatCard } from "@/components/stat-card";
import { getSelection, getPlayerById, getClubByCode } from "@/lib/data";
import { queryFor } from "@/lib/league";
import { POSITION_LABEL } from "@/lib/format";
import type { SearchParams } from "@/lib/league";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return { title: id };
}

export default async function PlayerProfile({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const player = await getPlayerById(sel, id);
  if (!player) notFound();

  const club = await getClubByCode(sel, player.club);
  const query = queryFor(sel);

  const hasStat = (v: number | null | undefined): v is number => typeof v === "number";

  const stats = [
    { label: "Goals", value: String(player.goals), sub: player.penalties ? `${player.penalties} pen` : undefined },
    hasStat(player.assists) ? { label: "Assists", value: String(player.assists) } : null,
    hasStat(player.appearances) ? { label: "Appearances", value: String(player.appearances) } : null,
    hasStat(player.minutes) ? { label: "Minutes", value: player.minutes.toLocaleString() } : null,
    hasStat(player.yellowCards) ? { label: "Yellow cards", value: String(player.yellowCards) } : null,
    hasStat(player.redCards) ? { label: "Red cards", value: String(player.redCards) } : null,
  ].filter(Boolean) as { label: string; value: string; sub?: string }[];

  return (
    <div className="container-page space-y-6 py-8">
      <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit">
        <Link href={`/players${query}`}>
          <ArrowLeft className="mr-1.5 size-4" /> All players
        </Link>
      </Button>

      <Card className="glass overflow-hidden">
        <div className="app-aura h-24 w-full" />
        <CardContent className="-mt-12 flex flex-col gap-4 sm:flex-row sm:items-end">
          <PlayerAvatar name={player.name} src={player.headshot} size="xl" className="ring-4" />
          <div className="flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{player.name}</h1>
              {player.shirtNumber != null && (
                <Badge variant="muted" className="tabular-nums">
                  #{player.shirtNumber}
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Flag iso2={player.nationIso2} size="sm" /> {player.nationName}
              </span>
              <span className="text-border">·</span>
              {club ? (
                <Link
                  href={`/clubs/${club.code.toLowerCase()}${query}`}
                  className="flex items-center gap-1.5 hover:text-foreground"
                >
                  <ClubBadge code={club.code} primary={club.primary} secondary={club.secondary} size="sm" />
                  {club.name}
                </Link>
              ) : (
                <span>{player.clubName}</span>
              )}
              <span className="text-border">·</span>
              <Badge variant="secondary">{player.detailedPosition || POSITION_LABEL[player.position]}</Badge>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Rating</p>
            <RatingPill rating={Math.round(player.rating)} className="mt-1 text-base" />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} sub={s.sub} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="size-4 text-primary" /> Goal timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            {player.goalMinutes.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {player.goalMinutes.map((m, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary tabular-nums"
                  >
                    {m}&rsquo;
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No goals recorded yet this season.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Nation" value={player.nationName} />
            <Row label="Club" value={player.clubName} />
            <Row label="Position" value={player.detailedPosition || POSITION_LABEL[player.position]} />
            {player.shirtNumber != null && <Row label="Shirt" value={`#${player.shirtNumber}`} />}
            {player.wiki && (
              <Button asChild variant="outline" size="sm" className="mt-1 w-full">
                <a
                  href={`https://en.wikipedia.org/wiki/${encodeURIComponent(player.wiki)}`}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  Wikipedia <ExternalLink className="ml-1.5 size-3.5" />
                </a>
              </Button>
            )}
            {player.photoCredit && (
              <p className="border-t border-border pt-3 text-[11px] leading-relaxed text-muted-foreground">
                Photo:{" "}
                <a
                  href={player.photoCredit.sourceUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline hover:text-foreground"
                >
                  {player.photoCredit.author}
                </a>{" "}
                · {player.photoCredit.license}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
