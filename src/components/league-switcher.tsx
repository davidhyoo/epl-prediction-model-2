"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Flag } from "@/components/flag";
import { LEAGUE_PARAM, SEASON_PARAM } from "@/lib/league";
import type { IndexData } from "@/lib/types";

/**
 * League + season switcher. Selection lives in the URL (`?league=&season=`)
 * so every server component re-reads the right dataset. Changing the league
 * resets the season to that league's first season when the current one is
 * unavailable.
 */
export function LeagueSwitcher({
  index,
  league,
  season,
}: {
  index: IndexData;
  league: string;
  season: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const currentLeague = index.leagues.find((l) => l.id === league) ?? index.leagues[0];

  const navigate = React.useCallback(
    (nextLeague: string, nextSeason: string) => {
      const usp = new URLSearchParams(searchParams.toString());
      usp.set(LEAGUE_PARAM, nextLeague);
      usp.set(SEASON_PARAM, nextSeason);
      // Detail pages ([code]/[id]) are dataset-specific; jump back to the
      // section root so the entity always exists in the new dataset.
      const base = sectionRoot(pathname);
      router.push(`${base}?${usp.toString()}`);
    },
    [router, pathname, searchParams],
  );

  const onLeagueChange = (nextLeague: string) => {
    const lref = index.leagues.find((l) => l.id === nextLeague);
    const nextSeason =
      lref?.seasons.find((s) => s.id === season)?.id ?? lref?.seasons[0]?.id ?? season;
    navigate(nextLeague, nextSeason);
  };

  return (
    <div className="flex items-center gap-1.5">
      <Select value={league} onValueChange={onLeagueChange}>
        <SelectTrigger className="h-8 w-[9.5rem] gap-1.5 text-xs font-medium" aria-label="League">
          <span className="flex items-center gap-1.5 truncate">
            <Flag iso2={currentLeague.iso2} size="sm" />
            <SelectValue />
          </span>
        </SelectTrigger>
        <SelectContent>
          {index.leagues.map((l) => (
            <SelectItem key={l.id} value={l.id}>
              {l.short}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={season} onValueChange={(s) => navigate(league, s)}>
        <SelectTrigger className="h-8 w-[6.5rem] text-xs font-medium tabular-nums" aria-label="Season">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {currentLeague.seasons.map((s) => (
            <SelectItem key={s.id} value={s.id}>
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** Reduce a path like /players/ARS-07 → /players so switching stays valid. */
function sectionRoot(pathname: string): string {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return "/";
  return `/${parts[0]}`;
}
