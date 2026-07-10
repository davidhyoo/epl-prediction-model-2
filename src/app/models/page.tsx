import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { ModelsExplorer } from "@/components/models-explorer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getModels, getSummary } from "@/lib/data";
import { formatDateTime, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "Models",
  description:
    "Model leaderboard for the 2026 World Cup predictor — accuracy, log loss, Brier score, calibration and feature importance across five models.",
};

export default async function ModelsPage() {
  const [models, summary] = await Promise.all([getModels(), getSummary()]);
  const evaluated = models[0]?.gamesEvaluated ?? 0;

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow="Model performance"
        title="Model leaderboard"
        description="Five independent approaches predict every match, then get scored on completed results only — no leakage. Models are re-ranked by log loss and the ensemble re-weights itself toward the sharpest, best-calibrated members."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Models evaluated"
          value={String(summary.modelCount)}
          hint="Elo, logistic regression, random forest, XGBoost and a weighted ensemble."
        />
        <SummaryCard
          label="Backtest matches"
          value={String(evaluated)}
          hint="Completed group-stage matches used for scoring only."
        />
        <SummaryCard
          label="Best model"
          value={summary.bestModel.name}
          hint={`Accuracy ${pct(summary.bestModel.accuracy)} · log loss ${summary.bestModel.logLoss.toFixed(3)}`}
        />
        <SummaryCard
          label="Last updated"
          value={formatDateTime(summary.generatedAt)}
          hint="Regenerated whenever the pipeline runs."
        />
      </div>

      <ModelsExplorer models={models} />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">How the self-improvement loop works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Every model generates probabilities for all 104 matches <em>before</em> any actual
            result is read. Only completed matches are then used for evaluation, so predictions can
            never peek at their own answers.
          </p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>Score each model on completed matches (accuracy, log loss, Brier, calibration/ECE).</li>
            <li>
              Re-rank all models by log loss and flag any that consistently underperform their
              peers.
            </li>
            <li>
              Recompute ensemble weights proportional to <code>1 / log loss</code>, so sharper,
              better-calibrated models earn more influence.
            </li>
            <li>Re-blend the ensemble and republish the cached predictions the site reads.</li>
          </ol>
          <p>
            These are statistical estimates from a reproducible model — not guarantees. See the{" "}
            <a href="/methodology" className="font-medium text-primary underline-offset-4 hover:underline">
              Data &amp; Methodology
            </a>{" "}
            page for the full pipeline and data-source notes.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <CardContent className="space-y-1 p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="truncate text-xl font-semibold" title={value}>
          {value}
        </div>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}
