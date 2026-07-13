"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Check, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type State = "idle" | "running" | "done" | "error";

/**
 * Triggers the local Python data refresh (`ml/refresh.py`) via `POST /api/refresh`,
 * which pulls the latest World Cup results + real player match stats and rebuilds
 * the cached JSON. Only rendered when the server reports the endpoint is enabled.
 */
export function RefreshDataButton() {
  const router = useRouter();
  const [state, setState] = React.useState<State>("idle");
  const [message, setMessage] = React.useState<string>("");

  async function refresh() {
    if (state === "running") return;
    setState("running");
    setMessage("Pulling latest results & player stats, then rebuilding predictions…");
    try {
      const res = await fetch("/api/refresh", { method: "POST" });
      const data = (await res.json()) as {
        ok: boolean;
        error?: string;
        durationMs?: number;
        log?: string[];
      };
      if (!res.ok || !data.ok) {
        setState("error");
        setMessage(data.error ?? `Refresh failed (HTTP ${res.status}).`);
        return;
      }
      const secs = data.durationMs ? Math.round(data.durationMs / 1000) : null;
      setState("done");
      setMessage(`Data refreshed${secs != null ? ` in ${secs}s` : ""}. Reloading…`);
      // Re-fetch the server components so the new JSON is reflected everywhere.
      router.refresh();
      setTimeout(() => {
        setState("idle");
        setMessage("");
      }, 4000);
    } catch (err) {
      setState("error");
      setMessage(err instanceof Error ? err.message : "Refresh request failed.");
    }
  }

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
