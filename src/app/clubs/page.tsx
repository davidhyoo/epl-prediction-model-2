import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { ClubsExplorer } from "@/components/clubs-explorer";
import { getSelection, getClubs, getSummary } from "@/lib/data";
import { queryFor } from "@/lib/league";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "Clubs" };

export default async function ClubsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [clubs, summary] = await Promise.all([getClubs(sel), getSummary(sel)]);
  const query = queryFor(sel);
  const preseason = summary.played === 0;

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow={`${summary.league.name} · ${summary.season.label}`}
        title="Clubs"
        description="Every club in the division with its live position, projected finish and squad strength. Open a club for its full profile, squad, key players and season odds."
        actions={<Badge variant="muted">{clubs.length} clubs</Badge>}
      />
      <ClubsExplorer clubs={clubs} query={query} preseason={preseason} />
    </div>
  );
}
