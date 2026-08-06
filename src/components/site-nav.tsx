"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Menu, Search, Hexagon, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { openCommandPalette, CommandPalette } from "@/components/command-palette";
import { DataFreshnessControl } from "@/components/refresh-data-button";
import { LeagueSwitcher } from "@/components/league-switcher";
import { resolveSelection, LEAGUE_PARAM, SEASON_PARAM } from "@/lib/league";
import type { IndexData } from "@/lib/types";

const LINKS = [
  { label: "Dashboard", href: "/" },
  { label: "Matches", href: "/matches" },
  { label: "Predictions", href: "/predictions" },
  { label: "Table", href: "/table" },
  { label: "Clubs", href: "/clubs" },
  { label: "Players", href: "/players" },
  { label: "Rankings", href: "/rankings" },
  { label: "Models", href: "/models" },
  { label: "Data", href: "/methodology" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav({ index, refreshEnabled }: { index: IndexData; refreshEnabled: boolean }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const params = React.useMemo(() => {
    const obj: Record<string, string> = {};
    searchParams.forEach((v, k) => (obj[k] = v));
    return obj;
  }, [searchParams]);

  const selection = resolveSelection(index, params);
  const query = `?${LEAGUE_PARAM}=${selection.league}&${SEASON_PARAM}=${selection.season}`;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/70 glass supports-[backdrop-filter]:bg-background/55">
      <div className="container-page flex h-14 items-center gap-3">
        <Link href={`/${query}`} className="flex items-center gap-2 font-semibold">
          <span className="relative flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-primary-foreground shadow-sm">
            <Hexagon className="size-4" fill="currentColor" />
          </span>
          <span className="hidden sm:inline tracking-tight">
            Soccer <span className="text-gradient">Agent</span>
          </span>
        </Link>

        <div className="ml-1 hidden sm:block">
          <LeagueSwitcher index={index} league={selection.league} season={selection.season} />
        </div>

        <nav className="ml-2 hidden items-center gap-0.5 xl:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={`${link.href}${query}`}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
                isActive(pathname, link.href)
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <DataFreshnessControl
            asOf={index.generatedAt}
            generatedAt={index.generatedAt}
            enabled={refreshEnabled}
          />
          <button
            onClick={openCommandPalette}
            className="hidden items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm transition-colors hover:bg-secondary md:flex"
            aria-label="Open search"
          >
            <Search className="size-3.5" />
            <span>Search…</span>
            <kbd className="ml-2 rounded border border-border bg-muted px-1.5 font-mono text-[10px]">
              ⌘K
            </kbd>
          </button>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Search"
            onClick={openCommandPalette}
          >
            <Search className="size-4" />
          </Button>
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            className="xl:hidden"
            aria-label="Menu"
            onClick={() => setMobileOpen((o) => !o)}
          >
            {mobileOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-border bg-background xl:hidden">
          <div className="container-page py-3">
            <div className="mb-2 sm:hidden">
              <LeagueSwitcher index={index} league={selection.league} season={selection.season} />
            </div>
            <nav className="grid grid-cols-2 gap-1 sm:grid-cols-3">
              {LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={`${link.href}${query}`}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive(pathname, link.href)
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/60",
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      )}

      <CommandPalette selection={selection} query={query} />
    </header>
  );
}
