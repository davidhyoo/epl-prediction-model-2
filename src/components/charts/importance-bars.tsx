"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART, ChartValue, toNum, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "./theme";
import type { FeatureImportance } from "@/lib/types";

export function ImportanceBars({
  importances,
  height,
  color = CHART.info,
}: {
  importances: FeatureImportance[];
  height?: number;
  color?: string;
}) {
  const data = importances.map((f) => ({
    label: f.label,
    value: Number((f.importance * 100).toFixed(1)),
  }));
  const h = height ?? Math.max(data.length * 30, 160);

  return (
    <div style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={150}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted) / 0.5)" }}
            contentStyle={tooltipContentStyle}
            itemStyle={tooltipItemStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(v: ChartValue) => [`${toNum(v)}%`, "Relative importance"]}
          />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} maxBarSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
