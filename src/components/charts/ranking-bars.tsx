"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART, ChartValue, toNum, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "./theme";

interface RankingBarsProps {
  data: { code: string; name: string; value: number }[];
  unit?: string;
  height?: number;
  color?: string;
}

export function RankingBars({ data, unit = "", height = 360, color = CHART.primary }: RankingBarsProps) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="code"
            width={42}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted) / 0.5)" }}
            contentStyle={tooltipContentStyle}
            itemStyle={tooltipItemStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(v: ChartValue, _n, p) => [
              `${toNum(v).toFixed(unit === "%" ? 1 : 0)}${unit}`,
              (p?.payload as { name?: string })?.name ?? "Value",
            ]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
            {data.map((d, i) => (
              <Cell key={d.code} fill={i === 0 ? CHART.primary : color} fillOpacity={i === 0 ? 1 : 0.7} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
