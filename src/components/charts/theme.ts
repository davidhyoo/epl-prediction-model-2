/** Literal colour palette for Recharts (SVG attributes can't use CSS vars).
 *  Mid-tone hues chosen to read well in both light and dark themes. */
export const CHART = {
  primary: "hsl(255 85% 66%)",
  info: "hsl(190 90% 48%)",
  amber: "hsl(35 92% 52%)",
  violet: "hsl(280 70% 66%)",
  rose: "hsl(322 82% 62%)",
  slate: "hsl(220 14% 55%)",
  grid: "hsl(220 14% 60% / 0.22)",
  axis: "hsl(220 12% 50%)",
};

export const CHART_SERIES = [
  CHART.primary,
  CHART.info,
  CHART.amber,
  CHART.violet,
  CHART.rose,
];

/** Well-separated qualitative hues for the title-race chart (up to ~10 lines
 *  that must stay distinguishable regardless of the clubs' brand colours). */
export const RACE_COLORS = [
  "hsl(255 85% 66%)", // indigo
  "hsl(190 90% 45%)", // cyan
  "hsl(35 92% 52%)", // amber
  "hsl(322 82% 60%)", // pink
  "hsl(142 66% 45%)", // green
  "hsl(280 70% 66%)", // violet
  "hsl(12 82% 58%)", // red-orange
  "hsl(210 90% 58%)", // blue
  "hsl(48 90% 50%)", // gold
  "hsl(168 72% 42%)", // teal
];

/** Inline style for Recharts <Tooltip contentStyle> — uses CSS vars (valid here). */
export const tooltipContentStyle: React.CSSProperties = {
  background: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  color: "hsl(var(--popover-foreground))",
  fontSize: "12px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
};

export const tooltipItemStyle: React.CSSProperties = {
  color: "hsl(var(--popover-foreground))",
};

export const tooltipLabelStyle: React.CSSProperties = {
  color: "hsl(var(--muted-foreground))",
  fontWeight: 600,
  marginBottom: 2,
};

/** Recharts v3 Tooltip formatter value type (may be a number, string, array or undefined). */
export type ChartValue = number | string | ReadonlyArray<number | string> | undefined;

/** Coerce a Recharts tooltip value to a number for formatting. */
export function toNum(v: ChartValue): number {
  if (v == null) return 0;
  return Array.isArray(v) ? Number(v[0]) : Number(v);
}
