/** Literal colour palette for Recharts (SVG attributes can't use CSS vars).
 *  Mid-tone hues chosen to read well in both light and dark themes. */
export const CHART = {
  primary: "hsl(160 84% 39%)",
  info: "hsl(217 91% 60%)",
  amber: "hsl(38 92% 50%)",
  violet: "hsl(280 65% 62%)",
  rose: "hsl(340 82% 60%)",
  slate: "hsl(215 20% 55%)",
  grid: "hsl(215 20% 65% / 0.25)",
  axis: "hsl(215 16% 47%)",
};

export const CHART_SERIES = [
  CHART.primary,
  CHART.info,
  CHART.amber,
  CHART.violet,
  CHART.rose,
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
