"""
club_fpl.py  —  real per-player assists / minutes / cards for the Premier League
================================================================================
openfootball (our fixtures + goalscorers source) publishes **goals only** — there
is no assist, minute or card feed in it, nor in football-data.co.uk. The Premier
League does, however, expose an official, public, **key-less** JSON feed (the
Fantasy Premier League API), and the community project
``vaastav/Fantasy-Premier-League`` snapshots that feed per season as CSV in an
openly-available GitHub repository. Both are free and require no account.

We use them purely to *enrich* our already-real squad players with:

  * **assists**       (real, per player)
  * **minutes** played
  * **yellow / red cards**
  * (best-effort) expected assists / goals for the profile trend

Goals stay sourced from the openfootball match scorers (our single source of
truth for the top-scorer race and goal minutes), so the two never disagree.

Scope + honesty
  * Premier League only. La Liga has no equivalent free, key-less per-player feed,
    so La Liga assists stay ``null`` and the UI renders a tasteful "—". The app
    never invents a number it cannot source.
  * A snapshot for a not-yet-started season simply doesn't exist upstream, so the
    fetch is a no-op and the (empty) pre-season stats remain ``null``.
  * Every network call is wrapped so a failure keeps the committed cache and the
    pipeline still rebuilds end to end.

Data flow (mirrors the openfootball / football-data caches):
  ``club_refresh`` → :func:`download` writes a trimmed CSV cache under
  ``data/source/epl/<season>/fpl_players.csv`` → the pipeline calls
  :func:`enrich_players` which reads that cache and merges the stats onto the
  real squad by an accent-folded name match within each club.
"""
from __future__ import annotations

import csv
import io
import os
import urllib.error
import urllib.request

from leagues import SOURCE_DIR, normalize_name, resolve_club

VAASTAV = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
_UA = ("soccer-agent/1.0 (portfolio project; "
       "https://github.com/davidhyoo/epl-prediction-model-2)")
_TIMEOUT = 45

# Columns we persist in the trimmed cache (keeps the committed file ~60 KB).
_CACHE_COLS = ["team", "first_name", "second_name", "web_name", "minutes",
               "goals_scored", "assists", "yellow_cards", "red_cards",
               "expected_assists", "expected_goals", "starts"]

# Only the Premier League has a free, key-less per-player feed.
SUPPORTED = {"epl"}


def cache_path(league_id: str, season_id: str) -> str:
    d = os.path.join(SOURCE_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "fpl_players.csv")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read()


def download(league_id: str, season_id: str) -> tuple[bool, str]:
    """Fetch the FPL per-player snapshot for one EPL season and write a trimmed
    CSV cache atomically. Returns (updated, status) like ``club_refresh``.

    Never raises: a missing snapshot (unstarted season) or a network error keeps
    any committed cache and reports a status the caller can log.
    """
    if league_id not in SUPPORTED:
        return False, "unsupported"

    dest = cache_path(league_id, season_id)
    base = f"{VAASTAV}/{season_id}"
    try:
        teams_raw = _get(f"{base}/teams.csv").decode("utf-8", "replace")
        players_raw = _get(f"{base}/players_raw.csv").decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        code = getattr(exc, "code", "")
        print(f"    . fpl_players.csv: {exc.__class__.__name__} {code} — "
              f"{'kept cache' if os.path.exists(dest) else 'absent'}")
        return False, "kept" if os.path.exists(dest) else "absent"

    teams = {r["id"]: r["name"] for r in csv.DictReader(io.StringIO(teams_raw))}
    rows = list(csv.DictReader(io.StringIO(players_raw)))
    if not rows:
        return False, "absent"

    tmp = dest + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(_CACHE_COLS)
        for r in rows:
            w.writerow([
                teams.get(r.get("team", ""), ""),
                r.get("first_name", ""), r.get("second_name", ""),
                r.get("web_name", ""), r.get("minutes", "0"),
                r.get("goals_scored", "0"), r.get("assists", "0"),
                r.get("yellow_cards", "0"), r.get("red_cards", "0"),
                r.get("expected_assists", ""), r.get("expected_goals", ""),
                r.get("starts", ""),
            ])
    os.replace(tmp, dest)
    print(f"    ok {len(rows):>5} rows  fpl_players.csv ({league_id} {season_id})")
    return True, "updated"


