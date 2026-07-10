import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { pct } from "@/lib/format";

/** Maps a 0-1 confidence (max class probability) to a labelled badge. */
export function ConfidenceBadge({ value, showValue = true }: { value: number; showValue?: boolean }) {
  let label = "Low";
  let variant: React.ComponentProps<typeof Badge>["variant"] = "muted";
  if (value >= 0.6) {
    label = "Very high";
    variant = "success";
  } else if (value >= 0.5) {
    label = "High";
    variant = "info";
  } else if (value >= 0.42) {
    label = "Moderate";
    variant = "warning";
  }
  return (
    <Badge variant={variant} className="tabular-nums">
      {label}
      {showValue && ` · ${pct(value)}`}
    </Badge>
  );
}
