import * as React from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClubBadge } from "@/components/club-badge";
import { FormPills } from "@/components/form-pills";
import { cn } from "@/lib/utils";
import type { Club, Standing } from "@/lib/types";

export interface Zones {
  /** Positions 1..ucl qualify for the Champions League. */
  ucl: number;
  /** Positions ucl+1..europa qualify for the Europa League. */
  europa: number;
  /** Bottom `releg` positions are relegated. */
  releg: number;
}

function zoneFor(pos: number, total: number, z: Zones): { cls: string; label: string } | null {
  if (pos <= z.ucl) return { cls: "before:bg-primary", label: "Champions League" };
  if (pos <= z.europa) return { cls: "before:bg-info", label: "Europa League" };
  if (pos > total - z.releg) return { cls: "before:bg-destructive", label: "Relegation" };
  return null;
}

/**
 * The league table. Rows are colour-coded by qualification zone (Champions
 * League / Europa / relegation) and link through to the club detail page.
 * `preseason` hides the played columns when no matches have kicked off.
 */
export function StandingsTable({
  standings,
  clubs,
  query,
  zones,
  preseason = false,
}: {
  standings: Standing[];
  clubs: Club[];
  query: string;
  zones: Zones;
  preseason?: boolean;
}) {
  const clubMap = new Map(clubs.map((c) => [c.code, c]));
  const total = standings.length;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-10 text-center">#</TableHead>
            <TableHead>Club</TableHead>
            <TableHead className="w-10 text-center">P</TableHead>
            <TableHead className="w-10 text-center">W</TableHead>
            <TableHead className="w-10 text-center">D</TableHead>
            <TableHead className="w-10 text-center">L</TableHead>
            <TableHead className="hidden w-12 text-center sm:table-cell">GF</TableHead>
            <TableHead className="hidden w-12 text-center sm:table-cell">GA</TableHead>
            <TableHead className="w-12 text-center">GD</TableHead>
            <TableHead className="w-12 text-center font-bold text-foreground">Pts</TableHead>
            <TableHead className="hidden text-center md:table-cell">Form</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {standings.map((s) => {
            const club = clubMap.get(s.code);
            const zone = zoneFor(s.position, total, zones);
            return (
              <TableRow key={s.code} className="group">
                <TableCell
                  className={cn(
                    "relative text-center font-semibold tabular-nums",
                    "before:absolute before:inset-y-1 before:left-0 before:w-1 before:rounded-full before:content-['']",
                    zone ? zone.cls : "before:bg-transparent",
                  )}
                >
                  {s.position}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/clubs/${s.code.toLowerCase()}${query}`}
                    className="flex items-center gap-2.5 font-medium hover:text-primary"
                  >
                    <ClubBadge
                      code={s.code}
                      primary={club?.primary ?? "#334155"}
                      secondary={club?.secondary ?? "#0f172a"}
                      size="sm"
                    />
                    <span className="truncate">{club?.short ?? s.code}</span>
                  </Link>
                </TableCell>
                <TableCell className="text-center tabular-nums text-muted-foreground">
                  {preseason ? "—" : s.played}
                </TableCell>
                <TableCell className="text-center tabular-nums">{preseason ? "—" : s.win}</TableCell>
                <TableCell className="text-center tabular-nums">{preseason ? "—" : s.draw}</TableCell>
                <TableCell className="text-center tabular-nums">{preseason ? "—" : s.loss}</TableCell>
                <TableCell className="hidden text-center tabular-nums sm:table-cell">
                  {preseason ? "—" : s.gf}
                </TableCell>
                <TableCell className="hidden text-center tabular-nums sm:table-cell">
                  {preseason ? "—" : s.ga}
                </TableCell>
                <TableCell className="text-center tabular-nums">
                  {preseason ? "—" : s.gd > 0 ? `+${s.gd}` : s.gd}
                </TableCell>
                <TableCell className="text-center text-base font-bold tabular-nums">
                  {preseason ? "—" : s.pts}
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <div className="flex justify-center">
                    <FormPills form={s.form} />
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/** Small legend explaining the zone colours. */
export function ZoneLegend({ zones }: { zones: Zones }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="inline-block size-2.5 rounded-full bg-primary" /> Champions League (top {zones.ucl})
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block size-2.5 rounded-full bg-info" /> Europa League
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block size-2.5 rounded-full bg-destructive" /> Relegation (bottom {zones.releg})
      </span>
    </div>
  );
}
