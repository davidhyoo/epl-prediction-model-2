# 🏆 World Cup 2026 — Prediction & Analytics Dashboard

A production-quality web app for exploring **2026 FIFA World Cup** results, fixtures,
predictions, countries, squads, players and model rankings — backed by a fully
reproducible, **offline-first** Python machine-learning pipeline.

> This is a **data-engineering & data-science portfolio project**. It deliberately
> surfaces the technical layer: a multi-model ensemble, feature importances,
> calibration diagnostics, a leakage-safe backtest, and a one-command data pipeline.

- **Frontend:** Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · Recharts
- **ML/Data:** Python · NumPy · pandas · scikit-learn · XGBoost
- **Models:** Elo baseline · Logistic Regression · Random Forest · XGBoost · Weighted Ensemble
- **Runs 100% offline** — no paid APIs, no secrets, no external services required.

---

## Table of contents

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Running the app](#running-the-app)
- [The data pipeline](#the-data-pipeline)
- [Data sources](#data-sources)
- [ML methodology](#ml-methodology)
- [Testing, linting & building](#testing-linting--building)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)
- [Original Build Prompt](#original-build-prompt)
- [Disclaimer](#disclaimer)

---

## Overview

The dashboard covers the real **48-team, 104-match** 2026 World Cup format (12 groups
of 4 → 72 group matches, then a 32-match knockout bracket from the Round of 32 to the
Final). Real fixtures and results drive the app's state; matches with no result yet are
treated as upcoming and predicted, so the dashboard tracks the tournament as it unfolds.

Predictions are produced by **five independent models**. Each model scores *every*
match **before** any real result is read; completed matches are then used **only** for
backtesting and re-ranking (see [Leakage prevention](#leakage-prevention--self-improvement)).
Championship odds come from a **20,000-run Monte Carlo** simulation of the remaining
knockout stage; eliminated teams are pinned to **0%**.

The tournament field, group draw, fixtures, results and knockout bracket are **real**,
sourced from openly-licensed **public-domain (CC0)** datasets and cached in the repo so
the whole thing is reproducible offline. The models train on **real men's international
results since 2002** (martj42, CC0). The **squads are real too** — current 26-player
rosters for all 48 nations are pulled from the maintained **English Wikipedia** squad
templates, with **free-licensed headshots from Wikimedia Commons** (1,047 of 1,248
players; the rest fall back to clean initials avatars). Only **per-player performance
statistics and ability ratings are model-generated** — no openly-licensed source for those
exists — and this is clearly flagged wherever it appears. See [Data sources](#data-sources).

Current snapshot (refresh any time with `python ml/refresh.py`):

| Metric | Value |
| --- | --- |
| Tournament | 2026 FIFA World Cup (USA · Canada · Mexico) |
| As of | 2026-07-11 (semi-final stage — real results through the quarter-finals) |
| Matches | 104 total — 100 completed, 4 upcoming |
| Teams / Players | 48 / 1,248 (real squads, 1,047 free-licensed headshots) |
| Models | 5 (Elo, Logistic Regression, Random Forest, XGBoost, Ensemble) |
| Engineered features | 10 |
| Training matches (real internationals, 2002→2026) | 2,948 |
| Top predicted champion | 🇦🇷 Argentina (~40%) |
| Best backtest model | Logistic Regression (64% acc, lowest log loss) |

---

## Screenshots

Screenshots are not committed to keep the repo lightweight. To capture your own:

1. `npm run dev` and open <http://localhost:3000>.
2. Capture the pages below (light **and** dark mode — toggle in the top-right):
   - `/` — Home dashboard
   - `/matches` — Fixtures & results (click a probability bar → prediction modal)
   - `/predictions` — Championship odds + knockout bracket
   - `/countries` and `/countries/[code]` — Country detail
   - `/players` and `/players/[id]` — Player profile
   - `/rankings`, `/models`, `/methodology`
3. Save them under `docs/screenshots/` and reference them here.

> Tip: press <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>K</kbd> anywhere to open the command palette.

---

## Features

### Product

- **Home dashboard** — KPI cards (matches completed/upcoming, top predicted champion,
  highest-confidence upcoming pick, best-performing model), championship race, and
  recent/upcoming match cards.
- **Matches** — Flags, team names, kickoff date/time, status (completed / upcoming /
  live-ready), scores for finished games, and win-probability bars for upcoming games.
  Filter by stage (group / knockout), status and country; sort by date, confidence,
  round or team name.
- **Prediction explanation modal** — Click any probability to open a breakdown of all
  five models (predicted winner, win probability, backtest accuracy, calibration/ECE),
  the ensemble headline, and the **top-5 contributing factors** with direction of
  influence. Every prediction is clearly labelled an **estimate**.
- **Predictions & bracket** — Monte-Carlo championship odds for all 48 nations plus a
  projected knockout bracket (Round of 32 → Final, with a third-place play-off).
- **Countries** — Flag, group, confederation, status and live title probability
  (eliminated ⇒ 0%). Country detail adds squad table, aggregated stats, strengths /
  weaknesses, key players and a championship-probability trend.
- **Players** — Searchable, sortable, filterable table of all 1,248 **real** players with
  **free-licensed headshots** (Wikimedia Commons; clean initials-avatar fallback), position,
  club, age, caps and rich stats. Player profiles add a stats table, form trend, a
  team-contribution score and photo attribution.
- **Rankings** — Nine ranking views (title odds, team strength, form, attack, defense,
  squad strength, model confidence, momentum, Elo) with charts and confederation
  filtering.
- **Models** — Leaderboard (accuracy, log loss, Brier, ECE, weight, rank), a selectable
  per-model **calibration reliability chart** and **feature-importance chart**, and a
  plain-English explanation of the self-improvement loop.
- **Data & Methodology** — The full pipeline, data-source table with licensing,
  feature set, model summaries and leakage/self-improvement notes.

### Experience & engineering

- Dark mode, responsive/mobile layouts, accessible contrast.
- Command palette (⌘K / Ctrl+K / `/`) for jumping to teams, players and pages.
- Skeleton loaders, empty states and a global error boundary.
- Tooltips on every technical metric.
- Deterministic, reproducible data (`SEED = 2026`).
- Unit tests (Vitest + Python `unittest`), ESLint, strict TypeScript.

---

## Tech stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Framework | **Next.js 16** (App Router, Server Components) | Static generation where possible |
| Language | **TypeScript** (strict) | Shared data contract in `src/lib/types.ts` |
| Styling | **Tailwind CSS v4** | CSS-variable design tokens, light/dark |
| UI primitives | Hand-built **shadcn-style** components on Radix | Dialogs, tooltips, selects, tabs, command menu |
| Charts | **Recharts 3** | Radar, area, bar, calibration & importance charts |
| Flags | **flag-icons** | Public-domain SVG country flags |
| ML / data | **Python**, NumPy, pandas, scikit-learn, XGBoost | Deterministic, offline |
| Testing | **Vitest** + Testing Library, Python **unittest** | |
| Tooling | ESLint (flat config), PostCSS | |

The frontend never computes predictions at request time — it reads pre-computed,
cached JSON from `public/data/`. This keeps pages fast and avoids recomputation on
every render.

---

## Project structure

```
.
├─ src/
│  ├─ app/                     # App Router pages (home, matches, predictions,
│  │                           #   countries, players, rankings, models, methodology)
│  │  ├─ loading.tsx / error.tsx / not-found.tsx
│  ├─ components/              # UI + feature components (cards, tables, charts,
│  │  ├─ ui/                   #   prediction modal, bracket, explorers, command palette)
│  │  └─ charts/               # Recharts wrappers (+ shared palette/theme)
│  └─ lib/                     # types (data contract), data loaders, formatters
├─ ml/
│  ├─ common.py                # constants, seeds, Elo/goal helpers, IO
│  ├─ sources.py               # parsers for the cached CC0 source files
│  ├─ tournament.py            # standings + general Monte-Carlo bracket simulator
│  ├─ ingest.py                # build raw inputs from real CC0 sources (+ real squads)
│  ├─ transform.py             # validation + cleaning
│  ├─ features.py              # feature engineering (leakage-safe, real Elo)
│  ├─ modeling.py              # Elo baseline, ensemble, metrics, calibration
│  ├─ train.py                 # train LogReg / RF / XGB (+ draw model)
│  ├─ predict.py               # per-model predictions, factors, rankings, Monte Carlo
│  ├─ evaluate.py              # backtest, re-weight ensemble, assemble frontend JSON
│  ├─ pipeline.py              # one-command orchestrator (ingest → evaluate)
│  ├─ refresh.py               # re-download CC0 sources (offline fallback) + rebuild
│  ├─ fetch_players.py         # real squads (Wikipedia) + free headshots (Commons)
│  ├─ models/                  # trained model artifacts (git-ignored)
│  └─ tests/test_ml.py         # Python unit tests
├─ data/
│  ├─ source/                    # cached CC0 sources + squads_wikipedia.json / credits
│  ├─ raw/  processed/  cached/  # pipeline stages
├─ public/
│  ├─ data/                    # cached JSON the frontend reads
│  └─ headshots/               # free-licensed player headshots (Wikimedia Commons)
├─ tests/                      # Vitest unit + data-integrity tests
├─ .env.example
└─ README.md
```

---

## Getting started

### Prerequisites

- **Node.js 20+** (Next.js 16) and npm
- **Python 3.11+** with `pip`

### Install

```bash
# 1. Frontend dependencies
npm install

# 2. Python dependencies (numpy, pandas, scikit-learn, xgboost)
pip install numpy pandas scikit-learn xgboost
```

The repo ships with the cached source data (`data/source/`) **and** the pre-computed
JSON the frontend reads (`public/data/`), so **you can run the app immediately** without
any network access or running the Python pipeline.

---

## Environment variables

**None are required.** The app runs fully offline out of the box, and even the data
refresh (`python ml/refresh.py`) needs **no API keys** — it pulls public-domain files
from public GitHub raw URLs over HTTPS.

A [`.env.example`](.env.example) documents *optional* variables reserved for future
live-data experiments (all blank/disabled by default). Copy it to `.env.local` if you
want to use them — `.env.local` is git-ignored and no secrets are ever committed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FOOTBALL_DATA_API_KEY` | *(empty)* | Optional free football-data API key (not needed for the CC0 refresh) |
| `ELO_RATINGS_SOURCE_URL` | *(empty)* | Optional open Elo ratings source override |
| `ENABLE_LIVE_DATA` | `0` | Set `1` to allow optional network fetches |

---

## Running the app

```bash
npm run dev      # start dev server → http://localhost:3000
npm run build    # production build
npm run start    # serve the production build
npm run lint     # ESLint
npm test         # Vitest unit + data-integrity tests
```

### Refresh the data

Two entry points:

```bash
# A) Re-download the real CC0 sources, then rebuild everything.
#    No API keys. Falls back to the committed caches if you're offline.
npm run data:fetch            # === python ml/refresh.py

# B) Rebuild from the committed source caches only (fully offline, deterministic).
npm run data:refresh          # === python ml/pipeline.py
```

`python ml/refresh.py` downloads five public-domain files (martj42 results +
shootouts, openfootball 2026 cup / cup_finals / stadiums) into `data/source/` using the
Python standard library only. Each file is validated and swapped in atomically, so a
failed or partial download never corrupts the cache — if a fetch fails, the previously
committed copy is kept and the pipeline still runs. Useful flags:

```bash
python ml/refresh.py --offline       # skip downloads, rebuild from caches
python ml/refresh.py --no-pipeline   # only refresh the source caches
python ml/refresh.py --players        # also refresh real squads + free headshots
python ml/refresh.py --from features # pass a resume-stage through to the pipeline
```

**Real squads + headshots (opt-in).** Squads and headshots are cached in the repo and
change infrequently, so they are **not** re-fetched on a normal refresh. To refresh them
from the public **MediaWiki APIs** (English Wikipedia squad templates + Wikimedia Commons
free-licensed portraits) run `npm run data:players` (or `python ml/refresh.py --players`
to fetch *and* rebuild). It uses **no API keys**, is polite/rate-limited, and degrades
gracefully — a network hiccup keeps the committed cache and the pipeline still runs.

```bash
npm run data:players                 # === python ml/fetch_players.py (squads + headshots)
python ml/fetch_players.py --no-images   # squad facts only (skip headshot downloads)
python ml/fetch_players.py --only ARG,ESP  # a subset of nations
```

Run a single pipeline stage, or resume from a stage:

```bash
python ml/pipeline.py --from features    # resume at feature engineering
npm run ml:ingest                        # individual stages:
npm run ml:transform
npm run ml:features
npm run ml:train        # train the models
npm run ml:predict      # generate predictions + Monte Carlo odds
npm run ml:evaluate     # backtest, re-weight ensemble, write frontend JSON
```

The real sources are the single source of truth: parsing is pure and the model-generated
player stats/ratings are seeded (`SEED = 2026`), so re-running the pipeline on the same
source files reproduces identical outputs. As the real tournament advances, refresh to pull
the latest results and the app tracks the live state automatically.

---

## The data pipeline

The pipeline is a classic staged data-engineering flow. Each stage reads the previous
stage's artifacts from `data/` and writes its own, ending in the cached JSON the app
consumes.

| # | Stage | Script | Output |
| --- | --- | --- | --- |
| 1 | **Ingest** | `ingest.py` + `sources.py` | Parse real CC0 sources → history, WC schedule/results, knockout tree, real squads (Wikipedia cache) → `data/raw/` |
| 2 | **Transform** | `transform.py` | Validated & cleaned tables → `data/processed/` |
| 3 | **Features** | `features.py` | Leakage-safe feature matrix (rolling form, Elo, xG, rest, squad strength) |
| 4 | **Train** | `train.py` | Logistic Regression, Random Forest, XGBoost, draw model → `ml/models/` |
| 5 | **Predict** | `predict.py` | Per-model probabilities, top factors, rankings, 20k-run Monte Carlo odds |
| 6 | **Evaluate** | `evaluate.py` | Backtest on completed matches, re-weight ensemble, assemble `public/data/*.json` |

**Cached outputs (`public/data/`):** `summary.json`, `teams.json`, `matches.json`,
`players.json`, `models.json`, `rankings.json`, `bracket.json`, `methodology.json`,
`search.json`. A copy is also mirrored to `data/cached/`.

---

## Data sources

| Source | Type | Description | License / notes |
| --- | --- | --- | --- |
| [`openfootball/worldcup`](https://github.com/openfootball/worldcup) — `2026--usa` | **Real · cached** | The actual 2026 field, 12-group draw, fixtures, results and knockout bracket (`cup.txt`, `cup_finals.txt`, `cup_stadiums.csv`) | **Public domain (CC0)** |
| [`martj42/international_results`](https://github.com/martj42/international_results) | **Real · cached** | Every men's international 1872→present (`results.csv`, `shootouts.csv`) — used to train the models and grow real Elo ratings | **Public domain (CC0)** |
| [English **Wikipedia**](https://en.wikipedia.org/) national-team squad templates | **Real · cached** | Current 26-player rosters for all 48 nations — name, shirt no., position, DOB/age, caps, goals, club (`data/source/squads_wikipedia.json`) | Text CC BY-SA 4.0; facts aren't copyrightable — Wikipedia credited here + in the app |
| [Wikimedia **Commons**](https://commons.wikimedia.org/) portraits | **Real · cached** | 1,047 free-licensed player headshots (`public/headshots/`), each with author + licence + source page (`data/source/headshot_credits.json`) | **Only free licences kept** (CC0 / public domain / CC BY / CC BY-SA); per-photo attribution shown in the UI |
| 48-team Elo priors & brand colours | **Curated** | Approximate starting Elo and team colours in `ml/common.py` | Curated from public knowledge |
| Per-player stats & ability ratings | **Generated** | Goals, assists, xG, minutes, ratings etc., keyed to the **real** players — no openly-licensed source exists | Synthetic — deterministic (`SEED = 2026`); flagged in the UI |
| Country flags | **Static** | `flag-icons` public-domain SVG sprites | MIT / public domain |

**Are these live, cached, sample or generated?**
The tournament data (field, draw, fixtures, results, bracket), the training history **and
the squads** are **real** and shipped **cached** in `data/source/` (plus committed
headshots in `public/headshots/`). Everything is fetched over plain HTTPS from public
repos / MediaWiki APIs — nothing is scraped from disallowed endpoints, and no login-gated
or paid dataset is used. Only **per-player performance statistics and ability ratings are
generated** (deterministically), because no clean, openly-licensed source of those exists.
Refresh with `python ml/refresh.py` (results) and `npm run data:players` (squads/headshots).

**Real squads.** The 26-player roster for each of the 48 nations comes from that nation's
maintained English-Wikipedia squad template (`{{nat fs … player}}`) — real names, shirt
numbers, positions, dates of birth/ages, caps, international goals and clubs. Facts like a
player's name or club aren't copyrightable; Wikipedia is credited regardless.

**Player headshots.** Per the build requirements, headshots are used **only** when the
Wikimedia Commons file carries a **free licence** (public domain / CC0 / CC BY / CC BY-SA).
That yields **1,047 of 1,248** players; the remaining 201 fall back to clean initials
avatars, so the UI never breaks on a missing image. Each kept photo stores its **author,
licence and Commons source page**, shown as attribution on the player profile (CC BY-SA
requires attribution). Non-free or missing images are never downloaded.

**Known limitation — player stats.** Per-player statistics (goals, assists, xG, minutes,
cards…) and the 0–100 ability rating are **model-generated** demonstration data seeded from
the real identity (caps, position, club tier). They exercise the players/profile UI and
feed a simple squad-strength feature, but the absolute numbers are illustrative and flagged
as such. Player **identities and photos**, and everything about *matches and outcomes*, are
real.

**How to refresh.** Run `python ml/refresh.py` (downloads CC0 results, then rebuilds), or
`npm run data:refresh` to rebuild from caches offline. For squads/headshots run
`npm run data:players` (or `python ml/refresh.py --players` to fetch *and* rebuild). All
refresh paths use **no API keys** and **no paid services**, with an offline fallback to the
committed caches.

**Licensing note.** This project respects site terms of service, `robots.txt`, rate limits
and dataset licensing. The two match/result datasets are **CC0 1.0 (public domain)**;
Wikipedia squad text is **CC BY-SA 4.0** (facts aren't copyrightable) and every headshot is
**free-licensed with per-photo attribution retained**. The generated per-player stats and
public-domain flag sprites carry no third-party data-licensing obligations.

---

## ML methodology

### Prediction targets

- Match outcome probabilities — **home win / draw / away win** (classes `0/1/2`).
- Team **advancement** probabilities and **tournament title** probability (Monte Carlo).

### Models

| Model | Type | Idea |
| --- | --- | --- |
| **Elo baseline** | Analytic baseline | Two-stage Elo: a draw model + the Elo win/loss split, including host advantage |
| **Logistic Regression** | Linear | Interpretable multinomial classifier over standardized features |
| **Random Forest** | Bagged trees | Captures non-linear interactions; robust to feature scaling |
| **XGBoost** | Gradient boosting | Strong tabular learner; regularized boosting |
| **Weighted Ensemble** | Blend | Probability average of the base models, **weighted ∝ 1 / log loss** |

### Features (10)

Recent team form, Elo/rating difference, expected-goals trend, goals scored/conceded,
squad strength, player-rating strength, rest days, tournament stage (knockout flag),
host advantage and head-to-head history. Relative importance is shown per model on the
**Models** page and aggregated on the **Methodology** page.

### Explainability

Each prediction lists its **top-5 contributing factors** with the direction each factor
favours. Factor weights are derived from the tree models' feature importances combined
with the specific feature values for that match — a transparent, inspectable
alternative to heavier SHAP computation.

### Metrics

Models are scored with **accuracy**, multiclass **log loss**, **Brier score**, and a
10-bin **calibration** reliability curve with **Expected Calibration Error (ECE)**.

### Leakage prevention & self-improvement

- **Train/evaluate separation.** Models train on **real** men's internationals since
  2002 (martj42, CC0), never on 2026 World Cup matches — the training history stops the
  day before the opener.
- **Predict before scoring.** Every model predicts *all* 104 matches before any real
  result is read. Only **completed** matches (currently 100) are used for evaluation;
  a match counts as completed only when a real result exists in the source data, and
  upcoming matches carry `score: null` in the cached data, so results can't leak into
  the UI either.
- **Self-improvement loop** (documented on the Methodology page):
  1. Score each model on completed matches.
  2. Re-rank models by log loss and flag persistent under-performers.
  3. Recompute ensemble weights **∝ 1 / log loss**.
  4. Re-blend the ensemble and republish the cached JSON.

These are **statistical estimates from a reproducible model, not guarantees.**

---

## Testing, linting & building

```bash
npm test                                   # 35 Vitest tests
python -m unittest discover -s ml/tests    # 14 Python tests
npm run lint                               # ESLint (flat config)
npm run build                              # production build (58 routes)
```

- **`tests/format.test.ts` / `model-meta.test.ts`** — pure UI helpers.
- **`tests/probability-bar.test.tsx`** — component render test (Testing Library).
- **`tests/data-integrity.test.ts`** — enforces ML invariants on the cached data:
  probabilities sum to 1, **no result leakage** (upcoming ⇒ no score), eliminated teams
  at 0% title odds, ensemble weights sum to ~1, unique model ranks, calibration bins in
  range.
- **`ml/tests/test_ml.py`** — Elo symmetry/monotonicity, expected goals, log-loss/Brier
  behaviour, ensemble normalization and importance ordering.

> **Note on ESLint 10.** `eslint-plugin-react`'s automatic React-version detection
> currently crashes under ESLint 10, so `eslint.config.mjs` pins `settings.react.version`
> explicitly. This is a tooling work-around, not an app change.

---

## Known limitations

- **Real squads, generated stats.** Squads (names, positions, ages, caps, clubs) and
  headshots are **real** (Wikipedia / Wikimedia Commons), but per-player **statistics and
  ability ratings are deterministically generated** — no clean, redistributable open dataset
  of full 2026 per-player stats exists. Those numbers are illustrative and flagged as demo
  data in the UI and README.
- **Partial headshot coverage.** 1,047 of 1,248 players have a free-licensed Commons photo;
  the remaining 201 show clean initials avatars (no non-free images are used).
- **Live-tracked state.** The tournament state reflects whatever results are present in
  the cached source (currently the semi-final stage: 100 completed, 4 upcoming). Run
  `python ml/refresh.py` to pull newer results as they're published upstream.
- **Backtest size.** Model metrics are computed on the completed World Cup matches (100
  so far), so differences between models are modest and can shift as more results arrive.
- **Knockout participants are projected.** Slots that depend on results not yet played
  are marked *(proj.)* and resolve as the bracket completes.

---

## Future improvements

- Optional live ingestion from a free/open football-data source (behind the `.env`
  flags already scaffolded).
- Openly-licensed **per-player stats** (goals, xG, minutes) to replace the generated
  demo numbers, keyed to the real squads already in place.
- Bayesian / hierarchical team-strength model and a Dixon-Coles goals model.
- Team- and player-comparison tools, favourites, and downloadable CSV exports.
- Prediction-history tracking across multiple pipeline runs.
- SHAP-based explanations as an opt-in, heavier alternative to the current factor logic.

---

## Original Build Prompt

<details>
<summary>The complete, verbatim prompt this project was built from.</summary>

```text
You are an expert full-stack engineer, data engineer, data scientist, and UI/UX designer. Build a production-quality web application for a 2026 FIFA World Cup prediction and analytics dashboard.

Important execution instructions:
1. Create a new Git branch named: worldcup-prediction
2. Build the complete application in this branch.
3. Commit all code changes with clear commit messages.
4. Push the branch to the remote repository.
5. Add this entire prompt to the README.md file under a section titled “Original Build Prompt” so I can refer to it later.
6. Do not use paid APIs, paid cloud services, paid datasets, or paid hosting unless there is already configuration in the repo for them.
7. Do not commit secrets, API keys, tokens, credentials, or private data.
8. If an external API key is required, use environment variables and provide a .env.example file.
9. If live data is unavailable, implement a reliable fallback using open-source datasets, cached sample data, or generated demo data, while clearly documenting the limitation in the README.
10. Follow website terms of service, robots.txt, rate limits, and data licensing rules. Do not scrape content that is disallowed. For player headshots, use only legally accessible images from open, public, or properly licensed sources. If reliable licensed headshots are unavailable, show clean placeholder avatars.

Project purpose:
Create a clean, modern website where I can view 2026 World Cup results, fixtures, predictions, countries, squads, players, player profiles, player headshots, player stats, team rankings, model rankings, and winning probabilities. This is also a data engineering and data science portfolio project, so the app should visibly include technical ML/data features, model explanations, data pipeline structure, and reproducible workflows.

The app should feel polished, fast, and modern. Prioritize clean UI/UX.

Recommended technology stack:
- Frontend: Next.js with TypeScript
- Styling: Tailwind CSS
- UI components: shadcn/ui or equivalent clean component system
- Charts/visualizations: Recharts, Tremor, or similar
- Backend/API: Next.js API routes, FastAPI, or a lightweight Node/Python service depending on the existing repo structure
- Data processing: Python scripts preferred if the repo supports it
- ML: scikit-learn, XGBoost if feasible, LightGBM if feasible, plus simple baseline models
- Database/storage: SQLite, DuckDB, local JSON/CSV cache, or existing repo database
- Testing: use the repo’s existing test framework if present; otherwise add practical unit/integration tests
- Linting/formatting: follow existing repo conventions

If the existing repository already has a stack, use that stack instead of replacing it. Do not unnecessarily rewrite unrelated code.

Core product requirements:

1. Home dashboard
Create a landing dashboard for the 2026 World Cup with:
- Clean, premium UI inspired by modern SaaS dashboards and high-quality sports analytics sites.
- Summary cards for:
  - Matches completed
  - Matches upcoming
  - Top predicted champion
  - Highest-confidence upcoming match
  - Best-performing model so far
- A clean navigation system with tabs/pages:
  - Matches
  - Predictions
  - Countries
  - Players
  - Rankings
  - Models
  - Data/Methodology

2. Matches page
Show all matches in a clean fixture/results layout:
- Display country flags.
- Display team names.
- Display match date/time.
- Display score if the game has already happened.
- Display status: upcoming, live if available, completed.
- If the game has not happened, show predicted win probability for each team.
- Use a clear horizontal probability bar using the main country colors when possible.
- If country colors are unavailable, create a tasteful default color palette.
- For completed matches, show actual result and compare it to the predicted result.
- Allow filtering by:
  - Group stage
  - Knockout round
  - Country
  - Completed/upcoming/live
- Allow sorting by:
  - Date
  - Prediction confidence
  - Round
  - Team name

3. Prediction explanation interaction
When a user clicks a predicted percentage for a match:
- Open a modal, drawer, or details panel.
- Show the top 5 ML models and their predicted probabilities.
- For each model, show:
  - Model name, for example Logistic Regression, Random Forest, XGBoost, Elo baseline, ensemble model
  - Predicted winner
  - Win probability
  - Accuracy so far, if actual results are available
  - Calibration score or confidence quality if feasible
  - Top 5 contributing factors
- Example top factors:
  1. Recent team form
  2. Elo/FIFA-style rating difference
  3. Expected goals trend
  4. Player strength score
  5. Injury/availability or lineup strength if data exists
- If model explanation methods are feasible, use feature importance, SHAP-like explanations, permutation importance, or model coefficients.
- If not feasible, provide transparent heuristic explanations based on available features.
- Do not present predictions as guaranteed. Clearly label them as estimates.

4. Model ranking page
Create a page that ranks ML models by performance:
- Show models sorted by current accuracy or another appropriate metric.
- Include:
  - Model name
  - Accuracy
  - Log loss if feasible
  - Brier score if feasible
  - Number of games evaluated
  - Average confidence
  - Last updated time
- Compare model predictions against completed match results.
- The model should first generate predictions without using the actual game result.
- After actual results are available, use them only for backtesting/evaluation.
- Avoid data leakage.

5. Countries page
Show all participating countries:
- Country flag
- Country name
- Confederation if data exists
- Group if data exists
- Current tournament status
- Current predicted winning percentage
- If a team has been eliminated, its tournament winning probability should be 0%.
- Clicking a country opens a country detail page or panel.

6. Country detail page
For each country, show:
- Team overview
- Current ranking/probability
- Matches played
- Upcoming matches
- Squad list
- Aggregated team stats
- Prediction trend if historical predictions are available
- Key players
- Strengths and weaknesses based on available data

7. Players page and squad tables
Show all players by country:
- Headshot photo if legally available, otherwise clean placeholder avatar
- Player name
- Country
- Position
- Club if available
- Age if available
- Player rating/score if available
- Goals, assists, expected goals, expected assists, minutes, cards, and other relevant statistics if available
- Allow sorting by:
  - Name
  - Country
  - Position
  - Rating
  - Goals
  - Assists
  - Minutes
  - Any other available useful stat
- Allow searching by player name.
- Allow filtering by country and position.
- Clicking a player should open a profile page or detail panel.

8. Player profile
For each player, show:
- Headshot or placeholder
- Name
- Country
- Position
- Club
- Bio/summary if data exists
- Stats table
- Trend charts if data exists
- Player contribution score
- Explanation of how the player impacts the team prediction if feasible

9. Rankings page
Create a rankings page with multiple ranking views:
- Championship winning probability
- Current team strength
- Recent form
- Attack strength
- Defense strength
- Player squad strength
- Model confidence
- Momentum/streak
- Allow sorting and filtering.
- Use clean tables and charts.

10. Data engineering requirements
Create a clear data pipeline structure:
- Raw data ingestion
- Data validation
- Data cleaning/transformation
- Feature engineering
- Model training
- Prediction generation
- Prediction evaluation
- Cached outputs for the frontend

Use open and legal data sources where possible. Investigate and use sources such as:
- Open football datasets
- Public football-data APIs where free
- Kaggle-style datasets only if licensing allows and no manual login is required
- Public GitHub datasets
- Official public match data if legally accessible
- Existing repo datasets if available

If live API access is possible without payment:
- Pull data dynamically when the app runs.
- Cache responses locally to avoid excessive requests.
- Add refresh logic.
- Document the data refresh process.

If live API access is not feasible:
- Use local sample datasets.
- Provide scripts to refresh data manually.
- Ensure the app still runs end-to-end.

Create a README section called “Data Sources” explaining:
- Which data sources were used
- Whether they are live, cached, sample, or generated
- Any known limitations
- How to refresh the data
- Any licensing notes

11. Data science and ML requirements
Build multiple predictive approaches if feasible:
- Elo rating baseline
- Logistic regression
- Random forest
- Gradient boosting model such as XGBoost or similar if dependencies allow
- Ensemble model combining multiple model outputs
- Optional Bayesian or simulation-based tournament model

Prediction targets:
- Match win probability
- Draw probability if group-stage match format requires it
- Team advancement probability if feasible
- Tournament winning probability

Feature ideas:
- Team historical performance
- Recent form
- Goals scored/conceded
- Expected goals if available
- Expected assists if available
- FIFA/Elo-style rating
- Squad strength
- Player ratings
- Starting lineup strength if available
- Injuries/availability if legally available
- Rest days
- Travel/location factor if useful
- Tournament stage
- Head-to-head history if available

Modeling requirements:
- Prevent data leakage.
- Separate training data from evaluation data.
- Use completed matches only for evaluating predictions.
- Store model outputs in a structured file or database table.
- Make predictions explainable at a high level.
- Display top contributing factors for each prediction.
- If exact SHAP/explainability is too expensive or complex, use simpler feature importance or transparent heuristic explanations.

Self-improvement requirement:
Implement a practical model evaluation/refinement loop, not vague AI magic.
- Evaluate each model against completed matches.
- Track accuracy and probabilistic scoring metrics.
- Re-rank models based on performance.
- If a model is consistently underperforming, document that in the model ranking page.
- If feasible, automatically update ensemble weights based on model performance.
- Clearly explain this logic in the Data/Methodology page.

12. UI/UX requirements
The UI must be especially clean and polished.
Use:
- Spacious layout
- Strong visual hierarchy
- Beautiful cards
- Minimal clutter
- Responsive design
- Smooth loading states
- Empty states
- Error states
- Skeleton loaders where appropriate
- Modern tables
- Accessible color contrast
- Mobile-friendly layouts
- Clean flag and team visuals
- Clear probability bars
- Tooltips for technical metrics
- Modal/drawer interactions for prediction details

Benchmark from clean modern UI patterns used by:
- Linear
- Vercel
- Stripe
- Airbnb
- Apple-style product pages
- Modern sports analytics dashboards

Do not copy proprietary designs. Use them only as inspiration for simplicity, spacing, visual hierarchy, and polish.

13. Performance and reliability
The app should:
- Run locally with simple setup commands.
- Avoid slow page loads.
- Cache data where appropriate.
- Avoid unnecessary re-computation on every page render.
- Handle missing data gracefully.
- Never crash because a player photo, stat, or API field is missing.
- Include loading/error states.
- Include practical tests for critical data functions and prediction logic.
- Include linting/formatting if available.
- Avoid large, unnecessary dependencies.

14. Documentation requirements
Update README.md with:
- Project overview
- Features
- Screenshots instructions or screenshot placeholders
- Tech stack
- Setup instructions
- Environment variables
- How to run the app
- How to refresh data
- How to train models
- How to generate predictions
- Data sources
- ML methodology
- Known limitations
- Future improvements
- Original Build Prompt containing this entire prompt

Also include:
- .env.example if environment variables are used
- Comments in complex ML/data code
- Clear folder structure

15. Suggested file/folder structure
Adapt this to the existing repo structure if necessary:

/app or /src
  /components
  /pages or /app routes
  /lib
  /api
  /styles
/data
  /raw
  /processed
  /cached
/ml
  ingest.py
  transform.py
  features.py
  train.py
  predict.py
  evaluate.py
  models/
  outputs/
/public
  /flags
  /player-placeholders
/tests
README.md
.env.example

16. Minimum viable features that must work
At minimum, deliver:
- A polished home dashboard
- Matches page with completed/upcoming matches
- Prediction probability bars
- Clickable prediction detail modal/panel
- Countries page with winning probabilities
- Country detail with squad table
- Players page with sortable/filterable table
- Model ranking page
- Data/methodology page
- Local data pipeline or sample data pipeline
- At least three prediction methods:
  - Elo baseline
  - Logistic regression or similar statistical model
  - Random forest, gradient boosting, or ensemble model
- README documentation
- Prompt saved in README
- Branch created and pushed as worldcup-prediction

17. Enhancements to add if feasible
Add as many useful enhancements as possible without breaking the fundamentals:
- Tournament bracket visualization
- Champion probability simulation
- Prediction history chart
- Dark mode
- Search command palette
- Team comparison tool
- Player comparison tool
- Downloadable CSV for predictions
- Model calibration chart
- Confidence badges
- Favorite teams
- Responsive mobile cards
- Data freshness indicator
- Explainability visualizations
- Lightweight admin/data refresh button if safe

18. Quality process
Work iteratively:
- Inspect the repo first.
- Identify existing framework, package manager, and conventions.
- Build the smallest working vertical slice first.
- Then add pages, data, ML, polish, and documentation.
- Run available tests, linting, and build commands.
- Fix errors found during validation.
- Remove dead code.
- Avoid broken links.
- Ensure the app starts successfully.
- Ensure core pages render.
- Ensure sample data works even when live data is unavailable.
- Ensure README instructions are accurate.

19. Final response format
After completing the implementation, summarize:
- Branch name
- Files changed
- Key features implemented
- Data sources used
- ML models implemented
- How to run the app
- Known limitations
- Any manual follow-up needed, especially for API keys or live data
- Confirmation that README contains this original prompt
- Confirmation that the branch was pushed

Remember:
The most important priorities are:
1. Clean and beautiful UI
2. Reliable end-to-end app experience
3. Clear World Cup matches, teams, players, and prediction views
4. Transparent ML methodology
5. Practical data engineering structure
6. Strong README documentation
```

</details>

---

## Disclaimer

This project is an independent **portfolio demonstration**. It is not affiliated with,
endorsed by, or associated with FIFA or any football federation. Match results and the
tournament bracket come from **public-domain (CC0)** datasets; **player squads and
headshots are real** (English Wikipedia / Wikimedia Commons, free-licensed with
attribution), while **per-player stats and ratings are generated for demonstration**, and
predictions are **statistical estimates, not guarantees**. Country flags are public-domain
assets from `flag-icons`. Player headshots are used only under free licences (CC0 / public
domain / CC BY / CC BY-SA) with per-photo attribution shown in the app; players without a
free-licensed photo show a clean initials avatar.
