"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART, ChartValue, toNum, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "./theme";
import type { CalibrationBin } from "@/lib/types";

export function CalibrationChart({ bins, height = 240 }: { bins: CalibrationBin[]; height?: number }) {
  const data = bins.map((b) => ({
    predicted: Number((b.predicted * 100).toFixed(1)),
    observed: Number((b.observed * 100).toFixed(1)),
    ideal: Number((b.predicted * 100).toFixed(1)),
  }));

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
          <XAxis
            dataKey="predicted"
            type="number"
            domain={[0, 100]}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}%`}
            label={{
              value: "Predicted confidence",
              position: "insideBottom",
              offset: -2,
              fill: CHART.axis,
              fontSize: 11,
            }}
          />
          <YAxis
            domain={[0, 100]}
            width={40}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={tooltipContentStyle}
            itemStyle={tooltipItemStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(v: ChartValue, n) => [`${toNum(v)}%`, n === "observed" ? "Observed" : "Perfect"]}
            labelFormatter={(l) => `Predicted ${l}%`}
          />
          <Line
            type="monotone"
            dataKey="ideal"
            stroke={CHART.slate}
            strokeDasharray="4 4"
            strokeWidth={1.5}
            dot={false}
            name="Perfect"
          />
          <Line
            type="monotone"
            dataKey="observed"
            stroke={CHART.primary}
            strokeWidth={2.5}
            dot={{ r: 3, fill: CHART.primary }}
            name="Observed"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