def _load_cache(league_id: str, season_id: str) -> list[dict] | None:
    path = cache_path(league_id, season_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value: str):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


class _FplRecord:
    __slots__ = ("full", "surname", "initial", "tokens", "minutes", "assists",
                 "yellow", "red", "xa", "xg", "starts")

    def __init__(self, row: dict):
        first = normalize_name(row.get("first_name", ""))
        second = normalize_name(row.get("second_name", ""))
        web = normalize_name(row.get("web_name", ""))
        self.full = " ".join(f"{first} {second}".split())
        # Prefer the surname from second_name; fall back to the web name.
        surname_src = second or web
        parts = surname_src.split()
        self.surname = parts[-1] if parts else ""
        self.initial = first[0] if first else (web[0] if web else "")
        self.tokens = set(self.full.split()) | set(web.split())
        self.minutes = _int(row.get("minutes"))
        self.assists = _int(row.get("assists"))
        self.yellow = _int(row.get("yellow_cards"))
        self.red = _int(row.get("red_cards"))
        self.xa = _float(row.get("expected_assists"))
        self.xg = _float(row.get("expected_goals"))
        self.starts = _int(row.get("starts"))


def _match(player: dict, candidates: list[_FplRecord]) -> _FplRecord | None:
    """Best FPL record for one of our squad players, within the same club.

    A surname match is always required to accept, so we never mis-attribute a
    stat line to the wrong player. Disambiguated by first initial, then by the
    largest full-name token overlap.
    """
    our = normalize_name(player.get("name", ""))
    if not our:
        return None
    tokens = set(our.split())
    surname = our.split()[-1]

    exact = [c for c in candidates if c.full == our]
    if len(exact) == 1:
        return exact[0]

    by_surname = [c for c in candidates if c.surname and c.surname == surname]
    if len(by_surname) == 1:
        return by_surname[0]
    if len(by_surname) > 1:
        initial = our[0]
        by_initial = [c for c in by_surname if c.initial == initial]
        if len(by_initial) == 1:
            return by_initial[0]
        pool = by_initial or by_surname
        return max(pool, key=lambda c: len(tokens & c.tokens))

    # Fall back to a token overlap, but only when the surname is among the
    # overlapping tokens (guards against loose first-name-only collisions).
    best, best_score = None, 0
    for c in candidates:
        overlap = tokens & c.tokens
        if surname in overlap and len(overlap) > best_score:
            best, best_score = c, len(overlap)
    return best


def enrich_players(league_id: str, season_id: str, players: list[dict],
                   played: int = 1) -> dict:
    """Merge real assists / minutes / cards onto ``players`` in place.

    Returns a small coverage summary for logging. A missing cache, an
    unsupported league, or a season with **no completed matches yet** is a
    silent no-op (assists stay ``null`` → UI shows "—"). The ``played`` gate
    matters because upstream seeds a not-yet-started season's snapshot with the
    *previous* season's carryover totals — we must not attach those to a season
    that hasn't kicked off (which would read as 24 assists but 0 goals).
    """
    summary = {"matched": 0, "assists": 0, "total": len(players)}
    if league_id not in SUPPORTED or played <= 0:
        return summary

    rows = _load_cache(league_id, season_id)
    if not rows:
        return summary

    # Index FPL records by our canonical club code.
    by_club: dict[str, list[_FplRecord]] = {}
    for row in rows:
        code = resolve_club(league_id, row.get("team", ""))
        if code:
            by_club.setdefault(code, []).append(_FplRecord(row))

    for p in players:
        candidates = by_club.get(p.get("club", ""))
        if not candidates:
            continue
        rec = _match(p, candidates)
        # Only trust a record for a player who actually featured (minutes > 0),
        # so "played but no assist" reads as a real 0 and "did not feature"
        # stays null.
        if rec is None or rec.minutes <= 0:
            continue
        p["assists"] = rec.assists
        p["minutes"] = rec.minutes
        p["yellowCards"] = rec.yellow
        p["redCards"] = rec.red
        summary["matched"] += 1
        if rec.assists:
            summary["assists"] += 1

    return summary
