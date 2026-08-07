import { PageHeader } from "@/components/page-header";
import { StandingsTable, ZoneLegend } from "@/components/standings-table";
import { Badge } from "@/components/ui/badge";
import { getSelection, getStandings, getClubs, getSummary } from "@/lib/data";
import { queryFor, zoneConfigFor } from "@/lib/league";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "League Table" };

export default async function TablePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [standings, clubs, summary] = await Promise.all([
    getStandings(sel),
    getClubs(sel),
    getSummary(sel),
  ]);
  const query = queryFor(sel);
  const zones = zoneConfigFor(sel.league, summary.league.format);
  const preseason = summary.played === 0;

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow={`${summary.league.name} · ${summary.season.label}`}
        title="League table"
        description={
          preseason
            ? "The season hasn't kicked off yet — standings show the fixtures loaded and projected finishing positions live under Predictions."
            : "Live standings after every completed match, with the last five results per club and European / relegation zones highlighted."
        }
        actions={
          preseason ? (
            <Badge variant="info">Pre-season — awaiting kickoff</Badge>
          ) : (
            <Badge variant="muted">{summary.played} matches played</Badge>
          )
        }
      />
      <StandingsTable
        standings={standings}
        clubs={clubs}
        query={query}
        zones={zones}
        preseason={preseason}
      />
      <ZoneLegend zones={zones} />
    </div>
  );
}
