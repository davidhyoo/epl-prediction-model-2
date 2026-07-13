"""
transform.py  —  Stage 2: validation, cleaning & transformation
================================================================
Validates the raw ingested data (schema + range + referential-integrity
checks) and writes cleaned, chronologically-consistent tables to
data/processed. Fails loudly if the raw data is malformed — this is the
"data validation" gate of the pipeline.

Match STATUS is derived from whether a real result exists (``played``), not a
fixed cutoff, so the pipeline naturally tracks the live tournament. Knockout
matches whose participants are not yet known (e.g. the final before the
semi-finals) are allowed to have null teams.
"""
from __future__ import annotations

import os
from collections import Counter

from common import (
    RAW_DIR, PROCESSED_DIR, GROUPS, read_json, write_json, write_json_pretty,
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
    """0 = home win, 1 = draw, 2 = away win (from the 90-minute score)."""
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
    gsizes = Counter(t["group"] for t in teams)
    for g in GROUPS:
        _require(gsizes.get(g) == 4, f"group {g} must have 4 teams, has {gsizes.get(g)}")
    for t in teams:
        _require(bool(t["iso2"]) and bool(t["name"]), f"team {t['code']} missing fields")
        _require(t["confederation"] in
                 {"UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"},
                 f"bad confederation for {t['code']}")

    # ---- History (real internationals; teams may be non-WC, keyed by name) -
    _require(len(history) > 1000, "history too small to train on")
    clean_history = []
    for m in history:
        _require(m["gh"] >= 0 and m["ga"] >= 0, f"negative goals in {m['id']}")
        clean_history.append({
            "id": m["id"], "date": m["date"], "home": m["home"], "away": m["away"],
            "home_code": m.get("home_code"), "away_code": m.get("away_code"),
            "home_adv": int(m["home_adv"]),
            "gh": int(m["gh"]), "ga": int(m["ga"]),
            "fh": int(m.get("fh", m["gh"])), "fa": int(m.get("fa", m["ga"])),
            "outcome": outcome(m["gh"], m["ga"]),
        })
    clean_history.sort(key=lambda m: m["date"])

    # ---- World Cup fixtures ----------------------------------------------
    stage_counts = Counter(m["stage"] for m in wc)
    for stage, n in EXPECTED_STAGES.items():
        _require(stage_counts.get(stage) == n,
                 f"stage {stage}: expected {n}, got {stage_counts.get(stage)}")
    clean_wc = []
    completed = 0
    for m in wc:
        for side in ("home", "away"):
            if m[side] is not None:
                _require(m[side] in codes, f"unknown team in WC match {m['id']}: {m[side]}")
        played = bool(m["played"]) if "played" in m else (m.get("gh") is not None)
        status = "completed" if played else "upcoming"
        if played:
            completed += 1
        clean_wc.append({
            "id": m["id"], "num": m.get("num"), "stage": m["stage"],
            "group": m.get("group"), "matchday": m.get("matchday"), "slot": m.get("slot"),
            "date": m["date"], "venue": m["venue"], "city": m["city"],
            "home": m["home"], "away": m["away"], "home_adv": int(m["home_adv"]),
            "gh": m["gh"], "ga": m["ga"], "fh": m.get("fh"), "fa": m.get("fa"),
            "pens": m.get("pens"), "winner": m.get("winner"),
            "feedHome": m.get("feedHome"), "feedAway": m.get("feedAway"),
            "knockout": 0 if m["stage"] == "group" else 1, "status": status,
            "outcome": outcome(m["gh"], m["ga"]) if played else None,
        })

    # ---- Squads -----------------------------------------------------------
    # Real Wikipedia squads are typically the full 26, but validation tolerates
    # variable sizes (short/generated fallbacks) so the pipeline never crashes on
    # a nation whose squad could not be fully parsed.
    _require(48 * 18 <= len(squads) <= 48 * 26,
             f"expected 864-1248 players (18-26 x48), got {len(squads)}")
    by_team = Counter(p["countryCode"] for p in squads)
    gk_by_team = Counter(p["countryCode"] for p in squads if p["position"] == "GK")
    for c in codes:
        _require(18 <= by_team[c] <= 26,
                 f"team {c} must have 18-26 players, has {by_team[c]}")
        _require(gk_by_team[c] >= 2,
                 f"team {c} must have >=2 goalkeepers, has {gk_by_team[c]}")
    for p in squads:
        _require(p["position"] in ("GK", "DEF", "MID", "FWD"),
                 f"player {p.get('id')} has bad position {p.get('position')!r}")
        _require(isinstance(p.get("real"), bool),
                 f"player {p.get('id')} missing boolean 'real' flag")

    # ---- Qualification ----------------------------------------------------
    _require(len(qual["ranked32"]) == 32, "expected 32 qualified teams")
    _require(len(set(qual["ranked32"])) == 32, "duplicate qualified teams")
    _require(len(qual.get("knockout", [])) == 32, "expected 32 knockout tree nodes")

    write_json_pretty(os.path.join(PROCESSED_DIR, "teams.json"), teams)
    write_json(os.path.join(PROCESSED_DIR, "history.json"), clean_history)  # large
    write_json_pretty(os.path.join(PROCESSED_DIR, "wc_matches.json"), clean_wc)
    write_json_pretty(os.path.join(PROCESSED_DIR, "squads.json"), squads)
    write_json_pretty(os.path.join(PROCESSED_DIR, "qualification.json"), qual)

    print(f"[transform] validated OK — history={len(clean_history)} "
          f"wc={len(clean_wc)} (completed={completed}, "
          f"upcoming={len(clean_wc) - completed})")


def main() -> None:
    validate_and_transform()


if __name__ == "__main__":
    main()
