"""
ucl_stats.py  —  real Champions-League per-player goal stats
============================================================
openfootball's Champions-League feed carries match scores but **no goalscorer
annotations**, so — unlike the domestic leagues, where goals are aggregated from
inline scorers — the UCL players would otherwise have zero real output.

This module fills that gap from the one free, legal, reproducible source that
carries it: the **"Top goalscorers" wikitable** on the English-Wikipedia season
article (e.g. "2024–25 UEFA Champions League"). That table is sourced directly
from UEFA.com's official player statistics and gives, for the tournament's
leading scorers:

    Rank | Player | Team | Goals | Minutes played

We resolve each row's club to a UCL club code, cache the result to
``data/source/ucl/{season}/topscorers.json`` (so the rest of the pipeline stays
offline), and expose it as a ``{(clubCode, name-key): {...}}`` map shaped exactly
like ``club_players.aggregate_goals`` so the player builder can consume it with
no special-casing.

Coverage & honesty
------------------
The UEFA/Wikipedia table only lists the leading scorers (down to a ~6–7 goal
threshold), so goals are **real and exact for those players** and 0 for everyone
else — the app never invents a number. There is no free per-player *assists* or
appearances feed for the current UCL seasons (documented in the README), so those
stay ``null`` and render as "—". Minutes played are real for the listed scorers.

No API keys, no paid services — plain HTTPS to the public MediaWiki API with a
descriptive User-Agent and a polite delay; runs are idempotent and a partial
failure never discards a good cached file.

    python ml/ucl_stats.py                 # refresh every shipped UCL season
    python ml/ucl_stats.py --season 2024-25
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from leagues import LEAGUES, SOURCE_DIR, normalize_name, resolve_club
from nations import nation_info

UA = ("epl-laliga-dashboard/1.0 (portfolio project; "
      "https://github.com/davidhyoo/epl-prediction-model-2)")
TIMEOUT = 45
POLITE = 0.3

# English-Wikipedia article title per shipped season. The season label uses an
# en-dash (U+2013), not a hyphen — the article does not exist under a hyphen.
_ARTICLE = {
    "2024-25": "2024\u201325 UEFA Champions League",
    "2025-26": "2025\u201326 UEFA Champions League",
}
_SECTION_ANCHOR = "Top_goalscorers"


# --------------------------------------------------------------------------- #
# HTTP (stdlib only)
# --------------------------------------------------------------------------- #
def _get(url: str, tries: int = 4) -> bytes:
    delay = POLITE
    for attempt in range(tries):
        time.sleep(delay)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < tries - 1:
                ra = exc.headers.get("Retry-After", "")
                delay = float(ra) if ra.isdigit() else min(10.0, delay * 3 + 0.5)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt < tries - 1:
                delay = min(10.0, delay * 3 + 0.5)
                continue
            raise
    raise RuntimeError("unreachable")


def _api(params: dict) -> dict:
    params = {**params, "format": "json", "maxlag": "5", "redirects": "1"}
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    return json.loads(_get(url).decode("utf-8", "replace"))


def _section_index(title: str) -> int | None:
    """Resolve the 'Top goalscorers' section index by its stable anchor rather
    than a hard-coded number (article sections shift as the page is edited)."""
    data = _api({"action": "parse", "page": title, "prop": "sections"})
    for sec in data.get("parse", {}).get("sections", []):
        if sec.get("anchor") == _SECTION_ANCHOR:
            return int(sec["index"])
        if sec.get("line", "").strip().lower() == "top goalscorers":
            return int(sec["index"])
    return None


# --------------------------------------------------------------------------- #
# Wikitable parsing
# --------------------------------------------------------------------------- #
def _link_display(cell: str) -> str | None:
    """Display text of the first ``[[…]]`` wikilink (piped label if present)."""
    m = re.search(r"\[\[([^\]]+)\]\]", cell)
    if not m:
        return None
    return m.group(1).split("|")[-1].strip()


def _link_target(cell: str) -> str | None:
    m = re.search(r"\[\[([^\]]+)\]\]", cell)
    if not m:
        return None
    return m.group(1).split("|")[0].strip()


def _cell_content(raw: str) -> str:
    """Strip a leading ``attr|content`` segment (attributes contain ``=``), being
    careful not to split inside ``[[…]]`` / ``{{…}}``."""
    depth = 0
    for i, ch in enumerate(raw):
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth = max(0, depth - 1)
        elif ch == "|" and depth == 0:
            return raw[i + 1:].strip() if "=" in raw[:i] else raw.strip()
    return raw.strip()


def _trailing_int(raw: str) -> int | None:
    m = re.search(r"(\d[\d,]*)\s*$", _cell_content(raw).replace(",", ""))
    return int(m.group(1)) if m else None


def _flag_code(cell: str) -> str | None:
    """3-letter nation code from a ``{{flagicon|XXX}}`` / ``{{fb|XXX}}`` template."""
    m = re.search(r"\{\{\s*(?:flagicon|fb|fbu?|fbw)\s*\|\s*([A-Za-z]{3})", cell)
    return m.group(1).upper() if m else None


def parse_topscorers(wikitext: str) -> list[dict]:
    """Parse the goalscorers wikitable → ordered list of scorer rows.

    Columns are *Rank | Player | Team | Goals | Minutes*. Rank and Goals use
    ``rowspan`` when several players share a tally, so continuation rows omit
    them — we carry the last Goals value forward. Player vs Team cells are told
    apart by their template: ``{{flagicon}}`` marks the player's nationality,
    ``{{fbaicon}}`` the club's country. A "Seven players" style summary row
    (no wikilink) carries no individual data and is skipped.
    """
    start = wikitext.find("{|")
    end = wikitext.find("|}", start)
    if start < 0 or end < 0:
        return []
    body = wikitext[start:end]

    rows: list[dict] = []
    cur_goals: int | None = None
    for chunk in re.split(r"\n\|-", body):
        cells: list[str] = []
        for line in chunk.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|+"):
                continue
            for part in re.split(r"\|\|", line[1:]):
                if part.strip():
                    cells.append(part.strip())
        if not cells:
            continue
        pl_i = next((i for i, c in enumerate(cells) if "flagicon" in c), None)
        tm_i = next((i for i, c in enumerate(cells) if "fbaicon" in c), None)
        if pl_i is None or tm_i is None:
            continue
        player = _link_display(cells[pl_i])
        team_disp = _link_display(cells[tm_i])
        team_tgt = _link_target(cells[tm_i])
        nation = _flag_code(cells[pl_i])
        if not player or not (team_disp or team_tgt):
            continue
        post = [n for n in (_trailing_int(c) for c in cells[tm_i + 1:])
                if n is not None]
        minutes: int | None
        if len(post) >= 2:
            cur_goals, minutes = post[0], post[1]
        elif len(post) == 1:
            minutes = post[0]
        else:
            minutes = None
        if cur_goals is None:
            continue
        rows.append({"player": player, "team": team_disp or team_tgt,
                     "teamTarget": team_tgt, "nation": nation,
                     "goals": cur_goals, "minutes": minutes})
    return rows


# --------------------------------------------------------------------------- #
# Fetch / cache / load
# --------------------------------------------------------------------------- #
def _cache_path(season_id: str) -> str:
    return os.path.join(SOURCE_DIR, "ucl", season_id, "topscorers.json")


def fetch_topscorers(season_id: str) -> list[dict]:
    title = _ARTICLE.get(season_id)
    if not title:
        return []
    idx = _section_index(title)
    if idx is None:
        return []
    data = _api({"action": "parse", "page": title, "prop": "wikitext",
                 "section": str(idx)})
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    return parse_topscorers(wikitext)


def refresh_season(season_id: str) -> list[dict]:
    """Fetch + resolve + cache one season's top scorers. Returns resolved rows."""
    raw = fetch_topscorers(season_id)
    resolved: list[dict] = []
    for r in raw:
        code = resolve_club("ucl", r["team"]) or resolve_club("ucl", r.get("teamTarget") or "")
        if not code:
            continue
        iso2, nat_name = (None, None)
        if r.get("nation"):
            iso2, nat_name = nation_info(r["nation"])
        resolved.append({"player": r["player"], "club": code,
                         "goals": r["goals"], "minutes": r["minutes"],
                         "nationIso2": iso2, "nationName": nat_name})
    if resolved:
        path = _cache_path(season_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"season": season_id, "source": "wikipedia/uefa",
                       "scorers": resolved}, fh, ensure_ascii=False, indent=1)
    return resolved


