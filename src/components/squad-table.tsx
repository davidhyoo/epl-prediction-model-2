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
import type { Player, Position } from "@/lib/types";

const POSITION_ORDER: Position[] = ["GK", "DEF", "MID", "FWD"];
const POSITION_LABEL: Record<Position, string> = {
  GK: "Goalkeepers",
  DEF: "Defenders",
  MID: "Midfielders",
  FWD: "Forwards",
};

export function SquadTable({ players }: { players: Player[] }) {
  const byPos = POSITION_ORDER.map((pos) => ({
    pos,
    players: players
      .filter((p) => p.position === pos)
      .sort((a, b) => b.rating - a.rating),
  })).filter((g) => g.players.length > 0);

  return (
    <div className="space-y-6">
      {byPos.map((group) => (
        <div key={group.pos}>
          <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
            {POSITION_LABEL[group.pos]}{" "}
            <span className="font-normal">({group.players.length})</span>
          </h3>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10">#</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead className="hidden md:table-cell">Club</TableHead>
                  <TableHead className="w-12 text-right">Age</TableHead>
                  <TableHead className="w-14 text-right">Apps</TableHead>
                  <TableHead className="w-12 text-right">G</TableHead>
                  <TableHead className="w-16 text-right">Min</TableHead>
                  <TableHead className="w-16 text-right">Rating</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.players.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">
                      {p.shirtNumber}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/players/${p.id}`}
                        className="flex items-center gap-2.5 font-medium hover:underline"
                      >
                        <PlayerAvatar name={p.name} src={p.headshot} size="sm" />
                        <span className="flex items-center gap-1.5">
                          {p.name}
                          {p.isCaptain && (
                            <span className="rounded bg-muted px-1 text-[10px] font-bold text-muted-foreground">
                              C
                            </span>
                          )}
                          {p.isKeyPlayer && <Star className="size-3 fill-warning text-warning" />}
                        </span>
                      </Link>
                    </TableCell>
                    <TableCell className="hidden text-sm text-muted-foreground md:table-cell">
                      {p.club}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">{p.age ?? "—"}</TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {p.stats.appearances}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">{p.stats.goals}</TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {p.stats.minutes.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <RatingPill rating={p.rating} />
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
