"""
club_crests.py  —  real club crest URLs (hot-linked, never redistributed)
=========================================================================
The user asked for real club logos. Club crests are trademarks, so this project
does **not** copy crest image files into the repository (that would redistribute
trademarked artwork and conflict with the "only legally accessible / licensed
images" rule). Instead we store, per club, a **hot-link URL** to a badge served
by a free, key-less, hot-link-friendly CDN (TheSportsDB). The frontend renders
``<img src=…>`` at view time and, whenever the image is unavailable (offline, CDN
hiccup, or an unmapped club), it falls back to the tasteful coloured monogram
badge — so the UI degrades gracefully and never breaks.

Only the small URL string is committed (``data/source/crests.json``); no image
bytes are stored. Building the map is a one-off / opt-in refresh step (``--crests``)
that hits TheSportsDB once per club and verifies every badge resolves back to the
right club (by name + country) before trusting it — a wrong crest is worse than a
clean monogram, so an unverified match is dropped.

Source
  * TheSportsDB free API (public test key ``3``) ``searchteams.php?t=<name>`` —
    returns the team's ``strBadge`` CDN URL. Free, no account, hot-link friendly.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from leagues import LEAGUES, ROOT_DIR, SOURCE_DIR, normalize_name, resolve_club

API = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
_UA = ("soccer-agent/1.0 (portfolio project; "
       "https://github.com/davidhyoo/epl-prediction-model-2)")
_TIMEOUT = 30
_COUNTRY = {"epl": "England", "laliga": "Spain"}

CACHE = os.path.join(SOURCE_DIR, "crests.json")
# Flat {code: url} map bundled into the frontend (club codes never collide
# between the EPL and La Liga registries, so a single lookup is unambiguous).
FRONTEND_MAP = os.path.join(ROOT_DIR, "src", "lib", "crests.json")

# Curated fallbacks for the very few clubs TheSportsDB's free search can't
# disambiguate (e.g. "Nottingham Forest" resolves to a *netball* team there).
# These point at football-data.org's free, key-less, hot-link-friendly crest CDN
# using that provider's stable, well-documented team ids — verified to return a
# real PNG for the correct club.
_OVERRIDE: dict[str, dict[str, str]] = {
    "epl": {
        "NFO": "https://crests.football-data.org/351.png",  # Nottingham Forest FC
    },
}


def _get(term: str) -> list[dict]:
    """Search TheSportsDB, retrying politely on 429 (free-key rate limit)."""
    url = API + urllib.parse.quote(term)
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.load(resp).get("teams") or []
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(6 * (attempt + 1))  # back off and retry
                continue
            raise
    return []


# generic tokens ignored when comparing club names to CDN team names
_GENERIC = {"fc", "cf", "afc", "ud", "ca", "rc", "rcd", "cd", "sad", "club",
            "de", "sd", "cp", "the", "and"}


def _tokens(name: str) -> set[str]:
    return {t for t in normalize_name(name).split() if t not in _GENERIC}


def _verify(league_id: str, club, team: dict) -> bool:
    """Only trust a badge whose team resolves back to this exact club and, when
    the CDN reports a country, sits in the league's country. Falls back to a
    significant-token subset match so spelling variants (``Brighton and Hove
    Albion`` vs ``Brighton & Hove Albion``) still line up — but never so loose
    that it would attach the wrong crest."""
    if (team.get("strSport") or "Soccer") != "Soccer":
        return False
    country = team.get("strCountry")
    if country and country != _COUNTRY.get(league_id, country):
        return False
    names = [team.get("strTeam"), team.get("strTeamAlternate")]
    name_toks = _tokens(club.name)
    short_toks = _tokens(club.short)
    for n in names:
        if not n:
            continue
        if resolve_club(league_id, n) == club.code:
            return True
        team_toks = _tokens(n)
        if name_toks and name_toks <= team_toks:
            return True
        if short_toks and short_toks <= team_toks:
            return True
    return False


def fetch_badge(league_id: str, club) -> str | None:
    """Search TheSportsDB for this club and return a verified crest URL, or None."""
    seen: set[str] = set()
    terms = [club.name, club.wiki, *club.aliases, club.short]
    for term in terms:
        key = normalize_name(term)
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            teams = _get(term)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        for team in teams:
            if _verify(league_id, club, team) and team.get("strBadge"):
                return team["strBadge"]
        time.sleep(1.2)  # stay under the free-key rate limit
    return None


def build(league_ids: list[str] | None = None, only_missing: bool = True) -> dict[str, dict[str, str]]:
    """Fetch crest URLs for every club and merge into the committed cache.

    Returns the full {league: {code: url}} map. Existing entries are kept when a
    fresh fetch fails, so a partial outage never wipes good URLs. With
    ``only_missing`` (default) clubs already in the cache are skipped, which keeps
    re-runs well under the free API's rate limit.
    """
    existing: dict[str, dict[str, str]] = {}
    if os.path.exists(CACHE):
        try:
            existing = json.load(open(CACHE, encoding="utf-8"))
        except (ValueError, OSError):
            existing = {}

    league_ids = league_ids or list(LEAGUES)
    for league_id in league_ids:
        lg = LEAGUES[league_id]
        bucket = dict(existing.get(league_id, {}))
        got = miss = skip = 0
        print(f"- {league_id}: {len(lg.clubs)} clubs")
        for club in lg.clubs:
            if only_missing and club.code in bucket:
                skip += 1
                continue
            url = fetch_badge(league_id, club)
            if not url:
                url = _OVERRIDE.get(league_id, {}).get(club.code)
            if url:
                bucket[club.code] = url
                got += 1
            else:
                miss += 1
                print(f"    . no verified crest for {club.code} ({club.name}) — monogram fallback")
        existing[league_id] = bucket
        print(f"  {league_id}: {got} new, {skip} cached, {miss} left to monogram "
              f"({len(bucket)}/{len(lg.clubs)} total)")

    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, CACHE)
    print(f"[crests] wrote {CACHE}")
    _write_frontend_map(existing)
    return existing


def _write_frontend_map(nested: dict[str, dict[str, str]]) -> None:
    """Flatten {league:{code:url}} -> {code:url} for the bundled frontend lookup."""
    flat: dict[str, str] = {}
    for bucket in nested.values():
        flat.update(bucket)
    os.makedirs(os.path.dirname(FRONTEND_MAP), exist_ok=True)
    tmp = FRONTEND_MAP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(flat, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, FRONTEND_MAP)
    print(f"[crests] wrote {FRONTEND_MAP} ({len(flat)} clubs)")


def load() -> dict[str, dict[str, str]]:
    """Return the committed {league: {code: url}} map (empty if none)."""
    if not os.path.exists(CACHE):
        return {}
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def crest_for(league_id: str, code: str) -> str | None:
    return load().get(league_id, {}).get(code)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Fetch verified club crest URLs")
    ap.add_argument("--league", choices=list(LEAGUES), default=None)
    args = ap.parse_args()
    build([args.league] if args.league else None)
