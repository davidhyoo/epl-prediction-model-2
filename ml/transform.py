"""
transform.py  —  Stage 2: validation, cleaning & transformation
================================================================
Validates the raw ingested data (schema + range + referential-integrity
checks) and writes cleaned, chronologically-consistent tables to
data/processed. Fails loudly if the raw data is malformed — this is the
"data validation" gate of the pipeline.
"""
from __future__ import annotations

import os
from datetime import datetime

from common import (
    RAW_DIR, PROCESSED_DIR, GROUPS, CUTOFF, read_json, write_json_pretty,
)

EXPECTED_STAGES = {
    "group": 72, "round-of-32": 16, "round-of-16": 8,
    "quarter-final": 4, "semi-final": 2, "third-place": 1, "final": 1,
}


class ValidationError(Exception):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)


def outcome(gh: int, ga: int) -> int:
    """0 = home win, 1 = draw, 2 = away win."""
    return 0 if gh > ga else (1 if gh == ga else 2)


def validate_and_transform() -> None:
    teams = read_json(os.path.join(RAW_DIR, "teams.json"))
    history = read_json(os.path.join(RAW_DIR, "history.json"))
    wc = read_json(os.path.join(RAW_DIR, "wc_matches.json"))
    squads = read_json(os.path.join(RAW_DIR, "squads.json"))
    qual = read_json(os.path.join(RAW_DIR, "qualification.json"))

    # ---- Teams ------------------------------------------------------------
    _require(len(teams) == 48, f"expected 48 teams, got {len(teams)}")
    codes = {t["code"] for t in teams}
    _require(len(codes) == 48, "duplicate team codes detected")
    from collections import Counter
    gsizes = Counter(t["group"] for t in teams)
    for g in GROUPS:
        _require(gsizes.get(g) == 4, f"group {g} must have 4 teams, has {gsizes.get(g)}")
    for t in teams:
        _require(t["iso2"] and t["name"], f"team {t['code']} missing fields")
        _require(t["confederation"] in
                 {"UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"},
                 f"bad confederation for {t['code']}")

    # ---- History ----------------------------------------------------------
    _require(len(history) > 1000, "history too small to train on")
    clean_history = []
    for m in history:
        _require(m["home"] in codes and m["away"] in codes,
                 f"unknown team in history match {m['id']}")
        _require(m["gh"] >= 0 and m["ga"] >= 0, f"negative goals in {m['id']}")
        clean_history.append({
            "id": m["id"], "date": m["date"], "home": m["home"], "away": m["away"],
            "home_adv": int(m["home_adv"]), "gh": int(m["gh"]), "ga": int(m["ga"]),
            "knockout": 0, "stage": "friendly", "outcome": outcome(m["gh"], m["ga"]),
        })
    clean_history.sort(key=lambda m: m["date"])

    # ---- World Cup fixtures ----------------------------------------------
    stage_counts = Counter(m["stage"] for m in wc)
    for stage, n in EXPECTED_STAGES.items():
        _require(stage_counts.get(stage) == n,
                 f"stage {stage}: expected {n}, got {stage_counts.get(stage)}")
    clean_wc = []
    for m in wc:
        _require(m["home"] in codes and m["away"] in codes,
                 f"unknown team in WC match {m['id']}")
        dt = datetime.fromisoformat(m["date"])
        knockout = 0 if m["stage"] == "group" else 1
        status = "completed" if dt <= CUTOFF else "upcoming"
        row = {
            "id": m["id"], "stage": m["stage"], "group": m.get("group"),
            "matchday": m.get("matchday"), "slot": m.get("slot"),
            "date": m["date"], "venue": m["venue"], "city": m["city"],
            "home": m["home"], "away": m["away"], "home_adv": int(m["home_adv"]),
            "gh": int(m["gh"]), "ga": int(m["ga"]), "pens": m.get("pens"),
            "winner": m.get("winner"), "knockout": knockout, "status": status,
            "outcome": outcome(m["gh"], m["ga"]) if status == "completed" else None,
        }
        clean_wc.append(row)

    # ---- Squads -----------------------------------------------------------
    _require(len(squads) == 48 * 26, f"expected 1248 players, got {len(squads)}")
    by_team = Counter(p["countryCode"] for p in squads)
    for c in codes:
        _require(by_team[c] == 26, f"team {c} must have 26 players, has {by_team[c]}")

    # ---- Qualification ----------------------------------------------------
    _require(len(qual["ranked32"]) == 32, "expected 32 qualified teams")
    _require(len(set(qual["ranked32"])) == 32, "duplicate qualified teams")

    write_json_pretty(os.path.join(PROCESSED_DIR, "teams.json"), teams)
    write_json_pretty(os.path.join(PROCESSED_DIR, "history.json"), clean_history)
    write_json_pretty(os.path.join(PROCESSED_DIR, "wc_matches.json"), clean_wc)
    write_json_pretty(os.path.join(PROCESSED_DIR, "squads.json"), squads)
    write_json_pretty(os.path.join(PROCESSED_DIR, "qualification.json"), qual)

    completed = sum(1 for m in clean_wc if m["status"] == "completed")
    print(f"[transform] validated OK — history={len(clean_history)} "
          f"wc={len(clean_wc)} (completed={completed}, "
          f"upcoming={len(clean_wc) - completed})")


def main() -> None:
    validate_and_transform()


if __name__ == "__main__":
    main()
