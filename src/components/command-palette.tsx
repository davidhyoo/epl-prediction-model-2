"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Home,
  CalendarDays,
  Trophy,
  Globe2,
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
import { pct } from "@/lib/format";

interface SearchTeam {
  code: string;
  iso2: string;
  name: string;
  group: string;
  championProb: number;
}
interface SearchPlayer {
  id: string;
  name: string;
  country: string;
  countryCode: string;
  iso2: string;
  position: string;
  club: string;
  rating: number;
}
interface SearchIndex {
  teams: SearchTeam[];
  players: SearchPlayer[];
}

const NAV = [
  { label: "Dashboard", href: "/", icon: Home },
  { label: "Matches", href: "/matches", icon: CalendarDays },
  { label: "Predictions & Bracket", href: "/predictions", icon: Trophy },
  { label: "Countries", href: "/countries", icon: Globe2 },
  { label: "Players", href: "/players", icon: Users },
  { label: "Rankings", href: "/rankings", icon: BarChart3 },
  { label: "Models", href: "/models", icon: Brain },
  { label: "Data & Methodology", href: "/methodology", icon: Database },
];

export const OPEN_COMMAND_EVENT = "open-command-palette";

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [index, setIndex] = React.useState<SearchIndex | null>(null);
  const loadingRef = React.useRef(false);
  const loadedRef = React.useRef(false);

  // Stable loader (no reactive deps) so it can be triggered from event
  // handlers without an effect. Guards against duplicate fetches.
  const loadIndex = React.useCallback(async () => {
    if (loadedRef.current || loadingRef.current) return;
    loadingRef.current = true;
    try {
      const res = await fetch("/data/search.json");
      loadedRef.current = true;
      setIndex((await res.json()) as SearchIndex);
    } catch {
      loadedRef.current = true;
      setIndex({ teams: [], players: [] });
    } finally {
      loadingRef.current = false;
    }
  }, []);

  const openPalette = React.useCallback(() => {
    setOpen(true);
    void loadIndex();
  }, [loadIndex]);

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

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) void loadIndex();
  };

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent hideClose className="max-w-xl gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <Command
          filter={(value, search) =>
            value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0
          }
        >
          <CommandInput placeholder="Search teams, players, or pages…" />
          <CommandList>
            <CommandEmpty>{open && !index ? "Loading…" : "No results found."}</CommandEmpty>

            <CommandGroup heading="Navigate">
              {NAV.map((item) => (
                <CommandItem
                  key={item.href}
                  value={`page ${item.label}`}
                  onSelect={() => go(item.href)}
                >
                  <item.icon className="size-4 text-muted-foreground" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>

            {index && index.teams.length > 0 && (
              <CommandGroup heading="Teams">
                {index.teams.slice(0, 60).map((t) => (
                  <CommandItem
                    key={t.code}
                    value={`team ${t.name} ${t.code} ${t.group}`}
                    onSelect={() => go(`/countries/${t.code.toLowerCase()}`)}
                  >
                    <Flag iso2={t.iso2} size="sm" />
                    <span className="flex-1">{t.name}</span>
                    <span className="text-xs text-muted-foreground">
                      Grp {t.group} · {pct(t.championProb)}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            {index && index.players.length > 0 && (
              <CommandGroup heading="Players">
                {index.players.slice(0, 80).map((p) => (
                  <CommandItem
                    key={p.id}
                    value={`player ${p.name} ${p.country} ${p.club} ${p.position}`}
                    onSelect={() => go(`/players/${p.id}`)}
                  >
                    <User className="size-4 text-muted-foreground" />
                    <span className="flex-1">{p.name}</span>
                    <Flag iso2={p.iso2} size="sm" />
                    <span className="w-10 text-right text-xs text-muted-foreground">
                      {p.position}
                    </span>
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
