import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RefreshDataButton } from "@/components/refresh-data-button";
import {
  Database,
  Filter,
  Wand2,
  Brain,
  Target,
  ClipboardCheck,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { getSelection, getSummary } from "@/lib/data";
import { formatDateTime } from "@/lib/format";
import type { SearchParams } from "@/lib/league";

export const metadata = { title: "Data & Methodology" };

const STAGES = [
  {
    icon: Database,
    name: "Ingest",
    file: "ml/club_ingest.py",
    text: "Turns the cached source files into per-season match + squad structures. Fixtures, results and inline goalscorers come from openfootball (CC0); per-match shots/corners/cards + closing market odds from football-data.co.uk. Every response is cached under data/raw so a rebuild never re-hits the network unnecessarily.",
  },
  {
    icon: Filter,
    name: "Validate & parse",
    file: "ml/club_sources.py",
    text: "Pure parsers for the cached source files: they reconcile the two openfootball text formats, normalise club names to stable codes, validate scorelines against scorer lists, and drop or flag rows that fail schema checks so bad data never reaches the model.",
  },
  {
    icon: Wand2,
    name: "Feature engineering",
    file: "ml/club_features.py",
    text: "A single chronological engine builds a strictly pre-match feature row for every fixture: rolling form, goals for/against rates, rest days, home advantage, Elo rating difference and market-implied probabilities — all computed only from matches played before kickoff.",
  },
  {
    icon: Brain,
    name: "Train",
    file: "ml/club_train.py",
    text: "Fits the base learners — Elo baseline, logistic regression, random forest and XGBoost — plus a market baseline, using walk-forward folds so a model is never trained on a match it will later be scored on.",
  },
  {
    icon: Target,
    name: "Predict",
    file: "ml/club_predict.py",
    text: "Loads the trained models, scores every fixture into win/draw/loss probabilities, blends the base learners into a weighted ensemble, and attaches the top contributing factors behind each prediction.",
  },
  {
    icon: RefreshCw,
    name: "Simulate",
    file: "ml/club_simulate.py",
    text: "Runs the remaining fixtures through a 10,000-season Monte-Carlo simulation to estimate every club's chance of winning the title, qualifying for the Champions League or Europa League, and being relegated.",
  },
  {
    icon: ShieldCheck,
    name: "Players",
    file: "ml/club_players.py",
    text: "Combines real, free data sources into the squad roster: Wikipedia/Wikimedia Commons for players + licensed headshots, and openfootball goalscorer data for real goals and goal-minute timelines. Missing photos fall back to clean initials avatars.",
  },
  {
    icon: ClipboardCheck,
    name: "Evaluate & publish",
    file: "ml/club_evaluate.py",
    text: "Scores each model against completed results on accuracy, log loss, Brier score and calibration (ECE), re-ranks the leaderboard, re-derives ensemble weights, and writes every cached JSON the dashboard reads.",
  },
];

const SOURCES = [
  {
    name: "openfootball",
    kind: "Fixtures · results · scorers",
    license: "CC0 (public domain)",
    mode: "Live + cached",
  },
  {
    name: "football-data.co.uk",
    kind: "Match stats · closing odds",
    license: "Free for non-commercial use",
    mode: "Live + cached",
  },
  {
    name: "Wikipedia / Wikimedia Commons",
    kind: "Squads · headshots",
    license: "CC BY-SA / public domain (per file)",
    mode: "Cached, credited",
  },
];

function refreshEnabled(): boolean {
  return process.env.NODE_ENV !== "production" || process.env.ALLOW_DATA_REFRESH === "1";
}

export default async function MethodologyPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const sel = await getSelection(sp);
  const summary = await getSummary(sel);
  const enabled = refreshEnabled();

  return (
    <div className="container-page space-y-8 py-8">
      <PageHeader
        eyebrow="Transparency"
        title="Data & methodology"
        description="Everything here is rebuilt from open, legally-licensed data by a reproducible Python pipeline. No paid APIs, no scraping of disallowed content, and no result ever leaks into a prediction it is later judged on."
        actions={<Badge variant="outline">Open data · reproducible</Badge>}
      />

      {/* Data sources */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Data sources</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {SOURCES.map((s) => (
            <Card key={s.name} className="p-4">
              <p className="font-semibold">{s.name}</p>
              <p className="mt-0.5 text-sm text-muted-foreground">{s.kind}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge variant="secondary" className="text-[10px]">{s.mode}</Badge>
                <Badge variant="muted" className="text-[10px]">{s.license}</Badge>
              </div>
            </Card>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Results loaded through {formatDateTime(summary.lastUpdated)}. Where a live source is
          temporarily unavailable, the pipeline falls back to the committed cache so the app always
          runs end-to-end.
        </p>
      </section>

      {/* Pipeline */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">The pipeline (eight stages)</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {STAGES.map((s, i) => (
            <Card key={s.name} className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <s.icon className="size-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground tabular-nums">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <p className="font-semibold">{s.name}</p>
                  </div>
                  <code className="text-[11px] text-primary">{s.file}</code>
                  <p className="mt-1.5 text-sm text-muted-foreground">{s.text}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Season strategy */}
      <section className="grid gap-3 md:grid-cols-2">
        <Card className="p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="size-4 text-primary" /> Two-season strategy
          </div>
          <p className="text-sm text-muted-foreground">
            The pipeline is validated on the <strong className="text-foreground">2025/26</strong>{" "}
            season, which is complete — so every prediction can be checked against a real result. The
            deliverable is <strong className="text-foreground">2026/27</strong>, which hasn&rsquo;t
            kicked off yet: fixtures load as pre-season forecasts and sharpen into live, evaluated
            predictions automatically as real results arrive.
          </p>
        </Card>
        <Card className="p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Target className="size-4 text-primary" /> No data leakage
          </div>
          <p className="text-sm text-muted-foreground">
            Features for a fixture are built only from matches played before it. Models predict first;
            actual results are used strictly afterwards for backtesting. Evaluation walks forward in
            date order, and ensemble weights are re-derived from recent accuracy on each refresh.
          </p>
        </Card>
      </section>

      {/* Refresh */}
      <section>
        <Card className="p-6">
          <CardHeader className="p-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <RefreshCw className="size-4 text-primary" /> Live data refresh
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 p-0 pt-4 text-sm text-muted-foreground">
            <p>
              The refresh button in the top bar (and below) triggers{" "}
              <code className="text-primary">POST /api/refresh</code>, which shells out to{" "}
              <code className="text-primary">ml/club_refresh.py</code>. That script re-pulls the
              latest completed results &amp; scorers from the open sources, replays the full
              ingest → evaluate pipeline, and rewrites every JSON under{" "}
              <code className="text-primary">public/data/**</code>. The route then calls{" "}
              <code className="text-primary">revalidatePath(&quot;/&quot;, &quot;layout&quot;)</code>{" "}
              so every page re-reads the new data — no code change or restart required.
            </p>
            <ol className="ml-4 list-decimal space-y-1">
              <li>Click refresh → the button locks and a progress toast appears.</li>
              <li>The Python pipeline pulls new results, retrains and re-evaluates (~1–2 min).</li>
              <li>On success the route purges the route cache and the UI re-fetches server data.</li>
              <li>If a source is down, it falls back to cache and reports the reason in the toast.</li>
            </ol>
            <p>
              A module-level guard prevents overlapping runs, and the endpoint is disabled in
              production unless <code className="text-primary">ALLOW_DATA_REFRESH=1</code> is set —
              executing a child process from a web request is only safe on a trusted machine.
            </p>
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              {enabled ? (
                <div className="space-y-3 text-center">
                  <p className="text-foreground">Refresh is enabled in this environment.</p>
                  <RefreshDataButton />
                </div>
              ) : (
                <p className="text-center">
                  Refresh is disabled here. Run{" "}
                  <code className="text-primary">npm run data:refresh</code> locally, or set{" "}
                  <code className="text-primary">ALLOW_DATA_REFRESH=1</code>.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
