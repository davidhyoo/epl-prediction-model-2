import Link from "next/link";
import { Trophy, ShieldCheck, TrendingDown, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClubBadge } from "@/components/club-badge";
import { SeasonOdds, type OddsClub } from "@/components/season-odds";
import { getSelection, getClubs, getSummary } from "@/lib/data";
import { queryFor } from "@/lib/league";
import { oddsPct } from "@/lib/format";
import type { SearchParams } from "@/lib/league";
import type { Club } from "@/lib/types";

export const metadata = { title: "Predictions" };

export default async function PredictionsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [clubs, summary] = await Promise.all([getClubs(sel), getSummary(sel)]);
  const query = queryFor(sel);

  const oddsClubs: OddsClub[] = clubs.map((c) => ({
    code: c.code,
    short: c.short,
    primary: c.primary,
    secondary: c.secondary,
    position: c.standing.position,
    title: c.odds.title,
    ucl: c.odds.ucl,
    europa: c.odds.europa,
    relegation: c.odds.relegation,
    expectedPoints: c.odds.expectedPoints,
    expectedPosition: c.odds.expectedPosition,
  }));

  const favourite = [...clubs].sort((a, b) => b.odds.title - a.odds.title)[0];
  const releg = [...clubs].sort((a, b) => b.odds.relegation - a.odds.relegation).slice(0, 3);
  const topFour = [...clubs].sort((a, b) => b.odds.ucl - a.odds.ucl).slice(0, 5);

  return (
    <div className="container-page space-y-8 py-8">
      <PageHeader
        eyebrow="Season simulation"
        title="Predictions"
        description="Each remaining fixture is simulated 10,000 times using the ensemble's win/draw/loss probabilities to estimate every club's chance of winning the title, qualifying for Europe, or being relegated."
        actions={
          <Badge variant="outline" className="gap-1.5">
            <Sparkles className="size-3" /> Monte-Carlo · 10k seasons
          </Badge>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <HighlightCard
          icon={<Trophy className="size-4 text-warning" />}
          title="Title favourite"
          club={favourite}
          value={`${oddsPct(favourite.odds.title)} to win`}
          query={query}
        />
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="size-4 text-primary" /> Champions League race
          </div>
          <div className="space-y-2">
            {topFour.map((c) => (
              <OddsRow key={c.code} club={c} value={c.odds.ucl} query={query} />
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <TrendingDown className="size-4 text-destructive" /> Relegation battle
          </div>
          <div className="space-y-2">
            {releg.map((c) => (
              <OddsRow key={c.code} club={c} value={c.odds.relegation} query={query} />
            ))}
          </div>
        </Card>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Full-season projection</h2>
        <Card className="p-4 sm:p-5">
          <SeasonOdds clubs={oddsClubs} query={query} />
        </Card>
        <p className="text-xs text-muted-foreground">
          {summary.played === 0
            ? "Pre-season: every club starts from zero points, so these are pure prior-strength projections that will sharpen as real results arrive."
            : "Odds combine points already banked with simulated outcomes for the remaining fixtures. A club already crowned or relegated shows 100% / 0%."}
        </p>
      </section>
    </div>
  );
}

function HighlightCard({
  icon,
  title,
  club,
  value,
  query,
}: {
  icon: React.ReactNode;
  title: string;
  club: Club;
  value: string;
  query: string;
}) {
  return (
    <Card className="card-hover p-5">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">{icon} {title}</div>
      <Link href={`/clubs/${club.code.toLowerCase()}${query}`} className="flex items-center gap-3">
        <ClubBadge code={club.code} primary={club.primary} secondary={club.secondary} size="lg" />
        <div>
          <p className="font-semibold">{club.name}</p>
          <p className="text-sm text-muted-foreground">{value}</p>
        </div>
      </Link>
    </Card>
  );
}

function OddsRow({ club, value, query }: { club: Club; value: number; query: string }) {
  return (
    <Link
      href={`/clubs/${club.code.toLowerCase()}${query}`}
      className="flex items-center gap-2.5 hover:text-primary"
    >
      <ClubBadge code={club.code} primary={club.primary} secondary={club.secondary} size="xs" />
      <span className="min-w-0 flex-1 truncate text-sm">{club.short}</span>
      <span className="text-sm font-semibold tabular-nums">
        {oddsPct(value)}
      </span>
    </Link>
  );
}
