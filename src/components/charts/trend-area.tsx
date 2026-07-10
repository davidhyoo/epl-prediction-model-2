"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART, ChartValue, toNum, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "./theme";

interface TrendAreaProps {
  data: { label: string; value: number }[];
  color?: string;
  height?: number;
  /** Format Y as percent (0-1 values) */
  percent?: boolean;
  yDomain?: [number, number];
  valueName?: string;
}

export function TrendArea({
  data,
  color = CHART.primary,
  height = 220,
  percent = false,
  yDomain,
  valueName = "Value",
}: TrendAreaProps) {
  const gradId = `grad-${valueName.replace(/\s/g, "")}`;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.35} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            width={40}
            domain={yDomain ?? ["auto", "auto"]}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => (percent ? `${Math.round(v * 100)}%` : `${v}`)}
          />
          <Tooltip
            contentStyle={tooltipContentStyle}
            itemStyle={tooltipItemStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(v: ChartValue) => [
              percent ? `${(toNum(v) * 100).toFixed(1)}%` : toNum(v).toFixed(0),
              valueName,
            ]}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradId})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
