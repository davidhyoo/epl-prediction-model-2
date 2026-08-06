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
- [Architecture & components (the "agents")](#architecture--components-the-agents)
- [The refresh system (deep dive)](#the-refresh-system-deep-dive)
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
players; the rest fall back to clean initials avatars). **Per-player tournament stats are
real as well** — appearances, minutes, goals, cards and goalkeeper clean sheets / goals
conceded are parsed from the official **FIFA match reports** (via Wikipedia). Only the
0–100 ability **rating** is model-generated, and advanced metrics with no free source
(assists, xG…) are omitted rather than faked — clearly flagged wherever it appears. See
[Data sources](#data-sources).

Current snapshot (refresh any time with `python ml/refresh.py`):

| Metric | Value |
| --- | --- |
| Tournament | 2026 FIFA World Cup (USA · Canada · Mexico) |
| As of | 2026-07-19 (**tournament complete** — all 104 real results in) |
| Matches | 104 total — 104 completed, 0 upcoming |
| Teams / Players | 48 / 1,248 (real squads, 1,047 free-licensed headshots) |
| Models | 5 (Elo, Logistic Regression, Random Forest, XGBoost, Ensemble) |
| Engineered features | 10 |
| Training matches (real internationals, 2002→2026) | 2,948 |
| Champion | 🇪🇸 **Spain** (beat 🇦🇷 Argentina 1–0 a.e.t. in the final) |
| Best backtest model | Logistic Regression (63% acc, lowest log loss) |

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
  club, age, caps and **real World Cup stats** (goals, appearances, minutes). Player profiles
  add a real per-match log (opponent, result, minutes, goals, cards), the tournament stat
  table, a team-contribution score and photo attribution.
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
│  │  │                        #   countries, players, rankings, models, methodology)
│  │  ├─ api/refresh/          # POST route → runs ml/refresh.py (dev / ALLOW_DATA_REFRESH)
│  │  ├─ loading.tsx / error.tsx / not-found.tsx
│  ├─ components/              # UI + feature components (cards, tables, charts,
│  │  ├─ ui/                   #   prediction modal, bracket, explorers, command palette)
│  │  └─ charts/               # Recharts wrappers (+ shared palette/theme)
│  └─ lib/                     # types (data contract), data loaders, formatters
├─ ml/
│  ├─ common.py                # constants, seeds, Elo/goal helpers, IO
│  ├─ sources.py               # parsers for the cached CC0 source files (+ player stats)
│  ├─ tournament.py            # standings + general Monte-Carlo bracket simulator
│  ├─ ingest.py                # build raw inputs from real CC0 sources (+ real squads/stats)
│  ├─ transform.py             # validation + cleaning
│  ├─ features.py              # feature engineering (leakage-safe, real Elo)
│  ├─ modeling.py              # Elo baseline, ensemble, metrics, calibration
│  ├─ train.py                 # train LogReg / RF / XGB (+ draw model)
│  ├─ predict.py               # per-model predictions, factors, rankings, Monte Carlo
│  ├─ evaluate.py              # backtest, re-weight ensemble, assemble frontend JSON
│  ├─ pipeline.py              # one-command orchestrator (ingest → evaluate)
│  ├─ refresh.py               # re-download CC0 sources + real player stats + rebuild
│  ├─ fetch_players.py         # real squads (Wikipedia) + free headshots (Commons)
│  ├─ fetch_stats.py           # real per-player WC stats (Wikipedia FIFA match reports)
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
| `ALLOW_DATA_REFRESH` | *(dev only)* | Set `1` to enable the in-app **Refresh data** button (`/api/refresh`) outside development |
| `PYTHON_BIN` | `python` | Python executable used by `/api/refresh` (e.g. `python3` or an absolute venv path) |

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
Python standard library only, then refreshes the **real per-player World Cup statistics**
from the English-Wikipedia match articles (which transcribe the official FIFA match
reports) via `ml/fetch_stats.py`. Those stats change after every match, so they are pulled
on **every** run. Each file is validated and swapped in atomically, so a failed or partial
download never corrupts the cache — if a fetch fails, the previously committed copy is kept
and the pipeline still runs. Useful flags:

```bash
python ml/refresh.py --offline       # skip downloads, rebuild from caches
python ml/refresh.py --no-pipeline   # only refresh the source caches
python ml/refresh.py --players        # also refresh real squads + free headshots
python ml/refresh.py --from features # pass a resume-stage through to the pipeline

python ml/fetch_stats.py             # refresh only the real player stats (npm run data:stats)
python ml/fetch_stats.py --offline   # validate the stats cache without any network
```

**Refresh from the app (live tracking).** A **“Data · &lt;date&gt;”** control lives in the top
navigation bar on **every page** (with a green “live” dot and the date of the latest loaded
result). Clicking it — or the larger **“Refresh data”** button at the bottom of the **Data &
Methodology** page — calls `POST /api/refresh`, which runs `python ml/refresh.py` on the
server: it pulls the latest completed results **and** real player match stats from the open
sources, rebuilds every cached JSON, and then revalidates all pages so the whole dashboard
reflects the new data instantly — **no code change, no restart, no redeploy**. Hover the
control for a tooltip showing exactly how current the data is. Because it launches a local
process, it is **enabled in development only** by default; set `ALLOW_DATA_REFRESH=1` to
enable it elsewhere (it then revalidates the static pages too), and `PYTHON_BIN` if `python`
isn't on `PATH`.

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

The real sources are the single source of truth: parsing is pure and the only
model-generated player field — the 0–100 ability **rating** — is seeded (`SEED = 2026`), so
re-running the pipeline on the same source files reproduces identical outputs. Per-player
**tournament stats are real** (parsed from the FIFA match reports), so as the tournament
advances a refresh pulls the latest results *and* the latest player numbers, and the app
tracks the live state automatically.

---

## The data pipeline

The pipeline is a classic staged data-engineering flow. Each stage is a **standalone
module** that reads the previous stage's artifacts from `data/` and writes its own,
ending in the cached JSON the app consumes. `pipeline.py` simply imports and runs the six
stages in order; any stage can also be run on its own (`python ml/<stage>.py`) or resumed
with `python ml/pipeline.py --from <stage>`.

```
 NETWORK — opt-in, key-less HTTPS               OFFLINE · DETERMINISTIC (SEED = 2026)
┌─────────────────────────────────┐   ┌───────────────────────────────────────────────────┐
│ refresh.py  (orchestrator)      │   │ 1 ingest → 2 transform → 3 features → 4 train      │
│  ├─ 5 CC0 source files  ────────┼──▶│                                     → 5 predict     │
│  ├─ fetch_stats.py (every run)  │   │                                     → 6 evaluate    │
│  └─ fetch_players.py (opt-in)   │   └───────────────────────┬───────────────────────────┘
└─────────────────────────────────┘                          │
     data/source/  ──▶  data/raw/  ──▶  data/processed/  ──▶  ml/models/  ──▶  ml/outputs/
                                                                                    │
                                                                                    ▼
                                                     public/data/*.json  ← what the frontend reads
```

| # | Stage | Script | Output |
| --- | --- | --- | --- |
| 1 | **Ingest** | `ingest.py` + `sources.py` | Parse real CC0 sources → history, WC schedule/results, knockout tree, real squads + **real player match stats** (Wikipedia cache) → `data/raw/` |
| 2 | **Transform** | `transform.py` | Validated & cleaned tables → `data/processed/` |
| 3 | **Features** | `features.py` | Leakage-safe feature matrix (rolling form, Elo, xG, rest, squad strength) |
| 4 | **Train** | `train.py` | Logistic Regression, Random Forest, XGBoost, draw model → `ml/models/` |
| 5 | **Predict** | `predict.py` | Per-model probabilities, top factors, rankings, 20k-run Monte Carlo odds → `ml/outputs/` + `teams/players/rankings/methodology.json` |
| 6 | **Evaluate** | `evaluate.py` | Backtest on completed matches, re-weight ensemble, assemble `matches/models/summary/bracket/search.json` |

**Cached outputs (`public/data/`):** `summary.json`, `teams.json`, `matches.json`,
`players.json`, `models.json`, `rankings.json`, `bracket.json`, `methodology.json`,
`search.json`. Every `publish()` call writes to `public/data/` **and** mirrors a copy to
`data/cached/` (both are committed so the app runs with zero setup).

---

## Architecture & components (the "agents")

The project is built from small, single-responsibility modules — think of them as
cooperating **agents**, each owning one job in the flow. They fall into four groups:
**(A)** data-acquisition agents (the only code that touches the network), **(B)** the six
pipeline-stage agents (pure, offline, deterministic), **(C)** shared libraries they all
build on, and **(D)** the serving agents (the Next.js frontend/backend). Every stage is
deterministic (`SEED = 2026`): re-running on the same source files reproduces identical
output.

For each component below: **Role**, what it **Reads**, what it **Writes**, its **Key
logic**, and its **Failure behavior** (so you know what breaks and where).

### A. Data-acquisition agents — the only parts that hit the network

#### `refresh.py` — refresh orchestrator
- **Role:** the single entry point behind `npm run data:fetch` and the in-app **Refresh
  data** button. Re-downloads the CC0 sources, refreshes real player stats, then runs the
  whole pipeline so `public/data/*.json` reflects the newest real results. Fully covered
  in [The refresh system](#the-refresh-system-deep-dive).
- **Reads:** public GitHub raw URLs (CC0). **Writes:** `data/source/*`, then triggers the
  pipeline. **Failure behavior:** validate-before-swap + atomic replace + candidate-URL
  fallback; on any download failure it keeps the committed cache and prints a visible
  `WARNING` instead of failing silently.

#### `fetch_stats.py` — real per-player tournament stats
- **Role:** derives **real** WC-2026 per-player stats (appearances, minutes, goals,
  yellow/red cards, and for goalkeepers clean sheets / goals conceded) from the public
  English-Wikipedia **match articles**, which transcribe the official FIFA match reports
  (goalscorer lists + starting-XI/substitution tables). Runs on **every** refresh because
  these numbers change after each match.
- **Reads:** MediaWiki API (no key). **Writes:** `data/source/player_stats_wikipedia.json`.
- **Key logic:** each scorer/lineup entry is a `[[wiki article title]]` — the exact title
  stored on every squad player by `fetch_players.py` — so the join back onto the squad is
  **exact, not fuzzy**. Assists/xG/shots are **not** in any free source and are left null
  (never fabricated).
- **Failure behavior:** non-fatal — a network hiccup keeps the committed stats cache and
  the pipeline still runs. `--offline` validates the cache without any network.

#### `fetch_players.py` — real squads + free headshots (opt-in)
- **Role:** downloads the real, current 26-player squad for each of the 48 nations from
  the maintained Wikipedia `{{nat fs … player}}` templates, plus a **freely-licensed**
  headshot from Wikimedia Commons where one exists.
- **Reads:** MediaWiki APIs (no key, polite/rate-limited). **Writes:**
  `data/source/squads_wikipedia.json`, `public/headshots/<CODE>-<NN>.jpg`, and
  `data/source/headshot_credits.json` (per-photo author + licence + source page).
- **Key logic:** only **free** licences (PD/CC0/CC BY/CC BY-SA) are kept; anything else
  falls back to the app's initials avatar. Idempotent — existing headshots aren't
  re-downloaded unless `--force-images`.
- **Failure behavior:** opt-in (`npm run data:players` / `--players`); on failure the
  committed squad cache is kept. Because squads change rarely, this is **not** run on a
  normal refresh.

### B. Pipeline-stage agents — pure, offline, deterministic

#### 1. `ingest.py` — raw data ingestion
- **Reads:** cached CC0 sources via `sources.py` + the 48-team field in `common.py`.
- **Writes:** `data/raw/{teams,history,wc_matches,squads,qualification}.json`.
- **Key logic:** builds the training history (every men's international up to the day
  **before** the opener — leakage-free), the real 2026 schedule/results, real group tables
  + the Round-of-32 bracket + a knockout tree with `W##/L##` feeders. A match's status is
  derived from **whether a real result exists**, so the app tracks the live tournament.
- **Failure behavior:** if a squad cache is missing it falls back to deterministically
  generated squads so the pipeline still completes.

#### 2. `transform.py` — validation, cleaning & transformation
- **Reads:** `data/raw/`. **Writes:** `data/processed/`.
- **Key logic:** the pipeline's **data-validation gate** — schema, range and
  referential-integrity checks, and a per-stage match-count check (72 group + 16 R32 + …
  = 104). Threads through knockout metadata (`winner`, `pens`, `aet`). Fails **loudly**
  (`ValidationError`) if the raw data is malformed rather than shipping bad data forward.
- **Failure behavior:** raises on malformed data — an intentional hard stop.

#### 3. `features.py` — feature engineering
- **Reads:** `data/processed/`. **Writes:** the leakage-safe feature matrices
  (`train.json`, `wc_features.json`) + `team_strength.json`.
- **Key logic:** every feature is computed from information available **before kick-off**
  (rolling Elo, form, goals for/against, xG trend, rest days, head-to-head). Real Elo is
  grown by walking the entire history from a common 1500 baseline, so each 2026 side's
  rating is *earned* from real results, never hand-set. Elo is snapshotted at each
  completed stage (feeds the champion-odds trend).

#### 4. `train.py` — model training
- **Reads:** the training matrix (real internationals only). **Writes:** `ml/models/`
  (joblib artifacts + `meta.json` with feature importances).
- **Key logic:** trains Logistic Regression (standardised, multinomial), Random Forest,
  XGBoost, and a fitted draw model for the Elo baseline. **No World Cup match is ever in
  training.** A time-based split prints honest validation metrics; final models refit on
  the full history.

#### 5. `predict.py` — prediction generation
- **Reads:** trained models + feature matrix. **Writes:** `ml/outputs/predictions.json`
  and publishes `teams.json`, `players.json`, `rankings.json`, `methodology.json`.
- **Key logic:** per-match home/draw/away probabilities for **every** model, the top-5
  **contributing factors** for the explanation modal, a vectorised **20k-run Monte-Carlo**
  championship simulation that **fixes every completed knockout result** and simulates only
  what's left (eliminated teams → 0%), projection of the not-yet-scheduled third-place/final
  matches from their most-likely participants, and realistic per-player stat allocation.

#### 6. `evaluate.py` — backtest, self-improvement & final assembly
- **Reads:** `ml/outputs/predictions.json` + `teams/players.json`. **Writes:**
  `matches.json`, `models.json`, `summary.json`, `bracket.json`, `search.json`.
- **Key logic:** scores each model on **completed matches only**, derives ensemble weights
  **∝ 1 / log-loss** (the self-improvement loop), re-ranks models and flags
  under-performers, blends the weighted ensemble, and emits `resultWinner`/`aet` so
  knockout ties settled in extra time / on penalties show the real advancing side while the
  models stay scored on the regulation-time 1X2 outcome (leakage-free).

#### `pipeline.py` — stage orchestrator
- **Role:** runs `ingest → transform → features → train → predict → evaluate` in order;
  `--from <stage>` resumes partway. Each stage is imported and its `main()` called, so the
  flow is reproducible and restartable.

### C. Shared libraries (used by every stage)

| Module | What it provides |
| --- | --- |
| `common.py` | Constants, `SEED`, directory paths, Elo/expected-goals math, JSON IO + `publish()` (writes `public/data/` **and** `data/cached/`), and the real 48-team field / group draw. |
| `sources.py` | Pure parsers for the cached source files (openfootball Football.TXT group + knockout parsing incl. `a.e.t.`/penalties, martj42 CSVs, the Wikipedia squad/stat caches). **No network here** — parsing only. |
| `modeling.py` | The analytic Elo-baseline probability model, ensemble blending, and the probabilistic metrics: accuracy, multiclass log-loss, Brier, calibration bins + Expected Calibration Error (ECE). Class order is fixed everywhere: `0 = home, 1 = draw, 2 = away`. |
| `tournament.py` | Standings/qualification logic + the Monte-Carlo bracket simulator, which is *stateful about reality*: already-played knockout matches are fixed to their real winner and only the rest are simulated. |

### D. Serving agents (frontend + backend)

| Component | Role |
| --- | --- |
| `src/app/api/refresh/route.ts` | The `POST /api/refresh` endpoint that spawns `ml/refresh.py`, guards execution, and revalidates pages. See the deep dive below. |
| `src/components/refresh-data-button.tsx` | The client refresh UI: the `useDataRefresh` hook, the nav **`DataFreshnessControl`** pill, the methodology-page **`RefreshDataButton`**, and the `RefreshToast`. |
| `src/lib/` | The shared data contract (`types.ts`) and the loaders that read `public/data/*.json` on the server. **The frontend never computes predictions at request time** — it only reads pre-built JSON, which is what keeps pages fast. |

---

## The refresh system (deep dive)

Keeping the dashboard aligned with the **actual, latest** results is the whole point of
the app, so the refresh path is built to be **safe, self-healing, and debuggable**. This
section explains exactly how it is constructed, layer by layer, and — most importantly —
**how to diagnose it when a refresh doesn't produce the results you expect.**

### End-to-end flow

```
[User clicks "Data · <date>" pill  or  "Refresh data" button]
                     │  (src/components/refresh-data-button.tsx → useDataRefresh)
                     ▼
        POST /api/refresh[?mode=offline]
                     │  (src/app/api/refresh/route.ts — Node runtime)
                     ▼
   guards: enabled? ──no──▶ 403     already running? ──yes──▶ 409
                     │
                     ▼  spawn(PYTHON_BIN, ["ml/refresh.py", …], {shell:false})
        ┌──────────────────────────────────────────────┐
        │ ml/refresh.py                                 │
        │  1. refresh_sources()  → download 5 CC0 files │
        │       · candidate-URL fallback + validate     │
        │       · atomic swap, or keep cache + WARNING  │
        │  2. fetch_stats.py     → real player stats    │
        │  3. pipeline.run()     → rebuild public/data/ │
        └───────────────────────┬──────────────────────┘
                     │ exit 0 + stdout/stderr (last 12 lines returned as `log`)
                     ▼
        route.ts: revalidatePath("/", "layout")   ← purges the full route cache
                     │
                     ▼
        useDataRefresh: router.refresh()          ← re-fetches server components
                     │
                     ▼
        Toast: "Live data reloaded in Ns."  →  whole dashboard shows new data
```

### Layer 1 — the button (client): `refresh-data-button.tsx`

- Two entry points share one hook (`useDataRefresh`): the compact **`DataFreshnessControl`**
  pill in the top nav (present on **every** page, showing a live dot + the date of the
  latest loaded result) and the full-width **`RefreshDataButton`** on the Methodology page.
- The hook does `POST /api/refresh`, tracks four states (`idle → running → done | error`),
  and shows a `RefreshToast`. A `runningRef` guard makes it **single-flight** on the client
  so double-clicks can't fire two requests.
- On success it calls **`router.refresh()`**, which re-fetches the (server-rendered)
  components so the new JSON is reflected everywhere without a reload.
- The pill/button is only interactive when the server says the endpoint is **enabled**
  (`enabled` prop). When disabled it renders as a static, non-clickable status pill and the
  tooltip tells you how to enable it.

### Layer 2 — the API route (server): `api/refresh/route.ts`

- Runs on the **Node.js runtime** (`export const runtime = "nodejs"`) and is
  `force-dynamic` (never statically cached), because it shells out to Python.
- **`refreshEnabled()`** → `NODE_ENV !== "production" || ALLOW_DATA_REFRESH === "1"`.
  Disabled ⇒ **HTTP 403**. This is why the button works in `npm run dev` but is off in a
  production build unless you opt in.
- A module-level **`running` flag** prevents overlapping pipelines ⇒ **HTTP 409** while one
  is in progress.
- `?mode=offline` appends `--offline` (rebuild from caches, no network); the default pulls
  live data first.
- Python is resolved as **`PYTHON_BIN` → `PYTHON` → `"python"`**. The child is spawned with
  **`shell: false`** and a fixed, in-repo argument list, so **no user input is ever
  interpolated** into the command (no shell-injection surface).
- stdout **and** stderr are captured (capped at 200 KB); a **12-minute timeout** SIGKILLs a
  hung run. The last **12 non-empty log lines** are returned as `log` in the JSON.
- Outcomes:
  - success ⇒ **`revalidatePath("/", "layout")`** (this is what makes the refresh land even
    in a production build, not just `next dev`) then `{ ok:true, durationMs, mode, log }`.
  - non-zero exit ⇒ **HTTP 500** `{ ok:false, error:"refresh.py exited with code N", log }`.
  - can't launch Python ⇒ a friendly **ENOENT** message telling you to install Python or set
    `PYTHON_BIN`.

### Layer 3 — the worker: `ml/refresh.py`

This is the part that actually fetches data, and it is deliberately defensive:

- **`SOURCES`** is a list of `(candidate_urls, local_filename, min_bytes, marker)` tuples.
  `candidate_urls` is a **list tried in order** (first that yields a *valid* file wins).
- **`OPENFOOTBALL_DIRS = ["2026--canada-usa-mexico", "2026--usa"]`** + the `_openfootball()`
  helper generate those candidates newest-directory-first. **This is the rename-resilience**:
  when openfootball renamed the 2026 folder, the single old URL 404'd and refresh silently
  kept stale data — now a rename just falls through to the next candidate. *If it renames
  again, add the new directory name to the front of this list* (see troubleshooting).
- **`_fetch_one()`** downloads a candidate, then **validates before touching the real file**:
  it checks a **minimum byte size** and that a required **marker string** appears in the
  first 4 KB (a cheap guard against 404 pages / truncated responses). Only a valid download
  is written to a `.tmp` file and **atomically `os.replace()`-d** into place, so a bad
  response can never corrupt the committed cache.
- **`refresh_sources()`** returns `(updated, kept_from_cache)`. If **any** file was served
  from cache it prints a loud **`WARNING`** (so silent staleness can't recur). It only
  aborts (`FATAL`) if a file both failed to download **and** has no cached copy at all.
- Then it runs **`fetch_stats.py`** (every run; non-fatal on failure), optionally
  **`fetch_players.py`** (`--players`), and finally **`pipeline.run()`** unless
  `--no-pipeline`.

### Design principles (why it's built this way)

| Principle | How it's enforced |
| --- | --- |
| **No keys / no paid services** | Plain HTTPS to public GitHub raw + MediaWiki APIs, stdlib only. |
| **Never corrupt the cache** | Validate (size + marker) → write `.tmp` → atomic `os.replace()`. |
| **Offline fallback** | A failed download keeps the committed cache; the pipeline still runs. |
| **Rename-resilient** | Per-file **candidate-URL list**, newest directory first. |
| **No silent staleness** | Any cache-kept file prints a visible `WARNING` in the log/toast. |
| **Safe to expose** | `shell:false`, fixed args, dev-only by default, single-flight, timeout. |
| **Live without redeploy** | `revalidatePath` + `router.refresh()` update prerendered pages in place. |
| **Deterministic** | `SEED = 2026` → same sources reproduce identical outputs. |

### Troubleshooting — when a refresh doesn't work

Start by reading the **`log`** the endpoint returns (last 12 lines) or run the script
directly to see everything: **`python ml/refresh.py`**. Then match the symptom below.

| Symptom | Likely cause | How to confirm & fix |
| --- | --- | --- |
| The nav pill is a **static badge** (not clickable) | Endpoint disabled (production build without opt-in) | Expected outside dev. Use `npm run dev`, **or** set `ALLOW_DATA_REFRESH=1`. |
| **HTTP 403** "In-app refresh is disabled" | Same as above | Same fix. |
| **HTTP 409** "already in progress" | A refresh is still running (12-min cap) | Wait for it to finish; the single-flight guard is working as intended. |
| **HTTP 500** "Could not launch Python (ENOENT)" | `python` not on `PATH`, or wrong `PYTHON_BIN` | Run `python --version`. Install Python 3.11+, or set `PYTHON_BIN` to an absolute path (e.g. a venv's `python.exe`). |
| **HTTP 500** "refresh.py exited with code N" | The script itself errored | Read `log`, then reproduce with `python ml/refresh.py` for the full traceback. Missing deps? `pip install numpy pandas scikit-learn xgboost`. |
| "**refresh timed out after 720s**" | Very slow network / stalled fetch | Re-run; or run `python ml/refresh.py --offline` (rebuild from caches), or `--no-pipeline` to isolate downloads. |
| Log shows **"all sources failed — keeping cache"** + `WARNING` | No network **or** the upstream directory/filename moved again | Test a candidate URL directly (see below). If the source **renamed** its folder, add the new name to the front of `OPENFOOTBALL_DIRS` in `ml/refresh.py`. **This exact issue** (openfootball `2026--usa` → `2026--canada-usa-mexico`) is what the candidate-URL fallback now guards against. |
| Log shows **"too small"** / **"missing marker"** for a source | Upstream file moved or changed format (you fetched a 404/redirect page) | Open the URL in a browser; update the URL, `min_bytes`, or `marker` in `SOURCES`. |
| **`FATAL: … no cached copy exists`** | First-ever run is offline with an empty `data/source/` | Connect to the internet once to seed the caches, then offline works forever. |
| Refresh returns **`ok:true`** but the page looks unchanged | (a) Nothing actually changed upstream yet; (b) you ran `?mode=offline`; (c) a stale browser tab | Check the log for `updated` vs `kept`; confirm `public/data/summary.json`'s `asOf`; hard-refresh the tab (`router.refresh()` runs automatically, but a manual reload never hurts). |
| `npm` / `next` won't start with "**node is not recognized**" | Node.js not on `PATH` (unrelated to the refresh path — Python still works) | Fix Node (e.g. `winget upgrade OpenJS.NodeJS.LTS`) or point at a known-good `node`/`npm`. The Python refresh (`python ml/refresh.py`) is unaffected. |

### Manual diagnostics

```bash
# 1) Only touch the network — download the 5 CC0 sources, skip the rebuild:
python ml/refresh.py --no-pipeline

# 2) Prove the pipeline is fine offline (rebuild purely from committed caches):
python ml/refresh.py --offline

# 3) Check one upstream URL by hand (should be HTTP 200, non-trivial size):
#    (PowerShell)  Invoke-WebRequest -Method Head <url>
#    (curl)        curl -I <url>
#    openfootball 2026 finals, current dir:
#    https://raw.githubusercontent.com/openfootball/worldcup/master/2026--canada-usa-mexico/cup_finals.txt

# 4) Refresh only the live player stats (isolates the Wikipedia stats agent):
python ml/fetch_stats.py            # live
python ml/fetch_stats.py --offline  # validate the cache, no network

# 5) Inspect what the app will show after a rebuild:
#    public/data/summary.json  → asOf, matchesCompleted/Upcoming, topChampion
```

**Where to change the source location:** the only place that knows upstream URLs is
`SOURCES` (and `OPENFOOTBALL_DIRS`) at the top of **`ml/refresh.py`**. Local cache
filenames in `data/source/` are stable and independent of the remote names, so a source
move only ever requires editing that one list — nothing downstream changes.

---

## Data sources

| Source | Type | Description | License / notes |
| --- | --- | --- | --- |
| [`openfootball/worldcup`](https://github.com/openfootball/worldcup) — `2026--canada-usa-mexico` | **Real · cached (live-refreshable)** | The actual 2026 field, 12-group draw, fixtures, results and knockout bracket (`cup.txt`, `cup_finals.txt`, `stadiums.csv`). The refresh script tries the current directory first and falls back to older names, so an upstream rename can't silently stale the data | **Public domain (CC0)** |
| [`martj42/international_results`](https://github.com/martj42/international_results) | **Real · cached** | Every men's international 1872→present (`results.csv`, `shootouts.csv`) — used to train the models and grow real Elo ratings | **Public domain (CC0)** |
| [English **Wikipedia**](https://en.wikipedia.org/) national-team squad templates | **Real · cached** | Current 26-player rosters for all 48 nations — name, shirt no., position, DOB/age, caps, goals, club (`data/source/squads_wikipedia.json`) | Text CC BY-SA 4.0; facts aren't copyrightable — Wikipedia credited here + in the app |
| [English **Wikipedia**](https://en.wikipedia.org/) 2026 World Cup **match articles** | **Real · cached (live-refreshable)** | Per-player tournament stats — appearances, minutes, goals, yellow/red cards, GK clean sheets & goals conceded — parsed from the goalscorer lists + starting-XI/substitution tables (official FIFA match reports) by `ml/fetch_stats.py` into `data/source/player_stats_wikipedia.json`. Refreshed every run via the key-less MediaWiki API | Sporting facts uncopyrightable; article text CC BY-SA 4.0 — credited in the app |
| [Wikimedia **Commons**](https://commons.wikimedia.org/) portraits | **Real · cached** | 1,047 free-licensed player headshots (`public/headshots/`), each with author + licence + source page (`data/source/headshot_credits.json`) | **Only free licences kept** (CC0 / public domain / CC BY / CC BY-SA); per-photo attribution shown in the UI |
| 48-team Elo priors & brand colours | **Curated** | Approximate starting Elo and team colours in `ml/common.py` | Curated from public knowledge |
| Per-player ability **rating** (0–100) | **Generated** | A single seeded skill score per player (from caps, role, club), used only as one squad-strength input — clearly labelled in the UI. **Assists, xG/xA and other advanced metrics have no free source and are omitted (shown as “—”), never fabricated** | Synthetic — deterministic (`SEED = 2026`) |
| Country flags | **Static** | `flag-icons` public-domain SVG sprites | MIT / public domain |

**Are these live, cached, sample or generated?**
The tournament data (field, draw, fixtures, results, bracket), the training history, **the
squads and the per-player tournament stats** are all **real** and shipped **cached** in
`data/source/` (plus committed headshots in `public/headshots/`). Everything is fetched over
plain HTTPS from public repos / MediaWiki APIs — nothing is scraped from disallowed
endpoints, and no login-gated or paid dataset is used. The **only** model-generated player
field is the 0–100 ability **rating** (deterministic, seeded), used as one squad-strength
input. Refresh with `python ml/refresh.py` (results **and** player stats) and
`npm run data:players` (squads/headshots).

**Real squads.** The 26-player roster for each of the 48 nations comes from that nation's
maintained English-Wikipedia squad template (`{{nat fs … player}}`) — real names, shirt
numbers, positions, dates of birth/ages, caps, international goals and clubs. Facts like a
player's name or club aren't copyrightable; Wikipedia is credited regardless.

**Real player stats.** Per-player tournament numbers — **appearances, minutes, goals,
yellow/red cards, and goalkeeper clean sheets / goals conceded** — are parsed by
`ml/fetch_stats.py` from the English-Wikipedia 2026 match articles, which transcribe the
official FIFA match reports (goalscorer lists + starting-XI/substitution tables). Each
scorer/lineup entry is joined to a squad player by exact Wikipedia article title, so the
golden-boot race and every per-match log are the genuine results. Players who haven't
featured show **real zeros**. A per-match log on each profile shows opponent, result,
minutes, goals and cards for every appearance.

**Player headshots.** Per the build requirements, headshots are used **only** when the
Wikimedia Commons file carries a **free licence** (public domain / CC0 / CC BY / CC BY-SA).
That yields **1,047 of 1,248** players; the remaining 201 fall back to clean initials
avatars, so the UI never breaks on a missing image. Each kept photo stores its **author,
licence and Commons source page**, shown as attribution on the player profile (CC BY-SA
requires attribution). Non-free or missing images are never downloaded.

**Known limitation — advanced stats.** **Assists, expected goals (xG/xA), shots, passing
and tackling are not published in any free, openly-licensed World Cup source.** Rather than
fabricate them, they are omitted and shown as “—” in the UI. Only the 0–100 ability
**rating** is model-generated (seeded from the real identity: caps, position, club tier) —
clearly flagged. Everything else about players (identity, photo, appearances, minutes,
goals, cards, GK stats) and all match outcomes are real.

**How to refresh.** Run `python ml/refresh.py` (downloads the CC0 results **and** the real
player stats, then rebuilds), or `npm run data:refresh` to rebuild from caches offline; or
click the **“Data · &lt;date&gt;”** control in the top nav (on any page) or **Refresh data** on
the Data & Methodology page (dev / `ALLOW_DATA_REFRESH=1`). For
squads/headshots run `npm run data:players` (or `python ml/refresh.py --players` to fetch
*and* rebuild). All refresh paths use **no API keys** and **no paid services**, with an
offline fallback to the committed caches.

**Licensing note.** This project respects site terms of service, `robots.txt`, rate limits
and dataset licensing. The two match/result datasets are **CC0 1.0 (public domain)**;
Wikipedia squad + match text is **CC BY-SA 4.0** (the underlying sporting facts aren't
copyrightable) and every headshot is **free-licensed with per-photo attribution retained**.
The seeded ability ratings and public-domain flag sprites carry no third-party
data-licensing obligations.

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
  result is read. Only **completed** matches (all 104, now that the tournament has
  finished) are used for evaluation;
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
npm test                                   # 41 Vitest tests
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

- **Real stats, one generated field.** Squads, headshots **and** per-player tournament
  stats (appearances, minutes, goals, cards, GK clean sheets / goals conceded) are **real**
  — parsed from Wikipedia squad templates and the official FIFA match reports. The **only**
  model-generated player field is the 0–100 ability **rating** (deterministic, seeded),
  clearly flagged in the UI.
- **No advanced metrics.** Assists, xG/xA, shots, passing and tackling are **not published
  in any free World Cup source**, so they are omitted and shown as “—” rather than
  fabricated.
- **Partial headshot coverage.** 1,047 of 1,248 players have a free-licensed Commons photo;
  the remaining 201 show clean initials avatars (no non-free images are used).
- **Live-tracked state.** The tournament state reflects whatever results are present in
  the cached source (the 2026 tournament is now **complete** — all 104 matches played;
  **Spain are champions**, beating Argentina 1–0 a.e.t. in the final). Click the
  **“Data · &lt;date&gt;”** control in the top nav (on any page) — or run
  `python ml/refresh.py` — to re-pull the latest results and player stats from upstream;
  the whole dashboard updates in place, with no code change. If a source can't be reached,
  the refresh log now says so explicitly rather than silently serving a stale cache.
- **Backtest size.** Model metrics are computed on the completed World Cup matches (all
  104), so differences between models are modest.
- **Knockout ties after 90 minutes.** Extra-time and penalty results are shown with the
  real advancing side highlighted and an “a.e.t. / pens” note, while the models are still
  scored on the regulation-time 1X2 outcome (no extra-time luck) to stay leakage-free.

---

## Future improvements

- Optional live ingestion from a free/open football-data source (behind the `.env`
  flags already scaffolded).
- Openly-licensed **advanced** per-player metrics (assists, xG, shots) if a
  redistributable source appears — the real base stats (goals, minutes, cards) are already
  wired in.
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
tournament bracket come from **public-domain (CC0)** datasets; **player squads, headshots
and tournament stats are real** (English Wikipedia / Wikimedia Commons, free-licensed with
attribution — player stats parsed from the official FIFA match reports), while only the
0–100 ability **rating** is generated for demonstration and predictions are **statistical
estimates, not guarantees**. Country flags are public-domain assets from `flag-icons`.
Player headshots are used only under free licences (CC0 / public domain / CC BY / CC BY-SA)
with per-photo attribution shown in the app; players without a free-licensed photo show a
clean initials avatar.
