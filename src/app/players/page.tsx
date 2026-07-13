import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { PlayersExplorer } from "@/components/players-explorer";

export const metadata: Metadata = {
  title: "Players",
  description:
    "Browse every 2026 World Cup squad member with real tournament stats — goals, appearances, minutes and cards. Search, filter and sort.",
};

export default function PlayersPage() {
  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Squads"
        title="Players"
        description="All 1,248 squad members across the 48 nations — real, current call-ups parsed from Wikipedia. Search by name or club, filter by country and position, and sort by any stat. Select a player for their full profile."
      />
      <PlayersExplorer />
      <p className="text-xs text-muted-foreground/70">
        Squad identities (name, position, age, caps, club) come from the maintained squad
        tables on Wikipedia. Headshots are freely-licensed portraits from Wikimedia Commons
        (public-domain / CC BY / CC BY-SA, attributed on each player&rsquo;s profile);
        players without a free photo show a clean initials avatar. Tournament statistics
        (goals, appearances, minutes, cards, clean sheets) are the real totals from the
        official FIFA match reports via Wikipedia; assists and advanced metrics are not in
        any free source and are omitted. Only the 0&ndash;100 ability rating is
        model-generated.
      </p>
    </div>
  );
}
