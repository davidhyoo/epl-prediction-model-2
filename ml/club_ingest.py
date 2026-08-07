"""
club_ingest.py  —  stage 1: raw data ingestion
==============================================
Turns the cached source files into two in-memory structures per (league, season):

  * **training corpus** — completed matches from *strictly earlier* seasons
    (football-data.co.uk history CSVs), used to train the models and to grow Elo.
    Because it never contains a match from the target season, the models can
    predict the whole target season leakage-free.
  * **season matches** — the target season's fixtures/results/goalscorers
    (openfootball, merged with football-data stats where the season has started),
    each assigned a stable id and a completed/upcoming status.

Nothing here touches the network — it only reads ``data/source/**``.
"""
from __future__ import annotations

import glob
import json
import os

import club_sources as S
from leagues import (LEAGUES, SEASONS, SOURCE_DIR, league_clubs, league_seasons,
                     raw_path)


def _fd_code_start_year(code: str) -> int:
    """football-data season code -> the season's starting calendar year."""
    return 2000 + int(code[:2])


def load_history(league_id: str) -> list[dict]:
    """All completed match rows we have for a league (past + current), used to
    train the models and grow Elo.

    Domestic leagues use football-data.co.uk CSVs (rich per-match stats + odds).
    The Champions League has no football-data feed, so it walks the openfootball
    Champions-League back-catalogue instead (results only — plenty for Elo + the
    result-based features). See ``load_history_ucl``.
    """
    if LEAGUES[league_id].format == "tournament":
        return load_history_ucl(league_id)

    rows: list[dict] = []
    seen_files: set[str] = set()

    hist_glob = os.path.join(SOURCE_DIR, league_id, "history", "*.csv")
    for path in sorted(glob.glob(hist_glob)):
        code = os.path.splitext(os.path.basename(path))[0]
        seen_files.add(code)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for r in S.parse_fd_history(fh.read(), league_id):
                r["startYear"] = _fd_code_start_year(code)
                rows.append(r)

    # the current-season football-data file (if the season has started)
    for season_id in league_seasons(league_id):
        cur = os.path.join(SOURCE_DIR, league_id, season_id, "footballdata.csv")
        if os.path.exists(cur):
            with open(cur, "r", encoding="utf-8", errors="replace") as fh:
                for r in S.parse_fd_history(fh.read(), league_id):
                    r["startYear"] = SEASONS[season_id].start_year
                    rows.append(r)

    rows = [r for r in rows if r["date"]]
    rows.sort(key=lambda r: r["date"])
    return rows


def load_history_ucl(league_id: str) -> list[dict]:
    """Completed Champions-League matches from the openfootball back-catalogue,
    one row per finished game. Two sources are merged:

      * ``data/source/ucl/history/{season}.txt`` — older editions (training only).
      * ``data/source/ucl/{season}/openfootball.txt`` — the seasons the app ships
        (2024-25, 2025-26). These double as training data for *later* seasons;
        ``training_rows`` keeps things leakage-free via the ``startYear`` cutoff.

    Unknown historical clubs (long since out of Europe) keep contributing to the
    training set + Elo history via the loose name resolver's synthetic codes.
    """
    def _emit(text: str, start_year: int, out: list[dict]) -> None:
        for m in S.parse_openfootball_ucl(text, league_id, loose=True):
            if m["homeGoals"] is None or m["awayGoals"] is None or not m.get("date"):
                continue
            out.append({
                "date": m["date"], "home": m["home"], "away": m["away"],
                "homeGoals": m["homeGoals"], "awayGoals": m["awayGoals"],
                "startYear": start_year,
                "shotsOnTarget": {"home": None, "away": None},
                "marketOdds": None,
            })

    rows: list[dict] = []
    hist_glob = os.path.join(SOURCE_DIR, league_id, "history", "*.txt")
    for path in sorted(glob.glob(hist_glob)):
        stem = os.path.splitext(os.path.basename(path))[0]  # e.g. "2022-23"
        try:
            start_year = int(stem[:4])
        except ValueError:
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            _emit(fh.read(), start_year, rows)

    # the shipped seasons also serve as training data for later seasons
    for season_id in league_seasons(league_id):
        cur = os.path.join(SOURCE_DIR, league_id, season_id, "openfootball.txt")
        if os.path.exists(cur):
            with open(cur, "r", encoding="utf-8", errors="replace") as fh:
                _emit(fh.read(), SEASONS[season_id].start_year, rows)

    rows.sort(key=lambda r: r["date"])
    return rows


def training_rows(league_id: str, target_season: str) -> list[dict]:
    """Completed matches strictly before the target season (leakage-free)."""
    cutoff = SEASONS[target_season].start_year
    return [r for r in load_history(league_id) if r["startYear"] < cutoff]


def ingest_season(league_id: str, season_id: str) -> dict:
    """The target season's matches with ids + status, plus its club list."""
    matches = S.load_matches(league_id, season_id)
    valid_codes = {c.code for c in league_clubs(league_id)}

    out: list[dict] = []
    seen_ids: set[str] = set()
    for m in matches:
        if m["home"] not in valid_codes or m["away"] not in valid_codes:
            continue
        completed = m["homeGoals"] is not None
        mid = f"{league_id}-{season_id}-{m['home']}-{m['away']}"
        if mid in seen_ids:
            # tournaments can pair the same clubs more than once (two-legged ties,
            # or a league-phase meeting that recurs in the knockouts) — keep ids
            # unique by appending the round.
            mid = f"{mid}-r{m.get('round', 0)}"
        seen_ids.add(mid)
        m["id"] = mid
        m["status"] = "completed" if completed else "upcoming"
        out.append(m)

    # the set of clubs actually contesting this season (handles promotion/relegation)
    codes = sorted({m["home"] for m in out} | {m["away"] for m in out})

    return {"league": league_id, "season": season_id, "matches": out, "codes": codes}


def main(league_id: str, season_id: str) -> dict:
    data = ingest_season(league_id, season_id)
    corpus = training_rows(league_id, season_id)
    played = [m for m in data["matches"] if m["status"] == "completed"]
    out = raw_path(league_id, season_id, "ingest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"codes": data["codes"], "matchCount": len(data["matches"]),
                   "played": len(played), "trainingMatches": len(corpus)},
                  fh, ensure_ascii=False, indent=2)
    print(f"  [ingest] {league_id} {season_id}: {len(data['matches'])} matches "
          f"({len(played)} played), {len(data['codes'])} clubs, "
          f"{len(corpus)} training matches")
    return {"data": data, "corpus": corpus}


if __name__ == "__main__":
    from leagues import COMBOS
    for lg, sn in COMBOS:
        main(lg, sn)
