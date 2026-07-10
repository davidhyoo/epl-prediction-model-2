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
Final). A single seeded simulation fills the tournament so the app always has a
coherent, end-to-end state to render.

Predictions are produced by **five independent models**. Each model scores *every*
match **before** any real result is read; completed matches are then used **only** for
backtesting and re-ranking (see [Leakage prevention](#leakage-prevention--self-improvement)).
Championship odds come from a **20,000-run Monte Carlo** simulation of the remaining
knockout stage; eliminated teams are pinned to **0%**.

Because live football data behind a login/paywall isn't used, all match history,
squads and player statistics are **deterministically generated demo data**. This keeps
the project reproducible and legally clean while still exercising a realistic
data-engineering + ML workflow. See [Data sources](#data-sources).

Current generated snapshot (regenerate any time with `python ml/pipeline.py`):

| Metric | Value |
| --- | --- |
| Tournament | 2026 FIFA World Cup (USA · Canada · Mexico) |
| Matches | 104 total — 72 completed, 32 upcoming |
| Teams / Players | 48 / 1,248 |
| Models | 5 (Elo, Logistic Regression, Random Forest, XGBoost, Ensemble) |
| Engineered features | 10 |
| Training matches (synthetic history) | 4,200 |
| Top predicted champion | 🇪🇸 Spain (~28%) |
| Best backtest model | Random Forest |

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
- **Players** — Searchable, sortable, filterable table of all 1,248 players with clean
  placeholder avatars, position, club, age, rating and rich stats. Player profiles add
  a stats table, form trend and a team-contribution score.
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
│  ├─ tournament.py            # 48-team schedule + knockout structure
│  ├─ ingest.py                # raw data generation (history, WC, squads)
│  ├─ transform.py             # validation + cleaning
│  ├─ features.py              # feature engineering (leakage-safe)
│  ├─ modeling.py              # Elo baseline, ensemble, metrics, calibration
│  ├─ train.py                 # train LogReg / RF / XGB (+ draw model)
│  ├─ predict.py               # per-model predictions, factors, rankings, Monte Carlo
│  ├─ evaluate.py              # backtest, re-weight ensemble, assemble frontend JSON
│  ├─ pipeline.py              # one-command orchestrator
│  ├─ models/                  # trained model artifacts (git-ignored)
│  └─ tests/test_ml.py         # Python unit tests
├─ data/
│  ├─ raw/  processed/  cached/  # pipeline stages (generated)
├─ public/
│  └─ data/                    # cached JSON the frontend reads
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

The repo ships with pre-generated data in `public/data/`, so **you can run the app
immediately** without running the Python pipeline.

---

## Environment variables

**None are required.** The app runs fully offline out of the box.

A [`.env.example`](.env.example) documents *optional* variables for experimenting with
live-data ingestion (all blank/disabled by default). Copy it to `.env.local` if you
want to try them — `.env.local` is git-ignored and no secrets are ever committed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FOOTBALL_DATA_API_KEY` | *(empty)* | Optional free football-data API key |
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

Regenerate every cached JSON file the frontend reads (fully deterministic):

```bash
npm run data:refresh          # === python ml/pipeline.py
```

Run a single stage, or resume from a stage:

```bash
python ml/pipeline.py --from features    # resume at feature engineering
npm run ml:ingest                        # individual stages:
npm run ml:transform
npm run ml:features
npm run ml:train        # train the models
npm run ml:predict      # generate predictions + Monte Carlo odds
npm run ml:evaluate     # backtest, re-weight ensemble, write frontend JSON
```

Because everything is seeded (`SEED = 2026`), re-running the pipeline reproduces
identical outputs.

---

## The data pipeline

The pipeline is a classic staged data-engineering flow. Each stage reads the previous
stage's artifacts from `data/` and writes its own, ending in the cached JSON the app
consumes.

| # | Stage | Script | Output |
| --- | --- | --- | --- |
| 1 | **Ingest** | `ingest.py` | Raw synthetic history, WC schedule, squads → `data/raw/` |
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
| 48-team field, Elo ratings & colours | **Static (curated)** | Publicly known qualified nations, approximate Elo ratings and brand colours | Curated from public knowledge; used for demo purposes |
| International match history (2019–2025) | **Generated** | ~4,200 deterministically simulated internationals used to *train* the models | Synthetic — no real fixtures |
| Squads & player statistics | **Generated** | 1,248 players with positions, clubs, ratings and stats | Synthetic — names/clubs are generated, not real people |
| Country flags | **Static** | `flag-icons` public-domain SVG sprites | MIT / public domain |
| Player headshots | **Placeholder** | Clean initials-based avatars | No real photos used (see below) |

**Are these live, cached, sample or generated?**
All modelling data is **generated** (deterministically, from `SEED = 2026`) and shipped
**cached** in `public/data/`. Nothing is scraped and no login-gated or paid dataset is
used.

**Player headshots.** Per the build requirements, real headshots are only used when
legally and openly licensed. Reliable, openly licensed headshots for a full 1,248-player
field are not available, so the app shows **clean placeholder avatars** (coloured
initials) everywhere. This never breaks the UI when an image is missing.

**How to refresh.** Run `python ml/pipeline.py` (or `npm run data:refresh`). To wire in
a real, free/open source, implement the fetch in `ml/ingest.py` behind the optional
`.env` flags and re-run the pipeline — the downstream stages and the frontend contract
stay the same.

**Licensing note.** This project respects site terms of service, `robots.txt`, rate
limits and dataset licensing. Because it uses only generated + public-domain assets, it
carries no third-party data-licensing obligations.

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

- **Train/evaluate separation.** Models are trained on the synthetic 2019–2025 history,
  never on World Cup matches.
- **Predict before scoring.** Every model predicts *all* 104 matches before any real
  result is read. Only the 72 **completed** group matches are used for evaluation;
  upcoming knockout matches carry `score: null` in the cached data, so results can't
  leak into the UI either.
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

- **Generated data.** Match history, squads and player stats are synthetic. Absolute
  numbers (e.g., a player's goal tally) are illustrative, not real. The *methods* —
  pipeline, features, models, evaluation — are the point.
- **Placeholder headshots.** No real player photos are used (licensing); avatars are
  coloured initials.
- **Fixed cutoff.** The tournament state is frozen at the end of the group stage
  (2026-06-27): 72 completed, 32 upcoming. There is no live in-tournament updating.
- **Backtest size.** Model metrics are computed on 72 completed matches, so differences
  between models are modest and can shift when the data is regenerated with a new seed.
- **Knockout participants are projected.** Round-of-16-and-beyond slots marked *(proj.)*
  depend on results not yet played and update as the bracket resolves.

---

## Future improvements

- Optional live ingestion from a free/open football-data source (behind the `.env`
  flags already scaffolded).
- Real, openly licensed player headshots where available, with graceful fallback.
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
endorsed by, or associated with FIFA or any football federation. Team, player and match
data are **generated for demonstration** and predictions are **statistical estimates,
not guarantees**. Country flags are public-domain assets from `flag-icons`; no real
player photographs are used.
