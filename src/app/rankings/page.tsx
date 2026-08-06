import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { RankingsExplorer } from "@/components/rankings-explorer";
import { getSelection, getRankings, getClubs, getSummary } from "@/lib/data";
import { queryFor } from "@/lib/league";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "Rankings" };

export default async function RankingsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [rankings, clubs, summary] = await Promise.all([
    getRankings(sel),
    getClubs(sel),
    getSummary(sel),
  ]);
  const query = queryFor(sel);

  const rankingClubs = clubs.map((c) => ({
    code: c.code,
    short: c.short,
    primary: c.primary,
    secondary: c.secondary,
  }));

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow={`${summary.league.name} · ${summary.season.label}`}
        title="Rankings"
        description="Eight ways to rank the division — title probability, overall strength, recent form, attack, defence, squad quality, Elo rating and momentum. Switch views to see how the picture changes."
        actions={<Badge variant="muted">8 ranking views</Badge>}
      />
      <RankingsExplorer rankings={rankings} clubs={rankingClubs} query={query} />
    </div>
  );
}
