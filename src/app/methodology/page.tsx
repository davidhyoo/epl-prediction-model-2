import type { Metadata } from "next";
import {
  Database,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
  FlaskConical,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { ImportanceBars } from "@/components/charts/importance-bars";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getMethodology, getSummary } from "@/lib/data";
import { formatDateTime } from "@/lib/format";

export const metadata: Metadata = {
  title: "Data & Methodology",
  description:
    "The data pipeline, feature set, models, leakage controls and self-improvement loop behind the 2026 World Cup predictor.",
};

const KIND_VARIANT: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
  generated: "warning",
  cached: "info",
  live: "success",
  static: "muted",
};

const STAGE_ICON: Record<string, React.ElementType> = {
  ingest: Database,
  transform: ShieldCheck,
  features: Layers,
  train: GitBranch,
  predict: Sparkles,
  evaluate: FlaskConical,
};

export default async function MethodologyPage() {
  const [methodology, summary] = await Promise.all([getMethodology(), getSummary()]);

  return (
    <div className="container-page space-y-8 py-8">
      <PageHeader
        eyebrow="Data & methodology"
        title="How the predictions are made"
        description="A fully reproducible, offline-first pipeline turns a seeded dataset into features, five models, simulated tournament odds and a self-scoring backtest. Every step is deterministic and re-runnable with one command."
      />

      {/* Data mode banner */}
      <Card className="border-warning/40 bg-warning/5">
        <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <FlaskConical className="mt-0.5 size-5 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-semibold">Data mode: generated demo dataset</p>
              <p className="text-sm text-muted-foreground">
                No paid APIs or scraped content are used. Match history, squads and player stats are
                deterministically synthesised so the whole app runs offline and reproducibly. Swap in
                a live source by editing <code>ml/ingest.py</code>.
              </p>
            </div>
          </div>
          <div className="shrink-0 text-xs text-muted-foreground sm:text-right">
            <div>{summary.trainingMatches.toLocaleString()} training matches</div>
            <div>{summary.featureCount} engineered features</div>
          </div>
        </CardContent>
      </Card>

      {/* Pipeline */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Pipeline</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {methodology.pipeline.map((stage, i) => {
            const Icon = STAGE_ICON[stage.id] ?? Database;
            return (
              <Card key={stage.id} className="relative overflow-hidden">
                <CardContent className="space-y-2 p-4">
                  <div className="flex items-center gap-2">
                    <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="size-4" />
                    </span>
                    <span className="text-xs font-medium tabular-nums text-muted-foreground">
                      Step {i + 1}
                    </span>
                  </div>
                  <h3 className="font-semibold">{stage.title}</h3>
                  <p className="text-sm text-muted-foreground">{stage.description}</p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {stage.outputs.map((o) => (
                      <Badge key={o} variant="outline" className="font-mono text-[10px]">
                        {o}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Data sources */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Data sources</h2>
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Source</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="hidden md:table-cell">Description</TableHead>
                  <TableHead>License</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {methodology.dataSources.map((s) => (
                  <TableRow key={s.name}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell>
                      <Badge variant={KIND_VARIANT[s.kind]} className="capitalize">
                        {s.kind}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden max-w-md text-sm text-muted-foreground md:table-cell">
                      {s.description}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{s.license}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>

      {/* Features + models */}
      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Feature set</CardTitle>
            <p className="text-sm text-muted-foreground">
              {methodology.features.length} features drive the models. Relative influence is averaged
              across the tree-based models.
            </p>
          </CardHeader>
          <CardContent>
            <ImportanceBars importances={methodology.features} height={methodology.features.length * 30} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Models</CardTitle>
            <p className="text-sm text-muted-foreground">
              Five complementary approaches, blended into a self-weighting ensemble.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {methodology.models.map((m) => (
              <div key={m.id} className="rounded-lg border p-3">
                <div className="font-medium">{m.name}</div>
                <p className="text-sm text-muted-foreground">{m.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      {/* Leakage + self-improvement notes */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Leakage controls & self-improvement</h2>
        <Card>
          <CardContent className="space-y-3 p-4">
            <ul className="space-y-2">
              {methodology.notes.map((note, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>

      <p className="text-center text-xs text-muted-foreground">
        Pipeline last run {formatDateTime(methodology.generatedAt)} · reproduce with{" "}
        <code>python ml/pipeline.py</code>
      </p>
    </div>
  );
}
