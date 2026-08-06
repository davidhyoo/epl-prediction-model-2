# ⚽ Data Driven Soccer — EPL & La Liga Prediction & Analytics Dashboard

_Developed by **David Yoo** — [LinkedIn](https://www.linkedin.com/in/david-h-yoo) · [GitHub](https://github.com/davidhyoo/epl-prediction-model-2)_

A production-quality web app for exploring the **English Premier League** and
**Spanish La Liga** — standings, fixtures & results, match predictions, club
profiles, real squads with headshots, player stats, multi-view rankings and a
transparent machine-learning model leaderboard — backed by a fully reproducible,
**offline-first** Python ML pipeline that pulls only free, openly-licensed data.

> **Branch:** `soccer-agent` (a sibling of the `worldcup-prediction` World Cup
> agent, rebuilt for club football with a cleaner, more futuristic UI).

It is built to run end-to-end **with no API keys, no paid services and no cloud
dependency**. Every number in the UI is produced locally by the pipeline and
committed as JSON under `public/data/**`, so a fresh clone renders instantly.

---

## Table of contents

1. [Two-season strategy: validate on 2025-26, ship 2026-27](#two-season-strategy)
2. [Features](#features)
3. [Tech stack](#tech-stack)
4. [Quick start](#quick-start)
5. [Project structure](#project-structure)
6. [The data pipeline — the eight "agents"](#the-data-pipeline--the-eight-agents)
7. [The models](#the-models)
8. [Feature engineering & leakage safety](#feature-engineering--leakage-safety)
9. [The Refresh function (how it works + how to debug it)](#the-refresh-function)
10. [Data sources & licensing](#data-sources--licensing)
11. [Testing](#testing)
12. [Environment variables](#environment-variables)
13. [Known limitations](#known-limitations)
14. [Future improvements](#future-improvements)
15. [Original Build Prompt](#original-build-prompt)

---

## Two-season strategy

Football data is only trustworthy if the pipeline that produces it has been
proven against **real, completed results**. So the app ships **two seasons per
league** and you can switch between them live (top-left league + season switcher):

| Season    | Role          | State                                   | Why it exists                                             |
| --------- | ------------- | --------------------------------------- | --------------------------------------------------------- |
| `2025-26` | **validation**| complete — real results + scorers       | Proves the ingest → features → predict → evaluate loop is correct against ground truth. |
| `2026-27` | **deliverable**| fixtures only (season not yet kicked off)| The real target. Predictions are made **pre-season** from priors; as the season is played, hitting **Refresh** flows real results straight into standings, odds and the model leaderboard. |

This is the core idea the brief asked for: **use 2025-26 to guarantee the plumbing
works, and have 2026-27 fully wired so that the moment the league kicks off the
same refresh path produces correct, live data** — no code changes required.

Datasets available in the app:

```
epl/2025-26      epl/2026-27
laliga/2025-26   laliga/2026-27
```

---

## Features

Every page is league- and season-aware (state lives in the URL as
`?league=epl&season=2025-26`, so any view is shareable/bookmarkable).

- **Home dashboard** — summary cards (matches played/upcoming, predicted
  champion, highest-confidence upcoming fixture, best-performing model), the live
  standings snapshot, title-race odds and recent/upcoming fixtures.
- **Matches** — full 380-match fixture/results list with club badges, kickoff
  times, scores for completed games and **W / D / L probability bars** for
  upcoming ones. Filter by round/completed/upcoming/club; sort by date,
  confidence or round. Click any prediction to open the **explanation modal**.
- **Prediction explanation modal** — the six models' probabilities for that
  fixture, the ensemble's pick and confidence, and the **top-5 contributing
  factors** (Elo gap, recent form, attack/defence, shots-on-target trend, rest,
  head-to-head) with direction and magnitude. Clearly labelled as estimates.
- **Table** — the classic league table (P/W/D/L/GF/GA/GD/Pts) with form pills
  and promotion/UCL/Europa/relegation zone colouring.
- **Predictions** — season-outcome projections from the Monte-Carlo simulation:
  title %, top-4/UCL %, Europa %, relegation %, plus expected finishing position.
- **Clubs** — searchable/sortable grid of all 20 clubs with title odds; click
  through to a **club detail** page: strength radar, SWOT-style
  strengths/weaknesses, key players, full squad and the club's fixtures.
- **Players** — every real squad player, with **Wikimedia-licensed headshots**
  (or a clean initials placeholder), club, position, nationality flag, goals and
  a model rating. Search by name; filter by club/position; sort by any stat.
  Click through to a **player profile** with a stat table and attribution.
- **Rankings** — eight ranking views: championship odds, team strength, recent
  form, attack, defence, squad strength, model confidence and momentum.
- **Models** — the model **leaderboard** ranked by accuracy, with log-loss,
  Brier score, average confidence, calibration (ECE), games evaluated and the
  current ensemble weights. For the unplayed 2026-27 season these are
  intentionally blank until real results exist to score against.
- **Methodology** — a plain-English walk-through of the eight pipeline stages,
  the models, the leakage-safety guarantees and the self-improvement loop.
- **Refresh data button** — rebuilds all data from the newest public sources
  without touching code (see [The Refresh function](#the-refresh-function)).
- **UX polish** — dark, futuristic theme; responsive layout; command palette
  (⌘K / Ctrl-K); skeleton loaders, empty states and error states; accessible
  contrast; tooltips on technical metrics; graceful handling of every missing
  photo/stat so the UI never crashes on absent data.

---

## Tech stack

| Layer            | Choice                                                              |
| ---------------- | ------------------------------------------------------------------- |
| Frontend         | **Next.js 16 (App Router)** + **React 19** + **TypeScript**         |
| Styling          | **Tailwind CSS v4** with a custom dark design system                |
| Charts           | **Recharts** (radars, calibration, bars)                            |
| Data (runtime)   | Static JSON under `public/data/**` — read server-side, cached       |
| ML / data        | **Python 3** + **NumPy** + **scikit-learn** (+ **XGBoost** if present) |
| Persistence      | Committed JSON + joblib model artifacts (no database needed)         |
| Frontend tests   | **Vitest** (+ react-dom/server for component rendering)             |
| Pipeline tests   | **pytest**                                                           |
| Lint             | **ESLint** (Next core-web-vitals config)                            |

---

## Quick start

### Prerequisites

- **Node.js 20+** (built and tested on Node 22)
- **Python 3.10+** with `numpy`, `scikit-learn`, `joblib` (and optionally
  `xgboost`). Install with:
  ```bash
  pip install numpy scikit-learn joblib xgboost
  ```

### Install & run

```bash
# 1. install JS dependencies
npm install

# 2. start the dev server (in-app refresh is enabled automatically here)
npm run dev
# open http://localhost:3000

# — or — a production build:
npm run build
npm run start
```

The app renders immediately from the committed JSON — **you do not need to run
the Python pipeline to view it.** Run the pipeline only when you want to refresh
or regenerate data (see below).

> **Windows note:** if `node`/`npm` aren't on your PATH, this repo was validated
> with a portable Node at
> `C:\Users\<you>\AppData\Local\node-portable\node-v22.11.0-win-x64`. Prepend it
> to PATH for the session:
> ```powershell
> $nd="C:\Users\<you>\AppData\Local\node-portable\node-v22.11.0-win-x64"
> $env:PATH="$nd;$env:PATH"
> ```

### Data / model commands

```bash
npm run data:refresh        # python ml/club_pipeline.py — rebuild all JSON from cache
npm run data:retrain        # python ml/club_pipeline.py --retrain — force model re-fit
npm run data:fetch          # python ml/club_refresh.py — pull latest sources, then rebuild
npm run data:fetch:offline  # python ml/club_refresh.py --offline — rebuild without network
npm run data:fetch:squads   # python ml/club_refresh.py --squads — also refresh squads + headshots
npm run data:fetch:crests   # python ml/club_refresh.py --crests — re-map club crest URLs
npm run ml:train            # stage 4 only
npm run ml:predict          # stage 5 only
npm run ml:simulate         # stage 6 only
npm run ml:evaluate         # stage 8 (+ publish JSON, incl. EPL assist enrichment)
```

### Tests / lint

```bash
npm test          # vitest — 79 frontend tests
npm run test:py   # pytest  — 48 pipeline tests
npm run lint      # eslint
```

---

## Project structure

```
epl-prediction-model-2/
├─ src/
│  ├─ app/                       # Next.js App Router pages (all league+season aware)
│  │  ├─ page.tsx                # home dashboard
│  │  ├─ matches/ table/ predictions/
│  │  ├─ clubs/  clubs/[code]/   # club grid + detail
│  │  ├─ players/ players/[id]/  # player grid + profile
│  │  ├─ rankings/ models/ methodology/
│  │  ├─ api/refresh/route.ts    # the in-app refresh endpoint (see below)
│  │  └─ layout.tsx              # nav (Suspense-wrapped), fonts, theme
│  ├─ components/                # explorers, match stack, charts, switchers, UI
│  └─ lib/
│     ├─ types.ts                # the frontend data contract (mirrors club_evaluate.py)
│     ├─ data.ts                 # server-side JSON loaders + selection helpers
│     ├─ format.ts               # pct/odds/label formatting + ranking metadata
│     ├─ league.ts               # league/season resolution + query-string helpers
│     └─ crests.json             # club-code → hot-link crest URL map (no images committed)
├─ ml/                           # the Python pipeline ("agents")
│  ├─ leagues.py                 # league/season/club registry, Elo constants, paths
│  ├─ nations.py                 # nationality → flag/name lookup for players
│  ├─ club_ingest.py             # stage 1 — build the corpus + target schedule
│  ├─ club_sources.py            # stage 2 — parse openfootball + football-data caches
│  ├─ club_features.py           # stage 3 — leakage-safe feature engineering
│  ├─ club_train.py              # stage 4 — fit logreg / forest / xgb / draw models
│  ├─ club_predict.py            # stage 5 — per-match W/D/L probabilities + factors
│  ├─ club_simulate.py           # stage 6 — Monte-Carlo season simulation
│  ├─ club_players.py            # stage 7 — squads, goals from scorers, ratings
│  ├─ club_evaluate.py           # stage 8 — backtest + publish all public/data JSON
│  ├─ club_fpl.py                # EPL assist/minute/card enrichment (Fantasy PL archive)
│  ├─ club_crests.py             # verified club-crest URL mapper → src/lib/crests.json
│  ├─ club_fetch_squads.py       # Wikipedia/Commons squad + headshot fetcher
│  ├─ club_refresh.py            # source downloader + pipeline runner (the refresh brain)
│  ├─ club_pipeline.py           # orchestrator (ingest→…→publish)
│  └─ tests/                     # pytest suite (modeling, features, sources, simulate, fpl, crests)
├─ data/                         # pipeline working area (NOT read at runtime)
│  ├─ source/{league}/{season}/  # cached openfootball.txt + footballdata.csv + fpl_players.csv
│  ├─ source/{league}/           # squads_wikipedia.json + headshot_credits.json
│  ├─ source/crests.json         # cached, verified club-crest URL map
│  └─ raw/{league}/{season}/     # ingest.json intermediate
├─ public/
│  ├─ data/                      # ← the frontend reads THIS
│  │  ├─ index.json              # dataset catalogue + default selection
│  │  └─ {league}/{season}/      # summary, standings, matches, models, clubs, players, rankings
│  └─ headshots/{league}/        # committed player headshots (epl/, laliga/)
├─ tests/                        # vitest suite (format, model-meta, data-integrity, probability-bar)
├─ .env.example
└─ README.md
```

---

## The data pipeline — the eight "agents"

The pipeline is a chain of small, single-responsibility modules ("agents"), each
a pure function of the stage before it. It is **deterministic** (fixed seed
`2026`) and **offline** (reads only cached source files), so the same inputs
always produce the same JSON. `club_pipeline.py` orchestrates them:

```
ingest → (sources) → features → train → predict → simulate → players → evaluate → publish
```

| # | Module              | Responsibility |
| - | ------------------- | -------------- |
| 1 | **`club_ingest.py`**   | Assemble, per (league, season), the **training corpus** (completed matches from seasons *strictly earlier* than the target) and the **target schedule** (the season being predicted). This separation is what prevents leakage — the training corpus can never contain a match that will later be evaluated. Writes `data/raw/{league}/{season}/ingest.json`. |
| 2 | **`club_sources.py`**  | Pure parsers (no network) for the two cached formats: **openfootball `.txt`** (schedule, results, and 2025-26+ inline goalscorers with minutes, penalties & own goals) and **football-data.co.uk CSV** (shots, shots-on-target, corners, fouls, cards and closing market odds). Handles all three openfootball line layouts (newer score, older `v` score, fixture-only) and merges the two sources per fixture. |
| 3 | **`club_features.py`** | A single chronological engine walks every match in date order and emits, for each fixture, a feature vector computed **only from matches that kicked off before it**: Elo gap, home advantage, recent form, attack/defence rates, shots-on-target trend, rest days and head-to-head. Elo is grown from real results and regressed 25% toward 1500 across each summer break. See [leakage safety](#feature-engineering--leakage-safety). |
| 4 | **`club_train.py`**    | Fit the learners on the **training corpus only**: multinomial **logistic regression**, **random forest**, **XGBoost** (falls back to sklearn gradient boosting if xgboost isn't installed) and the auxiliary binary **draw model** used by the Elo baseline. Artifacts saved to `ml/models/{league}-{season}/*.joblib` + `meta.json`. Training is the only reusable step, so it is skipped on refresh unless `--retrain` is passed. |
| 5 | **`club_predict.py`**  | Score the whole target schedule with every model, blend them into the **ensemble**, pick the predicted outcome + confidence, and attach the **top-5 contributing factors** (from model coefficients / feature importances) for the explanation modal. Also computes per-club team-strength snapshots. |
| 6 | **`club_simulate.py`** | **Monte-Carlo** the rest of the season (8,000 runs by default): completed matches are fixed to their real result; each remaining fixture is sampled from an independent-Poisson score model driven by the current Elo gap. Produces title / UCL / Europa / relegation probabilities, expected points and the full finishing-position distribution. Mathematically-eliminated clubs are **hard-zeroed** (an eliminated side has exactly 0% title chance). |
| 7 | **`club_players.py`**  | Build each club's squad from the cached Wikipedia rosters, credit goals from the parsed scorers (excluding own goals), and compute a transparent player **rating** from goals, position and squad role. |
| 8 | **`club_evaluate.py`** | The **self-improvement / backtest** step. For the validation season it grades every completed prediction against the real result, computes accuracy, log-loss, Brier score and calibration (ECE) per model, **re-ranks** the leaderboard and sets the ensemble weights ∝ 1/log-loss (better models get more say). It also invokes `club_fpl.py` to enrich EPL players with real assists/minutes/cards. Then it **publishes** every `public/data/{league}/{season}/*.json` and the top-level `index.json`. For the unplayed 2026-27 season it publishes blank metrics (nothing to score yet). |

`club_fetch_squads.py` is a separate, network-using helper (run via
`--squads`) that fetches rosters from Wikipedia and free-licensed headshots from
Wikimedia Commons, caching both under `data/source/{league}/` and writing images
to `public/headshots/{league}/`. It is decoupled from the daily refresh because
squads change rarely and image fetching is slow.

Two more helpers run alongside stage 8:

- **`club_fpl.py`** merges real **assists, minutes and cards** into the Premier
  League player list from the free, key-less [Fantasy Premier League archive](https://github.com/vaastav/Fantasy-Premier-League).
  Goals stay sourced from openfootball; only the missing fields are filled, by
  accent-folded `(club, surname, first-initial)` matching. A player is only
  enriched if they actually featured (`minutes > 0`), and the whole step is
  skipped for a season with no completed matches so an unstarted 2026-27 never
  inherits last season's totals. La Liga has no equivalent free feed, so it is a
  no-op there and those fields stay `null`.
- **`club_crests.py`** builds the club-code → crest-URL map. Each candidate URL
  (from TheSportsDB's free-key name search, with a football-data.org CDN
  fallback) is **verified** — the returned team must resolve back to the same
  club, country and sport — so a badge can never be silently mis-attributed. Only
  the *URLs* are stored (`data/source/crests.json` → `src/lib/crests.json`); no
  crest image is committed, and the UI falls back to a coloured monogram whenever
  a crest can't load. Re-map with `npm run data:fetch:crests`.

---

## The models

Six models feed the leaderboard and every prediction (fixed class order:
`0 = home win, 1 = draw, 2 = away win`):

| Model         | Type                         | Notes |
| ------------- | ---------------------------- | ----- |
| **Market**    | analytic baseline            | Normalised bookmaker closing odds → probabilities. A strong, hard-to-beat reference. |
| **Elo**       | analytic baseline            | World-Football-Elo-style ratings + a fitted draw model. No training beyond the draw split. |
| **Logistic**  | multinomial logistic reg.    | Linear, interpretable; its coefficients drive several "top factor" explanations. |
| **Forest**    | random forest                | Captures non-linear feature interactions. |
| **XGBoost**   | gradient boosting            | Usually the strongest learner; falls back to sklearn GBDT if xgboost is absent. |
| **Ensemble**  | weighted blend               | Combines the base learners with weights ∝ 1/log-loss, re-learned each backtest. This is the model shown as the headline prediction. |

**Self-improvement loop:** `club_evaluate.py` scores each model on the completed
matches, re-ranks them by accuracy, and updates the ensemble weights from their
log-losses — so as more of a season is played (and you hit Refresh), the blend
automatically shifts toward whichever models are actually calibrated for that
league/season. Persistently weak models sink down the leaderboard, visibly.

---

## Feature engineering & leakage safety

Leakage (letting a match's own result influence its features) is the single
biggest way a football model can look great in backtests and fail live. Three
guarantees prevent it here, and each is pinned by a test:

1. **Chronological engine.** For each fixture, features are computed **before**
   the engine observes that fixture's result. A fixture's own goals never enter
   its own feature vector — proven by
   `test_features_do_not_depend_on_the_matchs_own_result`.
2. **Train on the strict past only.** The training corpus (`club_ingest.py`)
   contains only seasons *earlier* than the target, so a model can never train on
   a match it will later be evaluated on.
3. **Evaluate on completed matches only.** The leaderboard is built purely from
   games whose real result exists; upcoming games contribute predictions but
   never grades. For an unplayed season there are simply no grades yet.

The frontend `data-integrity.test.ts` independently re-checks this on the shipped
JSON: upcoming matches must carry **no** score and **no** graded outcome, while
completed matches must carry both and grade consistently.

---

## The Refresh function

This is the feature to understand first when something looks stale, so it is
documented in depth. The goal: **click one button in the UI and have every number
re-derive from the newest public data — with zero code changes.**

### The full path of a click

```
[Refresh data] button (src/components/refresh-data-button.tsx)
        │  POST /api/refresh          (the button always runs the default = live mode)
        ▼
src/app/api/refresh/route.ts     (Node.js runtime, force-dynamic)
        │  reads optional ?mode=offline|squads, then
        │  spawn(python, ["ml/club_refresh.py", ...flags], { shell:false })
        ▼
ml/club_refresh.py               (download sources → run pipeline)
        │  for each (league, season): fetch openfootball.txt + footballdata.csv
        │  then: club_pipeline.run(...)
        ▼
ml/club_pipeline.py              ingest → features → (train?) → predict → simulate → players → evaluate
        │
        ▼
public/data/**/*.json  rewritten
        │
        ▼
route.ts calls revalidatePath("/", "layout")   ← purges the cached pages
        │
        ▼
next request re-reads the new JSON → the UI reflects reality
```

### The three refresh modes

- **`live` (default)** — this is what the **in-app button** runs. Downloads the
  latest openfootball results/scorers and football-data stats/odds for every
  league+season, then rebuilds all JSON. This is what pulls in "a match that
  finished since the last refresh".
- **`offline`** — skips all network calls and rebuilds purely from the committed
  caches. Use it to prove the pipeline works with no internet, or to rebuild
  after editing a cached source file by hand. Reachable via `?mode=offline`
  (e.g. `curl -X POST '.../api/refresh?mode=offline'`) or `npm run data:fetch:offline`.
- **`squads`** — additionally re-fetches Wikipedia rosters and Wikimedia
  headshots. Slow (several minutes); run occasionally, not on every result.
  Reachable via `?mode=squads` or `npm run data:fetch:squads`.

A fourth, standalone maintenance flag — **`--crests`** (`npm run
data:fetch:crests`) — re-verifies and re-maps every club's crest URL. It is not
part of the daily refresh because crests essentially never change; run it only
when a club is promoted/relegated into a league.

### Safety & robustness (why it won't corrupt your data)

- **Disabled by default in production.** The route only runs when
  `NODE_ENV !== "production"` (i.e. `next dev`) **or** `ALLOW_DATA_REFRESH=1` is
  set. Shelling a child process from a web request is only safe on a machine you
  trust.
- **No shell injection.** The command and its args are constants defined in the
  repo; `spawn(..., { shell: false })` runs Python directly with **no** user
  input interpolated.
- **Single-flight.** A module-level `running` flag rejects a second click with
  HTTP 409 while a refresh is in progress, so two clicks can't launch two
  overlapping pipelines.
- **12-minute timeout.** A stuck download is SIGKILLed and reported rather than
  hanging the request forever.
- **Atomic, sanity-checked downloads.** `club_refresh.py` writes each file to a
  temp path, checks its size + an expected marker, and only then swaps it in —
  so a truncated or error-page download **never** overwrites a good cache.
- **Offline fallback baked in.** If a download fails, the committed cache is kept,
  a visible `WARNING` is printed, and the pipeline still rebuilds end-to-end.
- **New-season resilient.** football-data.co.uk only publishes a division CSV
  *after* a season kicks off, and the 2026-27 openfootball file starts with
  fixtures and no results. Both are expected; a missing football-data file for an
  unstarted season is never fatal.

### Debugging checklist (if Refresh "doesn't update")

The route returns JSON with the **last 12 lines** of the pipeline log and a
`durationMs`; open DevTools → Network → `refresh` to read it. Then:

| Symptom | Likely cause / fix |
| ------- | ------------------ |
| **HTTP 403** `disabled in this environment` | You're on a production build. Set `ALLOW_DATA_REFRESH=1` (and restart), or use `npm run dev`. |
| **HTTP 409** `already in progress` | A refresh is still running; wait for it to finish. |
| **HTTP 500** `Could not launch Python (ENOENT)` | Python isn't on PATH for the server process. Set `PYTHON_BIN` to your interpreter (e.g. `py`, `python3`, or an absolute venv path). |
| **500** `exited with code N` | The pipeline itself failed — read the `log` array. Usually a missing Python dep (`pip install numpy scikit-learn joblib`) or an unreadable cache. |
| **`timed out after 720s`** | A slow network fetch. Retry, or use `mode=offline` to rebuild from cache. |
| **Returns `ok:true` but numbers look unchanged** | (a) The source genuinely hasn't updated yet (results appear in openfootball a short while after full-time). (b) You're on the wrong league/season — check the `?league=&season=` in the URL. (c) A stale browser view — the server data is fresh; a hard reload re-fetches it. |
| **A finished match still shows as "upcoming"** | The upstream openfootball file hasn't published that result yet, **or** you refreshed `offline`. Try `mode=live`. Verify the raw source updated at the GitHub URLs in `club_refresh.py`. |
| **Headshots missing after refresh** | A normal `live`/`offline` refresh does **not** touch squads. Run `npm run data:fetch:squads` (or `mode=squads`) to re-fetch rosters + images. |

Because the whole thing is just "download public files → rerun a deterministic
pipeline → rewrite JSON → revalidate", you can always reproduce exactly what the
button does from a terminal:

```bash
npm run data:fetch            # == mode=live
npm run data:fetch:offline    # == mode=offline
```

and diff `public/data/**` to see precisely what changed.

---

## Data sources & licensing

All sources are free, public and key-less. Nothing here requires a login,
payment, or scraping of disallowed content.

| Source | Used for | License | Live/cached |
| ------ | -------- | ------- | ----------- |
| **openfootball** ([github.com/openfootball](https://github.com/openfootball)) — `england/1-premierleague.txt`, `espana/1-liga.txt` | Fixtures, results, and (2025-26+) inline goalscorers with minutes/penalties/own-goals | **CC0** (public domain) | Cached; refreshable live |
| **football-data.co.uk** (`mmz4281/{yyyy}/{E0,SP1}.csv`) | Per-match shots, shots-on-target, corners, fouls, cards + **closing market odds** | Free for personal use | Cached; refreshable live |
| **Fantasy Premier League archive** ([vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League)) — `data/{season}/players_raw.csv` | Real per-player **assists, minutes, yellow/red cards** for the Premier League (goals stay sourced from openfootball) | Open GitHub data, snapshot of the public FPL API | Cached in `data/source/epl/{season}/fpl_players.csv`; refreshable live |
| **Wikipedia** (club squad pages) | Player rosters (name, position, nationality, club) | CC BY-SA | Cached; refreshable via `--squads` |
| **Wikimedia Commons** | Player **headshots** (free-licensed images only) | Per-file (CC BY / CC BY-SA / public domain) — attribution stored in `headshot_credits.json` and shown on player profiles | Cached in `public/headshots/{league}/` |
| **TheSportsDB** (free key `3`) + **football-data.org crest CDN** | Club **crest** image URLs (verified by name + country, never the wrong club) | Hot-linked at render only — **no crest image is ever committed**; each club falls back to a coloured monogram if the image can't load | URL map cached in `data/source/crests.json` → bundled to `src/lib/crests.json`; refreshable via `--crests` |

**How to refresh:** see [The Refresh function](#the-refresh-function). In short:
in-app button (dev, or `ALLOW_DATA_REFRESH=1`), or `npm run data:fetch`
(live) / `data:fetch:offline` (cache-only) / `data:fetch:squads` (rosters+images).

**Licensing notes:** only free-licensed headshots are used; where a properly
licensed image isn't available, the UI shows a clean initials placeholder instead
of an unlicensed photo. Every headshot's author + license + source URL is stored
and surfaced in the app. **Club crests are trademarks**, so no crest image is
committed to this repository — the app only stores a hot-link *URL* per club
(`src/lib/crests.json`) and renders it as an `<img>` at view time, falling back to
a coloured monogram whenever the image is unavailable (offline, CDN hiccup, or an
unmapped club).

---

## Testing

**127 tests total**, all green, split across the two toolchains:

### Frontend — Vitest (`npm test`) — 79 tests

- `tests/format.test.ts` — percentage/odds/label formatting helpers.
- `tests/model-meta.test.ts` — model registry ordering & metadata.
- `tests/probability-bar.test.tsx` — the W/D/L bar, rendered to static markup
  with `react-dom/server` (keeps the suite in a fast plain-Node environment).
- `tests/data-integrity.test.ts` — iterates **every** shipped dataset and
  asserts: 20 clubs / 380 matches, probabilities that sum to 1, **no leakage**
  (upcoming games carry no result), consistent grading, valid standings maths,
  season-odds in `[0,1]` with title odds summing to ~1, a correctly-ranked model
  leaderboard, calibration bins in range, well-formed & attributed headshots, and
  all eight ranking views. Preseason (2026-27) vs validation (2025-26) datasets
  are checked with the appropriate expectations.

### Pipeline — pytest (`npm run test:py`) — 48 tests

- `test_club_modeling.py` — Elo baseline (rows sum to 1, monotonic in rating gap,
  home-advantage tie-break, draw-model coupling), ensemble blending, and the
  metrics (accuracy, log-loss, Brier, calibration/ECE, inverse-log-loss weights,
  importance normalisation).
- `test_club_features.py` — outcome labelling, first-fixture neutrality, the
  **no-self-leakage** invariant, zero-sum Elo updates, form/H2H accumulation,
  chronological training-matrix construction and the summer Elo regression.
- `test_club_sources.py` — all three openfootball line layouts, the goalscorer
  grammar (penalties, own goals, stoppage time, multi-goal players), and the
  football-data CSV parser (stats + **normalised** market odds).
- `test_club_simulate.py` — standings accumulator maths, expected-goals ordering,
  valid probability distributions, and the **"eliminated ⇒ 0% title"** guarantee.
- `test_club_fpl.py` — the real-assists enrichment: surname + first-initial name
  matching, the "did the player actually feature" gate, the La-Liga no-op, and the
  pre-season gate that stops an unstarted season inheriting last season's totals.
- `test_club_crests.py` — the crest **verification** guard (accepts spelling
  variants, rejects the wrong sport / country / club) so a badge is never
  mis-attributed.

Run everything:

```bash
npm run lint && npm test && npm run test:py && npm run build
```

---

## Environment variables

None are required to run, build or test the app. The two optional ones tune the
in-app refresh button (see [`.env.example`](.env.example)); the **Python pipeline
itself reads no environment variables and needs no API keys**.

| Variable             | Purpose                                                                 | Default |
| -------------------- | ----------------------------------------------------------------------- | ------- |
| `ALLOW_DATA_REFRESH` | Allow `POST /api/refresh` in a production build (auto-on in `next dev`). | unset (off in prod) |
| `PYTHON_BIN`         | Python interpreter for the refresh route if `python` isn't on PATH.     | `python` |

---

## Known limitations

- **2026-27 is pre-season.** Its predictions come from priors (Elo carried over
  from prior seasons + squad strength), and its model leaderboard is blank until
  real results exist to score against. This is by design — hit Refresh once the
  season starts and the numbers become live.
- **Player stats: EPL is rich, La Liga is goals-only.** openfootball provides
  goalscorers with minutes for both leagues. For the **Premier League** we
  additionally merge real **assists, minutes and cards** from the free, key-less
  Fantasy Premier League archive (goals still come from openfootball, the single
  source of truth). **La Liga has no equivalent free per-player feed**, so its
  assists/minutes stay `null` and the UI shows a tasteful "—". Both degrade
  gracefully; the app never invents a stat it can't source.
- **Crest coverage is near-complete, with a safe fallback.** 46/46 clubs across
  both leagues map to a real, verified crest URL; any club that ever can't load
  its crest simply shows a coloured monogram.
- **Match stats depend on football-data.co.uk cadence.** Shots/odds appear once a
  season is under way; before then those fields are empty.
- **Headshot coverage is partial.** Only players with a free-licensed Commons
  image get a photo; everyone else gets a clean initials avatar.
- **Refresh runs a local process.** It's meant for a trusted machine; it's off by
  default in production for that reason.

---

## Future improvements

- Per-player advanced stats (xG/xA) from an additional open feed.
- Live in-play polling during matches (currently result-level after full-time).
- A head-to-head club/player comparison tool and downloadable CSV exports.
- SHAP-based explanations to complement the current coefficient/importance factors.
- Extending the same pipeline to more leagues (Serie A, Bundesliga, Ligue 1) —
  the architecture is already league-parameterised.

---

## Original Build Prompt

> This branch (`soccer-agent`) was created from the following request. It is
> preserved verbatim for reference.

```
now please create a new branch called soccer-agent, and create something very
similar for English Premier League and Spain La Liga. I want to have all the
functionalities here from the world cup agent, have view for all the playerrs,
headshots, refresh functionality, have all the players, stats, win rate,
machine learning, everything.

First, imporve UI. Benchmark it from other well known leading websites to make
it more interactive, have a very clean, futuristic ui.

Second, make sure we have a very accurate data source, so that we are always
pulling the data. Do a deep reserach on where we would have to pull it from,
which player is in which team, who scored, who won, who got substituted.... To
evaluate this, try to have a 2025 version as well to ensure we can pull all the
accurate dataset. But our final deliverable should be 2026, so make sure we are
well prepared for 2026, since this has not started yet. Ensure we have the
correct pipeline so that when the league actually starts we can get all the
infomration. To ensure this, try it with 2025.

take as much time as you need and validate all the data, create own test cases
to make the agent flawless and perfect.
```

_Predictions are statistical estimates, not guarantees. Data is sourced from
free, openly-licensed feeds and may lag real-world events by a short interval._
