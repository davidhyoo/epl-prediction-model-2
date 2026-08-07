"use client";

import * as React from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART, RACE_COLORS, tooltipContentStyle, tooltipLabelStyle } from "./theme";
import { cn } from "@/lib/utils";
import type { TitleRace } from "@/lib/types";

const MAX_LINES = 8; // how many contenders get a highlighted colour + legend slot
const MUTED = "hsl(220 12% 55%)";

/** Compact knockout-stage labels so the x-axis ticks never overlap. */
const STAGE_ABBREV: Record<string, string> = {
  "Bracket set": "Bracket",
  "Play-offs": "PO",
  "Round of 16": "R16",
  "Quarter-finals": "QF",
  "Semi-finals": "SF",
  Final: "Final",
};
function abbrevStage(label: string): string {
  return STAGE_ABBREV[label] ?? label;
}

type TipPayload = { dataKey?: string | number; value?: number; color?: string };

/**
 * Title-race chart: every club's championship probability traced matchday by
 * matchday. The genuine contenders (by peak probability) get distinct colours
 * and a clickable legend; the rest render as faint context lines. Clicking a
 * club isolates its line.
 */
export function TitleRaceChart({ race, height = 380 }: { race: TitleRace; height?: number }) {
  const [focus, setFocus] = React.useState<string | null>(null);
  const [showAll, setShowAll] = React.useState(true);

  // Tournament races (UCL) tag each checkpoint with a knockout stage rather than
  // a matchday number; switch the axis + tooltip into "stage" mode when present.
  const stageLabels =
    race.labels && race.labels.length === race.checkpoints.length ? race.labels : null;
  const xCaption = race.xLabel ?? "Matchday";

  const { data, contenders, others, colorOf, shortOf, playedByMd, labelByCp } = React.useMemo(() => {
    const contenders = race.clubs.filter((c) => c.peak >= 1).slice(0, MAX_LINES);
    // guarantee at least the leader is drawn even in a flat/early race
    if (contenders.length === 0 && race.clubs.length > 0) contenders.push(race.clubs[0]);
    const contenderCodes = new Set(contenders.map((c) => c.code));
    const others = race.clubs.filter((c) => !contenderCodes.has(c.code));

    const colorOf: Record<string, string> = {};
    contenders.forEach((c, i) => (colorOf[c.code] = RACE_COLORS[i % RACE_COLORS.length]));
    const shortOf: Record<string, string> = {};
    race.clubs.forEach((c) => (shortOf[c.code] = c.short));

    const data = race.checkpoints.map((cp, i) => {
      const row: Record<string, number> = { md: cp };
      for (const c of race.clubs) row[c.code] = race.series[c.code]?.[i] ?? 0;
      return row;
    });
    const playedByMd: Record<number, number> = {};
    race.checkpoints.forEach((cp, i) => (playedByMd[cp] = race.playedAt[i] ?? 0));
    const labelByCp: Record<number, string> = {};
    if (stageLabels) race.checkpoints.forEach((cp, i) => (labelByCp[cp] = stageLabels[i]));

    return { data, contenders, others, colorOf, shortOf, playedByMd, labelByCp };
  }, [race, stageLabels]);

  if (race.checkpoints.length < 2) {
    return (
      <p className="py-16 text-center text-sm text-muted-foreground">
        The title-race chart appears once the season has completed matches — it traces how each
        club&rsquo;s championship probability evolves matchday by matchday.
      </p>
    );
  }

  const tickStep = Math.max(1, Math.ceil(race.checkpoints.length / 9));
  const ticks = stageLabels
    ? race.checkpoints
    : race.checkpoints.filter((cp) => cp % tickStep === 0);
  if (!stageLabels && ticks[ticks.length - 1] !== race.lastCompletedRound)
    ticks.push(race.lastCompletedRound);

  const dim = (code: string) => focus != null && focus !== code;

  return (
    <div className="space-y-3">
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
            <XAxis
              dataKey="md"
              type="number"
              domain={[0, race.lastCompletedRound]}
              ticks={ticks}
              tick={{ fill: CHART.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={
                stageLabels ? (v: number) => abbrevStage(labelByCp[v] ?? String(v)) : undefined
              }
              label={{
                value: xCaption,
                position: "insideBottom",
                offset: -8,
                fill: CHART.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              domain={[0, 100]}
              width={44}
              tick={{ fill: CHART.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              contentStyle={tooltipContentStyle}
              labelStyle={tooltipLabelStyle}
              isAnimationActive={false}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const md = Number(label);
                const rows = (payload as ReadonlyArray<TipPayload>)
                  .map((p) => ({
                    code: String(p.dataKey),
                    value: Number(p.value ?? 0),
                    color: colorOf[String(p.dataKey)] ?? MUTED,
                  }))
                  .filter((r) => r.value >= 0.5)
                  .sort((a, b) => b.value - a.value)
                  .slice(0, 8);
                return (
                  <div style={tooltipContentStyle} className="min-w-[9rem]">
                    <div style={tooltipLabelStyle}>
                      {stageLabels
                        ? (labelByCp[md] ?? `Round ${md}`)
                        : `Matchday ${md} · ${playedByMd[md] ?? 0} played`}
                    </div>
                    {rows.length === 0 ? (
                      <div className="text-xs text-muted-foreground">Wide open</div>
                    ) : (
                      rows.map((r) => (
                        <div
                          key={r.code}
                          className="flex items-center justify-between gap-4 text-xs tabular-nums"
                        >
                          <span className="flex items-center gap-1.5">
                            <span
                              className="inline-block size-2 rounded-full"
                              style={{ background: r.color }}
                            />
                            {shortOf[r.code] ?? r.code}
                          </span>
                          <span className="font-medium">{r.value.toFixed(1)}%</span>
                        </div>
                      ))
                    )}
                  </div>
                );
              }}
            />

            {/* context lines: the also-rans */}
            {showAll &&
              others.map((c) => (
                <Line
                  key={c.code}
                  type="monotone"
                  dataKey={c.code}
                  stroke={MUTED}
                  strokeWidth={1}
                  strokeOpacity={focus ? 0.06 : 0.16}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}

            {/* highlighted contenders */}
            {contenders.map((c) => (
              <Line
                key={c.code}
                type="monotone"
                dataKey={c.code}
                stroke={colorOf[c.code]}
                strokeWidth={dim(c.code) ? 1.25 : 2.5}
                strokeOpacity={dim(c.code) ? 0.25 : 1}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {contenders.map((c) => (
          <button
            key={c.code}
            type="button"
            onClick={() => setFocus(focus === c.code ? null : c.code)}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
              focus === c.code
                ? "border-foreground/30 bg-secondary"
                : "border-border hover:bg-secondary/60",
              focus && focus !== c.code && "opacity-50",
            )}
            aria-pressed={focus === c.code}
          >
            <span
              className="inline-block size-2.5 rounded-full"
              style={{ background: colorOf[c.code] }}
            />
            <span className="font-medium">{c.short}</span>
            <span className="tabular-nums text-muted-foreground">
              peak {c.peak.toFixed(0)}%
            </span>
          </button>
        ))}
        {others.length > 0 && (
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="ml-auto rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:bg-secondary/60"
          >
            {showAll ? "Hide" : "Show"} {others.length} others
          </button>
        )}
      </div>
      {focus && (
        <p className="text-xs text-muted-foreground">
          Isolating <span className="font-medium text-foreground">{shortOf[focus]}</span> — click its
          chip again to show every contender.
        </p>
      )}
    </div>
  );
}
