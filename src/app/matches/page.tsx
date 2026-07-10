import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { MatchesExplorer } from "@/components/match/matches-explorer";
import { getMatches, getModels, getTeams } from "@/lib/data";
import { buildModelMeta } from "@/lib/model-meta";

export const metadata: Metadata = {
  title: "Matches",
  description:
    "All 2026 World Cup fixtures and results with model win probabilities, filtering and sorting.",
};

type StatusFilter = "all" | "upcoming" | "completed" | "live";

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const [matches, models, teams] = await Promise.all([getMatches(), getModels(), getTeams()]);
  const modelMeta = buildModelMeta(models);

  const validStatus: StatusFilter =
    status === "upcoming" || status === "completed" || status === "live" ? status : "all";

  const teamRefs = teams
    .map((t) => ({ code: t.code, name: t.name, iso2: t.iso2 }))
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Fixtures & results"
        title="Matches"
        description="Every match across the group stage and knockout rounds, with ensemble win probabilities. Click any probability bar to see the full model breakdown and contributing factors."
      />
      <MatchesExplorer
        matches={matches}
        teams={teamRefs}
        modelMeta={modelMeta}
        initialStatus={validStatus}
      />
    </div>
  );
}
