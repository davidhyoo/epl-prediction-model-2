import { PageHeader } from "@/components/page-header";
import { MatchesExplorer } from "@/components/match/matches-explorer";
import { DrawPendingBanner } from "@/components/draw-pending-banner";
import { buildModelMeta } from "@/lib/model-meta";
import { getSelection, getModels, getClubs, getSummary } from "@/lib/data";
import { isDrawPending, type SearchParams } from "@/lib/league";

export const metadata = { title: "Matches" };

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  // The heavy fixture list (~730 KB) is fetched client-side by MatchesExplorer,
  // so the server only prepares the small clubs + model-meta payloads.
  const [models, clubs, summary] = await Promise.all([
    getModels(sel),
    getClubs(sel),
    getSummary(sel),
  ]);
  const modelMeta = buildModelMeta(models.leaderboard);
  const drawPending = isDrawPending(summary.league.format, summary.totalMatches);
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
      {drawPending && <DrawPendingBanner />}
      <MatchesExplorer selection={sel} clubs={clubList} modelMeta={modelMeta} />
    </div>
  );
}
