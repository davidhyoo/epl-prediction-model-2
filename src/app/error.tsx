"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RotateCcw, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

const RELOAD_GUARD_KEY = "dds-chunk-reloaded";

/** Errors thrown when the browser holds a stale build and a code-split chunk
 *  (route or lazy component) can no longer be fetched after a redeploy. */
function isChunkLoadError(error: Error): boolean {
  const name = error?.name ?? "";
  const msg = error?.message ?? "";
  return (
    name === "ChunkLoadError" ||
    /loading chunk [\d]+ failed/i.test(msg) ||
    /failed to fetch dynamically imported module/i.test(msg) ||
    /importing a module script failed/i.test(msg) ||
    /error loading dynamically imported module/i.test(msg)
  );
}

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // Decide once (in the initializer, not in an effect) whether this crash is a
  // stale-chunk load failure we can auto-recover from by reloading. The
  // sessionStorage guard prevents an infinite reload loop.
  const [recovering] = useState(() => {
    if (typeof window === "undefined") return false;
    if (isChunkLoadError(error) && !sessionStorage.getItem(RELOAD_GUARD_KEY)) {
      sessionStorage.setItem(RELOAD_GUARD_KEY, "1");
      return true;
    }
    return false;
  });

  useEffect(() => {
    console.error(error);
    if (recovering) {
      // Self-heal after a redeploy: hard-reload to pull the new build.
      window.location.reload();
    } else if (typeof window !== "undefined" && !isChunkLoadError(error)) {
      // The current build loaded fine — clear the guard so a future stale-chunk
      // error can auto-recover again.
      sessionStorage.removeItem(RELOAD_GUARD_KEY);
    }
  }, [error, recovering]);

  if (recovering) {
    return (
      <div className="container-page flex min-h-[60vh] flex-col items-center justify-center gap-4 py-16 text-center">
        <RefreshCw className="size-7 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Updating to the latest version…</p>
      </div>
    );
  }

  return (
    <div className="container-page flex min-h-[60vh] flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="size-7" />
      </div>
      <div className="space-y-1.5">
        <h1 className="text-2xl font-bold tracking-tight">Something went wrong</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          An unexpected error occurred while loading this view. If you just updated the app, a hard
          reload usually fixes it. If the cached data looks missing, re-run{" "}
          <code>npm run data:refresh</code> to regenerate it, then reload.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button onClick={reset} className="gap-2">
          <RotateCcw className="size-4" />
          Try again
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            if (typeof window !== "undefined") {
              sessionStorage.removeItem(RELOAD_GUARD_KEY);
              window.location.reload();
            }
          }}
          className="gap-2"
        >
          <RefreshCw className="size-4" />
          Reload page
        </Button>
      </div>
    </div>
  );
}
