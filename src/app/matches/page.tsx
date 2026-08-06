import { PageHeader } from "@/components/page-header";
import { MatchesExplorer } from "@/components/match/matches-explorer";
import { buildModelMeta } from "@/lib/model-meta";
import { getSelection, getMatches, getModels, getClubs } from "@/lib/data";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "Matches" };

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [matches, models, clubs] = await Promise.all([
    getMatches(sel),
    getModels(sel),
    getClubs(sel),
  ]);
  const modelMeta = buildModelMeta(models.leaderboard);
  const clubList = [...clubs]
    .sort((a, b) => a.short.localeCompare(b.short))
    .map((c) => ({ code: c.code, short: c.short }));

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Fixtures & results"
        title="Matches"
        description="Every fixture with model win probabilities. Completed games show the final score and whether the ensemble's pick was correct. Click any probability bar for the full model breakdown and contributing factors."
      />
      <MatchesExplorer matches={matches} clubs={clubList} modelMeta={modelMeta} />
    </div>
  );
}
