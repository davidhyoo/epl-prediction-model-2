"use client";

import * as React from "react";
import { MatchCard } from "@/components/match/match-card";
import { PredictionModal } from "@/components/match/prediction-modal";
import type { Match } from "@/lib/types";
import type { ModelMeta } from "@/lib/model-meta";

/**
 * Renders a grid of match cards that share a single prediction modal. Used by
 * the matches explorer, the home dashboard and club detail pages.
 */
export function MatchList({
  matches,
  modelMeta,
  className = "grid gap-3 md:grid-cols-2 xl:grid-cols-3",
}: {
  matches: Match[];
  modelMeta: ModelMeta;
  className?: string;
}) {
  const [selected, setSelected] = React.useState<Match | null>(null);
  const [open, setOpen] = React.useState(false);

  const openFor = React.useCallback((m: Match) => {
    setSelected(m);
    setOpen(true);
  }, []);

  return (
    <>
      <div className={className}>
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} onOpenPrediction={openFor} />
        ))}
      </div>
      {selected && (
        <PredictionModal
          match={selected}
          open={open}
          onOpenChange={setOpen}
          modelMeta={modelMeta}
        />
      )}
    </>
  );
}
