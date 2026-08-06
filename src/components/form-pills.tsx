import * as React from "react";
import { cn } from "@/lib/utils";
import type { FormResult } from "@/lib/types";

const STYLE: Record<FormResult, string> = {
  W: "bg-success/15 text-success ring-success/30",
  D: "bg-warning/15 text-warning ring-warning/30",
  L: "bg-destructive/15 text-destructive ring-destructive/30",
};

/** A compact row of the last-N results as coloured W/D/L chips. */
export function FormPills({
  form,
  className,
  size = "sm",
}: {
  form: FormResult[];
  className?: string;
  size?: "sm" | "md";
}) {
  const dim = size === "md" ? "size-6 text-xs" : "size-5 text-[10px]";
  if (!form.length) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {form.map((r, i) => (
        <span
          key={i}
          className={cn(
            "inline-flex items-center justify-center rounded-[5px] font-bold ring-1",
            dim,
            STYLE[r],
          )}
          title={r === "W" ? "Win" : r === "D" ? "Draw" : "Loss"}
        >
          {r}
        </span>
      ))}
    </div>
  );
}
