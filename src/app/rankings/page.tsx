import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { RankingsExplorer } from "@/components/rankings-explorer";
import { getRankings } from "@/lib/data";

export const metadata: Metadata = {
  title: "Rankings",
  description:
    "Multi-dimensional 2026 World Cup team rankings: championship odds, strength, form, attack, defense, squad and model confidence.",
};

export default async function RankingsPage() {
  const rankings = await getRankings();
  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Leaderboards"
        title="Rankings"
        description="Compare all 48 nations across nine dimensions — from simulated title odds to attack, defense, squad strength and model confidence. Switch views and filter by confederation."
      />
      <RankingsExplorer rankings={rankings} />
    </div>
  );
}
