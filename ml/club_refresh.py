"""
club_refresh.py  —  offline-friendly source refresh (no API keys, no paid APIs)
===============================================================================
Downloads the free / openly-licensed source files the club-football pipeline is
built on, for every (league, season) combination, then rebuilds the app data so
``public/data/{league}/{season}/*.json`` reflects the latest real results.

    python ml/club_refresh.py                    # fetch all sources, rebuild all
    python ml/club_refresh.py --offline          # skip downloads; rebuild from cache
    python ml/club_refresh.py --no-pipeline      # only refresh the source caches
    python ml/club_refresh.py --league epl       # restrict to one league
    python ml/club_refresh.py --season 2025-26   # restrict to one season
    python ml/club_refresh.py --squads           # also refresh Wikipedia squads + headshots

Design goals (identical philosophy to the World-Cup agent's refresh):
  * **No secrets / no paid APIs** — plain HTTPS to public GitHub raw URLs
    (openfootball, CC0) and football-data.co.uk (free), stdlib only.
  * **Never corrupts the cache** — each file is downloaded to a temp path, sanity
    checked (size + expected marker) and only then atomically swapped in.
  * **Offline fallback** — a failed download keeps the committed cache and prints
    a visible WARNING; the pipeline still rebuilds end-to-end from caches.
  * **Rename / new-season resilient** — the openfootball 2026-27 fixtures start
    empty and gain results as the season is played; football-data.co.uk only
    publishes a division CSV once the season kicks off, so a missing football-data
    file for an unstarted season is expected and never fatal.

Sources
  * openfootball/england (1-premierleague.txt) and openfootball/espana
    (1-liga.txt) — CC0 fixtures, results and (2025-26+) inline goalscorers.
  * football-data.co.uk mmz4281/{yyyy}/{E0|SP1}.csv — free per-match stats
    (shots, shots on target, corners, fouls, cards) + closing market odds.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from leagues import COMBOS, LEAGUES, SEASONS, SOURCE_DIR  # noqa: E402

RAW = "https://raw.githubusercontent.com"
FD = "https://www.football-data.co.uk/mmz4281"

# football-data.co.uk season codes used to TRAIN the models and grow Elo.
# These are strictly-past seasons relative to the target seasons (2025-26 /
# 2026-27), so training never sees a match it will later be evaluated on.
HISTORY_FD = ["2021", "2122", "2223", "2324", "2425"]

_UA = ("soccer-agent/1.0 (portfolio project; "
       "https://github.com/davidhyoo/epl-prediction-model-2)")
_TIMEOUT = 45


def source_dir(league_id: str, season_id: str) -> str:
    d = os.path.join(SOURCE_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return d


def history_dir(league_id: str) -> str:
    d = os.path.join(SOURCE_DIR, league_id, "history")
    os.makedirs(d, exist_ok=True)
    return d


def _fd_yyyy(season_id: str) -> str:
    """'2025-26' -> '2526' (football-data.co.uk season code)."""
    start = SEASONS[season_id].start_year % 100
    return f"{start:02d}{(start + 1) % 100:02d}"


def openfootball_urls(league_id: str, season_id: str) -> list[str]:
    lg = LEAGUES[league_id]
    return [f"{RAW}/openfootball/{lg.of_repo}/master/{season_id}/{lg.of_file}"]


def football_data_url(league_id: str, season_id: str) -> str:
    lg = LEAGUES[league_id]
    return f"{FD}/{_fd_yyyy(season_id)}/{lg.fd_code}.csv"


def _fetch_one(urls: list[str], dest: str, min_bytes: int, marker: str,
               required: bool) -> tuple[bool, str]:
    """Download the first working candidate into ``dest`` atomically.

    Validates (size + marker) BEFORE touching the real file, so a 404 / error
    page can never corrupt the committed cache. Returns (updated, status).
    """
    tmp = dest + ".tmp"
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            code = getattr(getattr(exc, "code", None), "__str__", lambda: "")()
            print(f"    . {os.path.basename(dest)}: {exc.__class__.__name__} {code} — trying next")
            continue
        if len(data) < min_bytes:
            print(f"    . too small ({len(data)} < {min_bytes}) — trying next")
            continue
        head = data[:4096].decode("utf-8", "replace")
        if marker and marker not in head:
            print(f"    . missing marker {marker!r} — trying next")
            continue
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)
        print(f"    ok {len(data):>8,} bytes  {os.path.basename(dest)}")
        return True, "updated"

    if os.path.exists(dest):
        return False, "kept"
    if required:
        raise SystemExit(
            f"FATAL: {os.path.basename(dest)} could not be downloaded and no "
            f"cached copy exists at {dest}. Connect to the internet once to seed it."
        )
    return False, "absent"


def refresh_combo(league_id: str, season_id: str) -> dict:
    """Fetch openfootball + football-data for one (league, season)."""
    d = source_dir(league_id, season_id)
    print(f"- {league_id} {season_id}")
    stats = {"updated": 0, "kept": 0, "absent": 0}

    # openfootball is required (fixtures always exist for a scheduled season).
    up, st = _fetch_one(openfootball_urls(league_id, season_id),
                        os.path.join(d, "openfootball.txt"),
                        min_bytes=1_500, marker="", required=True)
    stats["updated" if up else st] += 1

    # The Champions League has no football-data / FPL feed — its schedule,
    # results and knockout bracket all come from the single openfootball file
    # above, so we're done for a tournament.
    if LEAGUES[league_id].format == "tournament":
        return stats

    # football-data is optional: a not-yet-started season has no stats CSV yet.
    up, st = _fetch_one([football_data_url(league_id, season_id)],
                        os.path.join(d, "footballdata.csv"),
                        min_bytes=2_000, marker="Div,Date", required=False)
    if up:
        stats["updated"] += 1
    else:
        stats[st] += 1

    # FPL per-player assists / minutes / cards (Premier League only; free +
    # key-less). Optional: a not-yet-started season has no snapshot upstream.
    try:
        import club_fpl
        up, st = club_fpl.download(league_id, season_id)
        if st in stats:
            stats["updated" if up else st] += 1
    except Exception as exc:  # noqa: BLE001 - keep the committed cache
        print(f"    ! fpl fetch failed ({exc.__class__.__name__}: {exc}) — keeping cache")
    return stats


# Past Champions-League editions used to train the models + grow Elo. These are
# strictly earlier than the shipped seasons (2024-25 / 2025-26), so training
# never sees a match it will later be evaluated on. They almost never change, but
# refreshing them keeps a fresh clone self-healing if a history file goes missing.
UCL_HISTORY_SEASONS = [
    "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17", "2017-18",
    "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24",
]


def refresh_history_ucl(league_id: str) -> dict:
    """Fetch the past-edition openfootball ``cl.txt`` files (results only) that
    train the Champions-League models, storing each as ``history/{season}.txt``."""
    lg = LEAGUES[league_id]
    d = history_dir(league_id)
    stats = {"updated": 0, "kept": 0, "absent": 0}
    print(f"- {league_id} history ({len(UCL_HISTORY_SEASONS)} editions)")
    for season in UCL_HISTORY_SEASONS:
        url = f"{RAW}/openfootball/{lg.of_repo}/master/{season}/{lg.of_file}"
        dest = os.path.join(d, f"{season}.txt")
        up, st = _fetch_one([url], dest, min_bytes=1_500, marker="", required=False)
        stats["updated" if up else st] += 1
    return stats


def refresh_history(league_id: str) -> dict:
    """Fetch the past-season football-data CSVs used for training + Elo."""
    if LEAGUES[league_id].format == "tournament":
        return refresh_history_ucl(league_id)

    lg = LEAGUES[league_id]
    d = history_dir(league_id)
    stats = {"updated": 0, "kept": 0, "absent": 0}
    print(f"- {league_id} history ({len(HISTORY_FD)} seasons)")
    for code in HISTORY_FD:
        url = f"{FD}/{code}/{lg.fd_code}.csv"
        dest = os.path.join(d, f"{code}.csv")
        up, st = _fetch_one([url], dest, min_bytes=2_000, marker="Div,Date",
                            required=False)
        stats["updated" if up else st] += 1
    return stats


def refresh_sources(combos) -> tuple[int, int]:
    updated = kept = 0
    seen_history: set[str] = set()
    for lg, sn in combos:
        s = refresh_combo(lg, sn)
        updated += s["updated"]
        kept += s["kept"]
        if lg not in seen_history:
            seen_history.add(lg)
            h = refresh_history(lg)
            updated += h["updated"]
            kept += h["kept"]
    return updated, kept


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Refresh club-football sources and rebuild")
    ap.add_argument("--offline", action="store_true",
                    help="skip downloads; rebuild from the committed caches")
    ap.add_argument("--no-pipeline", action="store_true",
                    help="only refresh the source caches, don't rebuild")
    ap.add_argument("--league", choices=list(LEAGUES), default=None)
    ap.add_argument("--season", choices=list(SEASONS), default=None)
    ap.add_argument("--squads", action="store_true",
                    help="also refresh real squads + free headshots (Wikipedia / Commons)")
    ap.add_argument("--squads-no-images", action="store_true",
                    help="with --squads, refresh squad facts only (skip headshot downloads)")
    ap.add_argument("--crests", action="store_true",
                    help="also refresh club crest URLs (TheSportsDB / football-data CDNs)")
    args = ap.parse_args(argv)

    combos = [(lg, sn) for lg, sn in COMBOS
              if (args.league in (None, lg)) and (args.season in (None, sn))]

    t0 = time.time()
    if args.offline:
        print("[refresh] --offline: skipping downloads, using committed caches")
        missing = [f"{lg}/{sn}" for lg, sn in combos
                   if not os.path.exists(os.path.join(SOURCE_DIR, lg, sn, "openfootball.txt"))]
        if missing:
            raise SystemExit(f"FATAL: offline but caches missing: {missing}")
    else:
        print(f"[refresh] fetching sources for {len(combos)} league/season combo(s)")
        updated, kept = refresh_sources(combos)
        print(f"[refresh] {updated} file(s) updated, {kept} kept from cache")
        if kept:
            print(f"[refresh] WARNING: {kept} source file(s) could not be updated and "
                  "were served from the local cache — some results may be stale. Check "
                  "your network connection or the upstream source layout.")

    # Squads + headshots are opt-in (hit the MediaWiki APIs; change infrequently).
    if args.squads and not args.offline:
        mode = "squads only" if args.squads_no_images else "squads + headshots"
        print(f"[refresh] refreshing real squads ({mode}) from Wikipedia / Wikimedia Commons")
        try:
            import club_fetch_squads
            fargv = []
            if args.squads_no_images:
                fargv.append("--no-images")
            if args.league:
                fargv += ["--league", args.league]
            club_fetch_squads.main(fargv)
        except Exception as exc:  # noqa: BLE001 - keep the committed squad cache
            print(f"  ! squad refresh failed ({exc.__class__.__name__}: {exc}) — keeping cache")
    elif args.squads and args.offline:
        print("[refresh] --offline: skipping squad refresh, using committed cache")

    # Club crests are static config (a bundled URL map), so refreshing them is
    # opt-in and rebuilds src/lib/crests.json for the next frontend build.
    if args.crests and not args.offline:
        print("[refresh] refreshing club crest URLs (TheSportsDB / football-data)")
        try:
            import club_crests
            club_crests.build([args.league] if args.league else None)
        except Exception as exc:  # noqa: BLE001 - keep the committed crest map
            print(f"  ! crest refresh failed ({exc.__class__.__name__}: {exc}) — keeping cache")
    elif args.crests and args.offline:
        print("[refresh] --offline: skipping crest refresh, using committed cache")

    if args.no_pipeline:
        print(f"[refresh] done in {time.time() - t0:0.1f}s (sources only)")
        return

    import club_pipeline
    club_pipeline.run(combos)
    print(f"[refresh] all done in {time.time() - t0:0.1f}s")


if __name__ == "__main__":
    main()
