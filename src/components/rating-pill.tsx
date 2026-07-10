import { cn } from "@/lib/utils";

/** A colour-graded rating chip (0-100). Higher = greener. */
export function RatingPill({ rating, className }: { rating: number; className?: string }) {
  let tone = "bg-muted text-muted-foreground";
  if (rating >= 85) tone = "bg-primary/15 text-primary";
  else if (rating >= 78) tone = "bg-info/15 text-info";
  else if (rating >= 70) tone = "bg-success/15 text-success";
  else if (rating >= 62) tone = "bg-warning/15 text-warning";

  return (
    <span
      className={cn(
        "inline-flex min-w-9 items-center justify-center rounded-md px-1.5 py-0.5 text-sm font-semibold tabular-nums",
        tone,
        className,
      )}
    >
      {rating}
    </span>
  );
}
