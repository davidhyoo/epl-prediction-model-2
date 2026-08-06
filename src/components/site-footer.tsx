import Link from "next/link";
import { Hexagon } from "lucide-react";
import { DevCreditLinks } from "@/components/dev-credit";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border">
      <div className="container-page flex flex-col gap-6 py-10 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm space-y-3">
          <div className="flex items-center gap-2 font-semibold">
            <span className="flex size-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-primary-foreground">
              <Hexagon className="size-4" fill="currentColor" />
            </span>
            Data Driven Soccer
          </div>
          <p className="text-sm text-muted-foreground">
            A data-science portfolio project: a reproducible ML pipeline that predicts match
            outcomes and simulates full-season odds for the Premier League and La Liga, validated on
            real completed results.
          </p>
          <p className="text-xs text-muted-foreground">
            Predictions are model estimates, not guarantees. Built on open data — see the Data &amp;
            Methodology page for sources and licensing.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 text-sm sm:grid-cols-3">
          <div className="space-y-2">
            <p className="font-semibold">Explore</p>
            <Link href="/matches" className="block text-muted-foreground hover:text-foreground">
              Matches
            </Link>
            <Link href="/table" className="block text-muted-foreground hover:text-foreground">
              League table
            </Link>
            <Link href="/clubs" className="block text-muted-foreground hover:text-foreground">
              Clubs
            </Link>
            <Link href="/players" className="block text-muted-foreground hover:text-foreground">
              Players
            </Link>
          </div>
          <div className="space-y-2">
            <p className="font-semibold">Analytics</p>
            <Link href="/predictions" className="block text-muted-foreground hover:text-foreground">
              Predictions
            </Link>
            <Link href="/rankings" className="block text-muted-foreground hover:text-foreground">
              Rankings
            </Link>
            <Link href="/models" className="block text-muted-foreground hover:text-foreground">
              Models
            </Link>
            <Link href="/methodology" className="block text-muted-foreground hover:text-foreground">
              Methodology
            </Link>
          </div>
          <div className="space-y-2">
            <p className="font-semibold">Data</p>
            <p className="text-muted-foreground">openfootball · football-data</p>
            <p className="text-muted-foreground">scikit-learn · XGBoost</p>
            <p className="text-muted-foreground">Next.js · TypeScript</p>
          </div>
        </div>
      </div>
      <div className="border-t border-border">
        <div className="container-page flex flex-col items-center justify-between gap-2 py-4 text-xs text-muted-foreground sm:flex-row">
          <p>© {new Date().getFullYear()} Data Driven Soccer — built by David Yoo.</p>
          <DevCreditLinks />
          <p>Flags via flag-icons (public domain). Headshots via Wikimedia Commons (CC).</p>
        </div>
      </div>
    </footer>
  );
}
