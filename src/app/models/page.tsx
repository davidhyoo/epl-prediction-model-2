import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";
import { ModelsExplorer } from "@/components/models-explorer";
import { getSelection, getModels, getSummary } from "@/lib/data";
import { pct } from "@/lib/format";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "Models" };

export default async function ModelsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const [models, summary] = await Promise.all([getModels(sel), getSummary(sel)]);
  const best = models.leaderboard.find((m) => m.rank === 1) ?? models.leaderboard[0];
  const evaluated = models.meta.evaluated;

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow={`${summary.league.name} · ${summary.season.label}`}
        title="Model leaderboard"
        description="Six models predict every fixture independently before kickoff; once real results arrive they are scored on accuracy, log loss, Brier score and calibration. No result ever leaks into a prediction it is later judged on."
        actions={<Badge variant="outline">{evaluated.toLocaleString()} matches evaluated</Badge>}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Best model"
          value={evaluated > 0 ? best.name : "—"}
          sub={evaluated > 0 && best.accuracy != null ? `${pct(best.accuracy, 1)} accuracy` : "Awaiting results"}
          accent="success"
        />
        <StatCard
          label="Matches evaluated"
          value={evaluated.toLocaleString()}
          sub={evaluated > 0 ? "Backtested, leakage-free" : "Season not started"}
          accent="info"
        />
        <StatCard
          label="Models compared"
          value={models.leaderboard.length}
          sub="Baselines → ensemble"
          accent="primary"
        />
      </div>

      <ModelsExplorer models={models} />

      <div className="rounded-xl border border-border bg-card/50 p-5 text-sm text-muted-foreground">
        <h2 className="mb-2 text-sm font-semibold text-foreground">How the leaderboard stays honest</h2>
        <ul className="space-y-1.5">
          <li>
            <strong className="text-foreground">Predict first, score later.</strong> Every model
            emits win/draw/loss probabilities from features known <em>before</em> kickoff. Actual
            results are used only afterwards for evaluation.
          </li>
          <li>
            <strong className="text-foreground">Walk-forward evaluation.</strong> Matches are scored
            in date order so no future information influences an earlier prediction.
          </li>
          <li>
            <strong className="text-foreground">Self-tuning ensemble.</strong> Ensemble weights are
            re-derived from each base learner&rsquo;s recent accuracy every time the data is
            refreshed, so persistently weak models fade out.
          </li>
        </ul>
      </div>
    </div>
  );
}
