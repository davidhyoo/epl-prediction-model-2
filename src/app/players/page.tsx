import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { PlayersExplorer } from "@/components/players-explorer";

export const metadata: Metadata = {
  title: "Players",
  description:
    "Browse every 2026 World Cup squad member with ratings, goals, assists and expected-goals stats. Search, filter and sort.",
};

export default function PlayersPage() {
  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Squads"
        title="Players"
        description="All 1,248 squad members across the 48 nations. Search by name or club, filter by country and position, and sort by any stat. Select a player for their full profile."
      />
      <PlayersExplorer />
    </div>
  );
}
