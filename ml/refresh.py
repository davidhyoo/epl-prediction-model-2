"""
refresh.py  —  offline-friendly data refresh (no API keys, no paid services)
============================================================================
Re-downloads the openly-licensed (CC0) source files the pipeline is built on,
then re-runs the full ML pipeline so ``public/data/*.json`` reflects the latest
real results.

    python ml/refresh.py                 # fetch sources, then run the pipeline
    python ml/refresh.py --offline       # skip fetching; rebuild from caches
    python ml/refresh.py --no-pipeline   # only refresh the source caches
    python ml/refresh.py --players       # also refresh real squads + headshots
    python ml/refresh.py --from features # (passed through to pipeline)

Design goals
------------
* **No secrets / no paid APIs.** Everything is fetched over plain HTTPS from
  public GitHub raw URLs (and, with ``--players``, the public MediaWiki APIs)
  with the Python standard library only.
* **Never corrupts the cache.** Each file is downloaded to a temp path, sanity
  checked (size + expected header/marker), and only then atomically swapped in.
* **Offline fallback.** If a download fails (no network, GitHub down, rate
  limited) the previously committed cache in ``data/source/`` is kept and a
  warning is printed. The pipeline still runs end-to-end from the caches, so the
  app is always reproducible offline.

Sources (all public domain / CC0 / free-licensed — see README "Data Sources"):
* martj42/international_results — men's international results 1872→present.
* openfootball/worldcup ``2026--canada-usa-mexico`` — the real 2026 draw,
  fixtures, results and knockout bracket.
* English Wikipedia 2026 World Cup **match articles** (official FIFA match
  reports) — real per-player tournament stats (appearances, minutes, goals,
  cards, GK clean sheets / goals conceded). Refreshed by default every run via
  ``ml/fetch_stats.py`` (public MediaWiki API, no key). Assists / xG / advanced
  metrics are not published in any free source and are intentionally omitted.
* (opt-in, ``--players``) English Wikipedia squad templates + Wikimedia Commons
  free-licensed headshots — see ``ml/fetch_players.py``.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request

# Import the pipeline package regardless of how this file is invoked
# (``python ml/refresh.py`` or ``python -m ml.refresh``).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA_DIR  # noqa: E402

SOURCE_DIR = os.path.join(DATA_DIR, "source")

RAW = "https://raw.githubusercontent.com"

# The openfootball/worldcup 2026 dataset lives in a per-tournament directory whose
# name has changed over time (it was renamed from ``2026--usa`` to
# ``2026--canada-usa-mexico``). To stay resilient to further renames we try each
# candidate directory in order (newest first) and use the first that resolves.
OPENFOOTBALL_DIRS = ["2026--canada-usa-mexico", "2026--usa"]


def _openfootball(filename: str) -> list[str]:
    """Candidate raw URLs for an openfootball 2026 file, newest dir first."""
    return [f"{RAW}/openfootball/worldcup/master/{d}/{filename}" for d in OPENFOOTBALL_DIRS]


# (urls, local filename, minimum plausible size in bytes, required marker)
# ``urls`` is a list of candidate URLs tried in order (the first that downloads a
# valid file wins). ``marker`` is a short string that MUST appear in a healthy
# download — a cheap guard against fetching an error page / truncated file.
SOURCES: list[tuple[list[str], str, int, str]] = [
    (
        [f"{RAW}/martj42/international_results/master/results.csv"],
        "martj42_results.csv",
        1_000_000,
        "date,home_team,away_team",
    ),
    (
        [f"{RAW}/martj42/international_results/master/shootouts.csv"],
        "martj42_shootouts.csv",
        5_000,
        "date,home_team,away_team,winner",
    ),
    (
        _openfootball("cup.txt"),
        "openfootball_cup.txt",
        3_000,
        "Group A",
    ),
    (
        _openfootball("cup_finals.txt"),
        "openfootball_cup_finals.txt",
        1_000,
        "Round of 32",
    ),
    (
        # The stadiums file was renamed ``cup_stadiums.csv`` -> ``stadiums.csv``;
        # try both so either repo layout works.
        _openfootball("stadiums.csv") + _openfootball("cup_stadiums.csv"),
        "openfootball_cup_stadiums.csv",
        500,
        "",
    ),
]

_UA = "worldcup-2026-dashboard/1.0 (+https://github.com; offline-refresh script)"
_TIMEOUT = 30


def _fetch_one(urls: list[str], dest: str, min_bytes: int, marker: str) -> bool:
    """Download the first working ``urls`` candidate into ``dest`` atomically.

    Each candidate is validated (size + expected marker) BEFORE the real file is
    touched, so a 404 / error page / truncated response can never corrupt the
    committed cache. On total failure the existing ``dest`` is left untouched and
    ``False`` is returned.
    """
    tmp = dest + ".tmp"
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"  . {url.rsplit('/master/', 1)[-1]}: {exc.__class__.__name__} — trying next")
            continue

        # Validate BEFORE touching the real file so a bad response can't corrupt it.
        if len(data) < min_bytes:
            print(f"  . too small ({len(data)} < {min_bytes} bytes) — trying next")
            continue
        text_head = data[:4096].decode("utf-8", "replace")
        if marker and marker not in text_head:
            print(f"  . missing marker {marker!r} — trying next")
            continue

        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)  # atomic swap on the same filesystem
        print(f"  ok {len(data):>9,} bytes  <- {url.rsplit('/master/', 1)[-1]}")
        return True

    print("  ! all sources failed — keeping cache")
    return False


def refresh_sources() -> tuple[int, int]:
    """Fetch every source. Returns (updated, kept_from_cache)."""
    os.makedirs(SOURCE_DIR, exist_ok=True)
    updated = kept = 0
    for urls, name, min_bytes, marker in SOURCES:
        dest = os.path.join(SOURCE_DIR, name)
        print(f"- {name}")
        if _fetch_one(urls, dest, min_bytes, marker):
            updated += 1
        else:
            if os.path.exists(dest):
                kept += 1
            else:
                raise SystemExit(
                    f"FATAL: {name} could not be downloaded and no cached copy "
                    f"exists at {dest}. Connect to the internet once to seed it."
                )
    return updated, kept


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh CC0 source data and rebuild")
    ap.add_argument("--offline", action="store_true",
                    help="skip downloads; rebuild from the committed caches")
    ap.add_argument("--no-pipeline", action="store_true",
                    help="only refresh the source caches, don't run the pipeline")
    ap.add_argument("--players", action="store_true",
                    help="also refresh real squads + free headshots (Wikipedia / "
                         "Wikimedia Commons) before rebuilding — slower, needs network")
    ap.add_argument("--players-no-images", action="store_true",
                    help="with --players, refresh squad facts only (skip headshot downloads)")
    ap.add_argument("--from", dest="start", default=None,
                    help="resume the pipeline from this stage")
    args = ap.parse_args()

    t0 = time.time()
    if args.offline:
        print("[refresh] --offline: skipping downloads, using committed caches")
        missing = [n for _, n, _, _ in SOURCES
                   if not os.path.exists(os.path.join(SOURCE_DIR, n))]
        if missing:
            raise SystemExit(f"FATAL: offline but caches missing: {missing}")
    else:
        print(f"[refresh] fetching {len(SOURCES)} CC0 source files -> {SOURCE_DIR}")
        updated, kept = refresh_sources()
        print(f"[refresh] {updated} updated, {kept} kept from cache")
        if kept:
            print(f"[refresh] WARNING: {kept}/{len(SOURCES)} source file(s) could not be "
                  "updated and were served from the local cache — some results may be "
                  "stale. Check your network connection or the upstream source layout.")

    # Real per-player World Cup statistics are parsed from the public English
    # Wikipedia match articles (which transcribe the official FIFA match reports).
    # They change after *every* match, so — unlike squads — they are refreshed by
    # default on each run. A failure here never blocks the rebuild: the committed
    # ``data/source/player_stats_wikipedia.json`` cache is kept and reused.
    if not args.offline:
        print("[refresh] refreshing real player match stats (Wikipedia FIFA match reports)")
        try:
            import fetch_stats
            fetch_stats.main([])
        except Exception as exc:  # noqa: BLE001 - keep the committed stats cache
            print(f"  ! stats refresh failed ({exc.__class__.__name__}: {exc}) — keeping cache")
    else:
        print("[refresh] --offline: skipping player-stats refresh, using committed cache")

    # Real squads + free headshots are opt-in: they hit the public MediaWiki APIs
    # (slower, network-bound) and change infrequently, so the committed cache is
    # used by default. A failure here never blocks the rebuild — the pipeline
    # falls back to the previously cached squads.
    if args.players and not args.offline:
        mode = "squads only" if args.players_no_images else "squads + headshots"
        print(f"[refresh] refreshing real players ({mode}) from Wikipedia / Wikimedia Commons")
        try:
            import fetch_players
            fetch_players.main(["--no-images"] if args.players_no_images else [])
        except Exception as exc:  # noqa: BLE001 - keep the committed squad cache
            print(f"  ! player refresh failed ({exc.__class__.__name__}: {exc}) — keeping cache")
    elif args.players and args.offline:
        print("[refresh] --offline given: skipping player refresh, using committed squad cache")

    if args.no_pipeline:
        print(f"[refresh] done in {time.time() - t0:0.1f}s (sources only)")
        return

    # Run the pipeline in-process so it shares the same interpreter/env.
    import pipeline
    pipeline.run(args.start)
    print(f"[refresh] all done in {time.time() - t0:0.1f}s")


if __name__ == "__main__":
    main()
