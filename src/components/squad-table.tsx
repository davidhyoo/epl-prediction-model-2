import Link from "next/link";
import { Star } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PlayerAvatar } from "@/components/player-avatar";
import { RatingPill } from "@/components/rating-pill";
import { Flag } from "@/components/flag";
import type { Player, Position } from "@/lib/types";

const POSITION_ORDER: Position[] = ["GK", "DEF", "MID", "FWD"];
const POSITION_LABEL: Record<Position, string> = {
  GK: "Goalkeepers",
  DEF: "Defenders",
  MID: "Midfielders",
  FWD: "Forwards",
};

export function SquadTable({
  players,
  query,
  keyPlayerIds = [],
}: {
  players: Player[];
  query: string;
  keyPlayerIds?: string[];
}) {
  const keySet = new Set(keyPlayerIds);
  const byPos = POSITION_ORDER.map((pos) => ({
    pos,
    players: players
      .filter((p) => p.position === pos)
      .sort((a, b) => (a.shirtNumber ?? 99) - (b.shirtNumber ?? 99) || b.rating - a.rating),
  })).filter((g) => g.players.length > 0);

  return (
    <div className="space-y-6">
      {byPos.map((group) => (
        <div key={group.pos}>
          <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
            {POSITION_LABEL[group.pos]} <span className="font-normal">({group.players.length})</span>
          </h3>
          <div className="overflow-hidden rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10 text-center">#</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead className="hidden sm:table-cell">Nation</TableHead>
                  <TableHead className="w-12 text-right">G</TableHead>
                  <TableHead className="w-16 text-right">Rating</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.players.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-center text-xs text-muted-foreground tabular-nums">
                      {p.shirtNumber ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/players/${p.id}${query}`}
                        className="flex items-center gap-2.5 font-medium hover:text-primary"
                      >
                        <PlayerAvatar name={p.name} src={p.headshot} size="sm" />
                        <span className="flex items-center gap-1.5">
                          {p.name}
                          {keySet.has(p.id) && <Star className="size-3 fill-warning text-warning" />}
                        </span>
                      </Link>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <span className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Flag iso2={p.nationIso2} size="sm" />
                        <span className="hidden truncate lg:inline">{p.nationName}</span>
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium tabular-nums">
                      {p.goals}
                    </TableCell>
                    <TableCell className="text-right">
                      <RatingPill rating={Math.round(p.rating)} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ))}
    </div>
  );
}
