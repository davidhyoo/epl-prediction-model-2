import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";
import { ModelsWorkbench } from "@/components/models-workbench";
import { getSelection, getModels, getSummary, getRace } from "@/lib/data";
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
  const [models, summary, race] = await Promise.all([
    getModels(sel),
    getSummary(sel),
    getRace(sel),
  ]);
  const best = models.leaderboard.find((m) => m.rank === 1) ?? models.leaderboard[0];
  const evaluated = models.meta.evaluated;

  return (
    <div className="container-page space-y-6 py-8">
      <PageHeader
        eyebrow={`${summary.league.name} · ${summary.season.label}`}
        title="Models & predictions"
        description="Two layers of prediction: six models price every fixture (win/draw/loss), and a Monte-Carlo simulation turns those edges into each club's championship probability. Switch between the per-game leaderboard and the season-long title race below."
        actions={<Badge variant="outline">{evaluated.toLocaleString()} matches evaluated</Badge>}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Best per-game model"
          value={evaluated > 0 ? best.name : "—"}
          sub={evaluated > 0 && best.accuracy != null ? `${pct(best.accuracy, 1)} accuracy` : "Awaiting results"}
          accent="success"
        />
        <StatCard
          label="Projected champion"
          value={summary.champion ? summary.champion.name : "—"}
          sub={summary.champion ? `${summary.champion.probability.toFixed(1)}% title probability` : "Season not started"}
          accent="primary"
        />
        <StatCard
          label="Matches evaluated"
          value={evaluated.toLocaleString()}
          sub={evaluated > 0 ? "Backtested, leakage-free" : "Season not started"}
          accent="info"
        />
      </div>

      <ModelsWorkbench models={models} race={race} champion={summary.champion} />

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
