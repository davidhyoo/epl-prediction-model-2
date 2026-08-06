"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Home,
  CalendarDays,
  Trophy,
  Table2,
  Shield,
  Users,
  BarChart3,
  Brain,
  Database,
  User,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Flag } from "@/components/flag";
import type { Selection } from "@/lib/types";

interface SearchClub {
  code: string;
  name: string;
  short: string;
  position: number;
  title: number;
}
interface SearchPlayer {
  id: string;
  name: string;
  club: string;
  clubName: string;
  nationIso2: string;
  position: string;
}

const NAV = [
  { label: "Dashboard", href: "/", icon: Home },
  { label: "Matches", href: "/matches", icon: CalendarDays },
  { label: "Predictions", href: "/predictions", icon: Trophy },
  { label: "League Table", href: "/table", icon: Table2 },
  { label: "Clubs", href: "/clubs", icon: Shield },
  { label: "Players", href: "/players", icon: Users },
  { label: "Rankings", href: "/rankings", icon: BarChart3 },
  { label: "Models", href: "/models", icon: Brain },
  { label: "Data & Methodology", href: "/methodology", icon: Database },
];

export const OPEN_COMMAND_EVENT = "open-command-palette";

export function CommandPalette({ selection, query }: { selection: Selection; query: string }) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [clubs, setClubs] = React.useState<SearchClub[]>([]);
  const [players, setPlayers] = React.useState<SearchPlayer[]>([]);
  const loadedFor = React.useRef<string>("");

  const key = `${selection.league}/${selection.season}`;

  const load = React.useCallback(async () => {
    if (loadedFor.current === key) return;
    loadedFor.current = key;
    try {
      const [c, p] = await Promise.all([
        fetch(`/data/${key}/clubs.json`).then((r) => r.json()),
        fetch(`/data/${key}/players.json`).then((r) => r.json()),
      ]);
      setClubs(
        (c as Array<{ code: string; name: string; short: string; standing: { position: number }; odds: { title: number } }>).map((x) => ({
          code: x.code,
          name: x.name,
          short: x.short,
          position: x.standing.position,
          title: x.odds.title,
        })),
      );
      setPlayers(
        (p as { players: Array<{ id: string; name: string; club: string; clubName: string; nationIso2: string; position: string }> }).players.map((x) => ({
          id: x.id,
          name: x.name,
          club: x.club,
          clubName: x.clubName,
          nationIso2: x.nationIso2,
          position: x.position,
        })),
      );
    } catch {
      setClubs([]);
      setPlayers([]);
    }
  }, [key]);

  const openPalette = React.useCallback(() => {
    setOpen(true);
    void load();
  }, [load]);

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || e.key === "/") {
        if (e.key === "/" && isTypingTarget(e.target)) return;
        e.preventDefault();
        openPalette();
      }
    };
    const openHandler = () => openPalette();
    document.addEventListener("keydown", down);
    window.addEventListener(OPEN_COMMAND_EVENT, openHandler);
    return () => {
      document.removeEventListener("keydown", down);
      window.removeEventListener(OPEN_COMMAND_EVENT, openHandler);
    };
  }, [openPalette]);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? openPalette() : setOpen(false))}>
      <DialogContent hideClose className="max-w-xl gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <Command filter={(value, search) => (value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0)}>
          <CommandInput placeholder="Search clubs, players, or pages…" />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>

            <CommandGroup heading="Navigate">
              {NAV.map((item) => (
                <CommandItem
                  key={item.href}
                  value={`page ${item.label}`}
                  onSelect={() => go(`${item.href}${query}`)}
                >
                  <item.icon className="size-4 text-muted-foreground" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>

            {clubs.length > 0 && (
              <CommandGroup heading="Clubs">
                {clubs.map((c) => (
                  <CommandItem
                    key={c.code}
                    value={`club ${c.name} ${c.code}`}
                    onSelect={() => go(`/clubs/${c.code.toLowerCase()}${query}`)}
                  >
                    <Shield className="size-4 text-muted-foreground" />
                    <span className="flex-1">{c.name}</span>
                    <span className="text-xs tabular-nums text-muted-foreground">#{c.position}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            {players.length > 0 && (
              <CommandGroup heading="Players">
                {players.slice(0, 120).map((p) => (
                  <CommandItem
                    key={p.id}
                    value={`player ${p.name} ${p.clubName} ${p.position}`}
                    onSelect={() => go(`/players/${p.id}${query}`)}
                  >
                    <User className="size-4 text-muted-foreground" />
                    <span className="flex-1">{p.name}</span>
                    <Flag iso2={p.nationIso2} size="sm" />
                    <span className="w-10 text-right text-xs text-muted-foreground">{p.position}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || el.isContentEditable;
}

/** Small helper used by the nav search button. */
export function openCommandPalette() {
  window.dispatchEvent(new Event(OPEN_COMMAND_EVENT));
}
