"""
pipeline.py  —  one-command orchestration of the full data/ML workflow.

    python ml/pipeline.py            # run every stage in order
    python ml/pipeline.py --from features   # resume from a stage

Stages: ingest -> transform -> features -> train -> predict -> evaluate
Each stage is a standalone module that reads/writes JSON on disk, so the
pipeline is fully reproducible and can be resumed at any point.
"""
from __future__ import annotations

import argparse
import importlib
import time

STAGES = ["ingest", "transform", "features", "train", "predict", "evaluate"]


def run(start: str | None = None) -> None:
    stages = STAGES[STAGES.index(start):] if start else STAGES
    t0 = time.time()
    for name in stages:
        print(f"\n=== [{name}] " + "=" * 48)
        stage = importlib.import_module(name)
        stage.main()
    print(f"\n[pipeline] done in {time.time() - t0:0.1f}s -> public/data/*.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="World Cup prediction pipeline")
    ap.add_argument("--from", dest="start", choices=STAGES, default=None,
                    help="resume from this stage")
    args = ap.parse_args()
    run(args.start)