def load_goal_stats(season_id: str) -> dict[tuple[str, str], dict]:
    """Cached top scorers as ``{(clubCode, name-key): {...}}`` — the same shape
    ``club_players.aggregate_goals`` returns, so the player builder consumes it
    with no special-casing. ``minutesPlayed`` carries the real UEFA minutes.
    Returns ``{}`` when no cache exists (players then simply have goals 0)."""
    path = _cache_path(season_id)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out: dict[tuple[str, str], dict] = {}
    for s in data.get("scorers", []):
        key = normalize_name(s["player"])
        if not key or not s.get("club"):
            continue
        out[(s["club"], key)] = {
            "goals": int(s.get("goals") or 0),
            "penalties": 0,          # UEFA table doesn't split penalties
            "minutes": [],           # no per-goal minute labels for the UCL
            "minutesPlayed": s.get("minutes"),
            "nationIso2": s.get("nationIso2"),
            "nationName": s.get("nationName"),
            "display": s["player"],
        }
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh Champions-League top-scorer stats")
    ap.add_argument("--season", help="only this season id (e.g. 2024-25)")
    args = ap.parse_args()
    seasons = [args.season] if args.season else list(LEAGUES["ucl"].seasons)
    for sid in seasons:
        rows = refresh_season(sid)
        top = ", ".join(f"{r['player']} {r['goals']}" for r in rows[:5])
        print(f"[ucl {sid}] {len(rows)} scorers cached  ({top} …)")


if __name__ == "__main__":
    main()
