"""
club_pipeline.py  —  end-to-end orchestration
=============================================
Runs the whole club-football pipeline for a set of (league, season) combos and
writes the ``public/data`` bundle the frontend reads:

    ingest → features → train (once) → predict → simulate → evaluate → publish

Training is the only expensive, *reusable* step: the models learn from seasons
strictly earlier than each target season, so they don't change between refreshes
of an in-progress season. We therefore train only when a combo's models are
missing (or ``retrain=True``). Everything downstream re-runs every refresh so new
results immediately flow into standings, predictions, odds and the leaderboard.

Called by ``club_refresh.py`` (after the sources are downloaded) and runnable
standalone:

    python ml/club_pipeline.py                 # rebuild everything from cache
    python ml/club_pipeline.py --retrain       # force model re-fit
    python ml/club_pipeline.py --league epl --season 2025-26
"""
from __future__ import annotations

import argparse
import os

import club_evaluate as E
import club_train as T
from leagues import COMBOS, LEAGUES, MODELS_DIR, SEASONS


def _models_present(league_id: str, season_id: str) -> bool:
    d = os.path.join(MODELS_DIR, f"{league_id}-{season_id}")
    need = ["logreg.joblib", "forest.joblib", "xgb.joblib", "draw.joblib"]
    return all(os.path.exists(os.path.join(d, n)) for n in need)


def run(combos=None, retrain: bool = False) -> None:
    combos = combos or COMBOS
    print(f"[pipeline] building {len(combos)} combo(s)")
    for lg, sn in combos:
        if retrain or not _models_present(lg, sn):
            T.train_combo(lg, sn)
        else:
            print(f"  [train] {lg} {sn}: models present — skipping (use --retrain to refit)")
    E.main(combos)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Run the club-football pipeline")
    ap.add_argument("--retrain", action="store_true", help="force model re-fit")
    ap.add_argument("--league", choices=list(LEAGUES), default=None)
    ap.add_argument("--season", choices=list(SEASONS), default=None)
    args = ap.parse_args(argv)
    combos = [(lg, sn) for lg, sn in COMBOS
              if (args.league in (None, lg)) and (args.season in (None, sn))]
    run(combos, retrain=args.retrain)


if __name__ == "__main__":
    main()
