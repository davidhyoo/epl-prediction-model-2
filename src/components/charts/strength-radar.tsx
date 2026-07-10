"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { CHART, ChartValue, toNum, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "./theme";

interface StrengthRadarProps {
  data: { metric: string; value: number }[];
  color?: string;
  height?: number;
}

export function StrengthRadar({ data, color = CHART.primary, height = 260 }: StrengthRadarProps) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke={CHART.grid} />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: CHART.axis, fontSize: 11 }}
          />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.28}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={tooltipContentStyle}
            itemStyle={tooltipItemStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(v: ChartValue) => [`${Math.round(toNum(v))}/100`, "Rating"]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
