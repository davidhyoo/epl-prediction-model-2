"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Check, AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { formatDateTime, formatMatchDate, formatRelative } from "@/lib/format";

type State = "idle" | "running" | "done" | "error";

/**
 * Shared client-side logic for the local data refresh. Triggers the Python
 * pipeline (`ml/club_refresh.py`) via `POST /api/refresh`, which pulls the
 * latest completed results + scorers from public open data and rebuilds every
 * cached JSON, then re-fetches the server components so the whole dashboard
 * reflects the new data without a code change or a manual restart.
 */
function useDataRefresh() {
  const router = useRouter();
  const [state, setState] = React.useState<State>("idle");
  const [message, setMessage] = React.useState<string>("");
  const runningRef = React.useRef(false);

  const refresh = React.useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    setState("running");
    setMessage(
      "Pulling the latest results & scorers, then rebuilding predictions… (this can take ~1-2 min)",
    );
    try {
      const res = await fetch("/api/refresh", { method: "POST" });
      const data = (await res.json()) as {
        ok: boolean;
        error?: string;
        durationMs?: number;
      };
      if (!res.ok || !data.ok) {
        setState("error");
        setMessage(data.error ?? `Refresh failed (HTTP ${res.status}).`);
        return;
      }
      const secs = data.durationMs ? Math.round(data.durationMs / 1000) : null;
      setState("done");
      setMessage(
        `Live data reloaded${secs != null ? ` in ${secs}s` : ""}. Everything is up to date.`,
      );
      // Re-fetch the server components so the new JSON is reflected everywhere.
      router.refresh();
      window.setTimeout(() => {
        setState("idle");
        setMessage("");
      }, 5000);
    } catch (err) {
      setState("error");
      setMessage(err instanceof Error ? err.message : "Refresh request failed.");
    } finally {
      runningRef.current = false;
    }
  }, [router]);

  const dismiss = React.useCallback(() => {
    setState("idle");
    setMessage("");
  }, []);

  return { state, message, refresh, dismiss };
}

/**
 * Full-width refresh button used on the Methodology page. Only rendered when the
 * server reports the endpoint is enabled (dev, or `ALLOW_DATA_REFRESH=1`).
 */
export function RefreshDataButton() {
  const { state, message, refresh } = useDataRefresh();

  return (
    <div className="flex flex-col items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={refresh}
        disabled={state === "running"}
        aria-busy={state === "running"}
      >
        <RefreshCw className={cn("size-4", state === "running" && "animate-spin")} />
        {state === "running" ? "Refreshing…" : "Refresh data"}
      </Button>
      {message && (
        <p
          className={cn(
            "flex max-w-md items-center gap-1.5 text-center text-xs",
            state === "error" ? "text-red-600 dark:text-red-400" : "text-muted-foreground",
          )}
        >
          {state === "done" && <Check className="size-3.5 shrink-0 text-emerald-500" />}
          {state === "error" && <AlertTriangle className="size-3.5 shrink-0" />}
          <span>{message}</span>
        </p>
      )}
    </div>
  );
}

/** Small fixed toast that reports the progress of a nav-triggered refresh. */
function RefreshToast({
  state,
  message,
  onDismiss,
}: {
  state: State;
  message: string;
  onDismiss: () => void;
}) {
  if (state === "idle" || !message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 bottom-4 z-[60] flex justify-center px-4"
    >
      <div
        className={cn(
          "pop-anim flex max-w-md items-center gap-2.5 rounded-lg border bg-popover px-4 py-3 text-sm text-popover-foreground shadow-lg",
          state === "error" ? "border-red-500/40" : "border-border",
        )}
      >
        {state === "running" && (
          <RefreshCw className="size-4 shrink-0 animate-spin text-primary" />
        )}
        {state === "done" && <Check className="size-4 shrink-0 text-emerald-500" />}
        {state === "error" && <AlertTriangle className="size-4 shrink-0 text-red-500" />}
        <span className="min-w-0">{message}</span>
        {(state === "done" || state === "error") && (
          <button
            onClick={onDismiss}
            aria-label="Dismiss"
            className="ml-1 shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Compact "data freshness" control for the top navigation. Shows how current the
 * loaded results are and — when the refresh endpoint is enabled — doubles as a
 * one-click button to pull the latest live results and rebuild the whole
 * dashboard from the backend, no code change required.
 */
export function DataFreshnessControl({
  asOf,
  generatedAt,
  enabled,
}: {
  asOf: string;
  generatedAt: string;
  enabled: boolean;
}) {
  const { state, message, refresh, dismiss } = useDataRefresh();
  const asOfShort = formatMatchDate(asOf).date; // deterministic (UTC) — no hydration mismatch

  const label =
    state === "running"
      ? "Refreshing…"
      : state === "done"
        ? "Up to date"
        : state === "error"
          ? "Retry"
          : `Data · ${asOfShort}`;

  const dotClass =
    state === "error" ? "bg-red-500" : state === "running" ? "bg-amber-500" : "bg-emerald-500";

  const tooltip = (
    <div className="space-y-1">
      <p className="font-medium text-popover-foreground">
        Results loaded through {formatDateTime(asOf)}
      </p>
      <p className="text-muted-foreground">Last rebuilt {formatRelative(generatedAt)}</p>
      <p className="text-muted-foreground">
        {enabled
          ? "Click to pull the latest live results & scorers and rebuild every prediction."
          : "Live refresh is disabled here. Run `npm run data:fetch` locally, or set ALLOW_DATA_REFRESH=1."}
      </p>
    </div>
  );

  const pill = (
    <span className="flex items-center gap-1.5">
      <span className="relative flex size-2 shrink-0">
        {state !== "running" && enabled && (
          <span
            className={cn(
              "absolute inline-flex size-full animate-ping rounded-full opacity-60",
              dotClass,
            )}
          />
        )}
        <span className={cn("relative inline-flex size-2 rounded-full", dotClass)} />
      </span>
      <RefreshCw className={cn("size-3.5", state === "running" && "animate-spin")} />
      <span className="hidden md:inline">{label}</span>
    </span>
  );

  const baseClass =
    "flex items-center rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground shadow-sm transition-colors";

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          {enabled ? (
            <button
              type="button"
              onClick={refresh}
              disabled={state === "running"}
              aria-busy={state === "running"}
              aria-label="Reload the latest live data"
              className={cn(
                baseClass,
                "hover:bg-secondary hover:text-foreground disabled:opacity-70",
              )}
            >
              {pill}
            </button>
          ) : (
            <span className={cn(baseClass, "cursor-default")}>{pill}</span>
          )}
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">{tooltip}</TooltipContent>
      </Tooltip>
      <RefreshToast state={state} message={message} onDismiss={dismiss} />
    </>
  );
}
