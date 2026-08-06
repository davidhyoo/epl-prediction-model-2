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
from leagues import LEAGUES, SEASONS, SOURCE_DIR, league_clubs, raw_path


def _fd_code_start_year(code: str) -> int:
    """football-data season code -> the season's starting calendar year."""
    return 2000 + int(code[:2])


def load_history(league_id: str) -> list[dict]:
    """All completed football-data rows we have for a league (past + current)."""
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
    for season_id in SEASONS:
        cur = os.path.join(SOURCE_DIR, league_id, season_id, "footballdata.csv")
        if os.path.exists(cur):
            with open(cur, "r", encoding="utf-8", errors="replace") as fh:
                for r in S.parse_fd_history(fh.read(), league_id):
                    r["startYear"] = SEASONS[season_id].start_year
                    rows.append(r)

    rows = [r for r in rows if r["date"]]
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
    for m in matches:
        if m["home"] not in valid_codes or m["away"] not in valid_codes:
            continue
        completed = m["homeGoals"] is not None
        m["id"] = f"{league_id}-{season_id}-{m['home']}-{m['away']}"
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
    for lg in LEAGUES:
        for sn in SEASONS:
            main(lg, sn)
