import { spawn } from "node:child_process";
import { NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

// This route shells out to the Python refresh script, so it must run on the
// Node.js runtime (not the Edge runtime) and must never be statically cached.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Refreshing the data runs a local Python process (`ml/club_refresh.py`) that
 * hits public, key-less data sources (openfootball, football-data.co.uk,
 * Wikipedia/Wikimedia Commons) and rebuilds `public/data/**`. Executing a
 * child process from a web request is only safe on a trusted machine, so it is
 * **disabled by default in production**. It is enabled automatically in local
 * development, and can be explicitly enabled anywhere with `ALLOW_DATA_REFRESH=1`.
 */
function refreshEnabled(): boolean {
  return process.env.NODE_ENV !== "production" || process.env.ALLOW_DATA_REFRESH === "1";
}

// Module-level guard so two clicks can't launch two overlapping pipelines.
let running = false;

const REFRESH_TIMEOUT_MS = 12 * 60 * 1000; // stats fetch + full pipeline

export async function POST(request: Request) {
  if (!refreshEnabled()) {
    return NextResponse.json(
      {
        ok: false,
        error:
          "In-app refresh is disabled in this environment. Run `npm run data:fetch` " +
          "(python ml/club_refresh.py) locally, or set ALLOW_DATA_REFRESH=1 to enable it.",
      },
      { status: 403 },
    );
  }
  if (running) {
    return NextResponse.json(
      { ok: false, error: "A data refresh is already in progress. Please wait for it to finish." },
      { status: 409 },
    );
  }

  // `?mode=offline` rebuilds from the committed caches without any network calls;
  // the default pulls the latest results + scorers first. `?mode=squads` also
  // refreshes rosters + headshots (slow — several minutes).
  const mode = new URL(request.url).searchParams.get("mode");
  const args = ["ml/club_refresh.py"];
  if (mode === "offline") args.push("--offline");
  if (mode === "squads") args.push("--squads");

  const cwd = process.cwd();

  running = true;
  const startedAt = Date.now();
  try {
    const python = await resolvePython();
    if (!python) {
      return NextResponse.json(
        {
          ok: false,
          error:
            "Could not find a Python interpreter. Install Python 3, ensure it is on PATH " +
            "(tried python3, python and the Windows `py` launcher), or set the PYTHON_BIN " +
            "environment variable to its full path.",
        },
        { status: 500 },
      );
    }
    const result = await runProcess(python, args, cwd, REFRESH_TIMEOUT_MS);
    const tail = result.output.split(/\r?\n/).filter(Boolean).slice(-12);
    if (result.code !== 0) {
      return NextResponse.json(
        {
          ok: false,
          error: `club_refresh.py exited with code ${result.code}`,
          durationMs: Date.now() - startedAt,
          log: tail,
        },
        { status: 500 },
      );
    }
    // The pipeline rewrote public/data/*.json. Purge the full route cache (every
    // page under the root layout) so statically-prerendered pages re-read the
    // new data on the next request — this is what makes the in-app refresh work
    // "live" even in a production build, not just in `next dev`.
    revalidatePath("/", "layout");
    return NextResponse.json({
      ok: true,
      durationMs: Date.now() - startedAt,
      mode: mode === "offline" ? "offline" : "live",
      log: tail,
    });
  } catch (err) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  } finally {
    running = false;
  }
}

function runProcess(
  cmd: string,
  args: string[],
  cwd: string,
  timeoutMs: number,
): Promise<{ code: number | null; output: string }> {
  return new Promise((resolve, reject) => {
    // The command + args are constants defined in this repo; no user input is
    // ever interpolated into them, and shell interpretation is disabled.
    const child = spawn(cmd, args, {
      cwd,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      shell: false,
    });

    let output = "";
    const onData = (buf: Buffer) => {
      output += buf.toString("utf-8");
      if (output.length > 200_000) output = output.slice(-200_000); // cap memory
    };
    child.stdout.on("data", onData);
    child.stderr.on("data", onData);

    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`refresh timed out after ${Math.round(timeoutMs / 1000)}s`));
    }, timeoutMs);

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(
        err.message.includes("ENOENT")
          ? new Error(
              `Could not launch Python ("${cmd}"). Ensure Python is installed and on PATH, ` +
                `or set the PYTHON_BIN environment variable. (${err.message})`,
            )
          : err,
      );
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, output });
    });
  });
}

/**
 * Find a usable Python 3 interpreter. Different machines expose Python under
 * different names (`python3` on macOS/Linux, `py` launcher on Windows), so we
 * probe a prioritised list — `PYTHON_BIN`/`PYTHON` first — and return the first
 * one that responds to `--version`. This is what lets the in-app refresh button
 * work on a fresh clone without any per-machine configuration.
 */
async function resolvePython(): Promise<string | null> {
  const candidates = [
    process.env.PYTHON_BIN,
    process.env.PYTHON,
    "python3",
    "python",
    "py",
  ].filter((c): c is string => Boolean(c && c.trim()));

  for (const cmd of candidates) {
    if (await canRun(cmd)) return cmd;
  }
  return null;
}

function canRun(cmd: string): Promise<boolean> {
  return new Promise((resolve) => {
    const child = spawn(cmd, ["--version"], { shell: false });
    const done = (ok: boolean) => resolve(ok);
    child.on("error", () => done(false));
    child.on("close", (code) => done(code === 0));
    // Guard against a hung probe.
    setTimeout(() => {
      child.kill("SIGKILL");
      done(false);
    }, 5000).unref?.();
  });
}
