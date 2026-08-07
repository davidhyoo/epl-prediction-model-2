import * as React from "react";
import { CalendarClock } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Shown for a tournament season whose league-phase draw has not been published
 * yet (e.g. UCL 2026-27 before the late-August draw). The 36-club field is a
 * projection carried forward from the previous edition and the trophy odds are a
 * pure Elo forecast; there are no fixtures to show until the draw lands. The
 * in-app Refresh button pulls the real bracket, fixtures, results and scorers
 * the moment openfootball publishes them.
 */
export function DrawPendingBanner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border border-primary/25 bg-primary/5 px-4 py-3.5 text-sm",
        className,
      )}
    >
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary [&_svg]:size-4">
        <CalendarClock />
      </div>
      <div className="space-y-1">
        <p className="font-semibold">League-phase draw pending</p>
        <p className="text-muted-foreground">
          The 2026/27 field below is a projection carried forward from last season and the
          trophy odds are an Elo-based forecast. The real 36-club draw is made in late August —
          hit <span className="font-medium text-foreground">Refresh</span> then and the app fills in
          the actual fixtures, results, standings and scorers automatically.
        </p>
      </div>
    </div>
  );
}
