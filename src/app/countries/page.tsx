import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { CountriesExplorer } from "@/components/countries-explorer";
import { getTeams } from "@/lib/data";

export const metadata: Metadata = {
  title: "Countries",
  description:
    "All 48 nations at the 2026 World Cup with championship probabilities, Elo ratings and group standings.",
};

export default async function CountriesPage() {
  const teams = await getTeams();
  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Nations"
        title="Countries"
        description="All 48 qualified nations, ranked by their simulated championship probability. Eliminated teams drop to 0%. Select a country for its squad, fixtures and analysis."
      />
      <CountriesExplorer teams={teams} />
    </div>
  );
}
