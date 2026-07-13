"""
fetch_stats.py  —  real 2026 FIFA World Cup per-player tournament statistics
=============================================================================
Derives **real** per-player World Cup 2026 stats (appearances, minutes, goals,
yellow/red cards and — for goalkeepers — clean sheets / goals conceded) from the
public English-Wikipedia match articles, which mirror the official FIFA match
reports (goalscorers, starting XIs and substitutions).

Why this source
---------------
There is no free, machine-readable feed of *official* World Cup per-player stats.
Wikipedia's per-group / knockout match articles, however, transcribe the FIFA
match reports into structured templates:

  * ``{{#invoke:football box|main ...}}`` — teams, score and the goalscorer list
    (``|goals1=`` / ``|goals2=`` with ``*[[Player]] 9'`` lines).
  * two lineup wikitables per match — the starting XI and the substitutes, with
    ``{{yel|min}}`` (yellow), ``{{sent off|n|min}}`` (red), ``{{suboff|min}}`` and
    ``{{subon|min}}`` markers.

From those we can compute genuine tournament stats. Each scorer / lineup entry is
a ``[[wiki article title]]`` — the very same title stored on every squad player by
``ml/fetch_players.py`` — so the join back onto the squad is exact (no fuzzy
matching).

What is NOT available (and is therefore never faked)
----------------------------------------------------
Goal *assists*, expected goals (xG/xA), shots, passing, tackles, etc. are **not**
published in any free World Cup source, so downstream those fields are left null
and clearly labelled "not tracked in open data" in the UI.

Licensing / etiquette
---------------------
Plain HTTPS to the public MediaWiki API (no key), descriptive User-Agent, a polite
delay + exponential backoff. Sporting facts (who scored, who played) are not
copyrightable; Wikipedia's text is CC BY-SA 4.0 and is credited in the README /
Methodology page. The result is cached to
``data/source/player_stats_wikipedia.json`` so the rest of the pipeline stays
offline and reproducible; a failed refresh never discards a good cache.

    python ml/fetch_stats.py            # refresh from Wikipedia (all articles)
    python ml/fetch_stats.py --offline  # validate the existing cache, no network
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA_DIR  # noqa: E402

SOURCE_DIR = os.path.join(DATA_DIR, "source")
STATS_CACHE = os.path.join(SOURCE_DIR, "player_stats_wikipedia.json")

UA = ("worldcup-2026-dashboard/1.0 (portfolio project; "
      "https://github.com/davidhyoo/epl-prediction-model-2)")
TIMEOUT = 45
POLITE = 0.2

# The 12 group articles + the single knockout-stage article carry every match box
# with its goalscorers and lineups.
ARTICLES = [f"2026 FIFA World Cup Group {g}" for g in "ABCDEFGHIJKL"]
# The round-of-32 match boxes live on their own article (the knockout-stage page
# only transcludes them); R16/QF/SF/Final boxes are inlined on the knockout page.
ARTICLES.append("2026 FIFA World Cup round of 32")
ARTICLES.append("2026 FIFA World Cup knockout stage")


# --------------------------------------------------------------------------- #
# HTTP (polite, retrying) — mirrors ml/fetch_players.py
# --------------------------------------------------------------------------- #
def _get(url: str, tries: int = 4) -> bytes:
    delay = POLITE
    last: Exception | None = None
    for attempt in range(tries):
        time.sleep(delay)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (429, 503) and attempt < tries - 1:
                ra = exc.headers.get("Retry-After", "")
                delay = float(ra) if ra.isdigit() else min(10.0, delay * 3 + 0.5)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < tries - 1:
                delay = min(10.0, delay * 3 + 0.5)
                continue
            raise
    raise last or RuntimeError("request failed")


def _wikitext(title: str) -> str:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "prop": "wikitext", "page": title,
         "redirects": 1, "format": "json", "maxlag": "5"})
    data = json.loads(_get(url).decode("utf-8", "replace"))
    if "error" in data:
        raise RuntimeError(f"wiki error for {title!r}: {data['error'].get('info')}")
    return data["parse"]["wikitext"]["*"]


# --------------------------------------------------------------------------- #
# Wikitext helpers
# --------------------------------------------------------------------------- #
def _norm_title(t: str) -> str:
    """Normalise a wiki article title so both sides of the squad join match.

    Wikipedia titles are case-sensitive except for the first character and treat
    spaces and underscores as equivalent.
    """
    t = t.replace("_", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


def _match_braces(text: str, i: int) -> int:
    """Given ``text[i:i+2] == '{{'`` return the index just past the matching ``}}``."""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _split_params(body: str) -> dict:
    """Split a template body into ``key -> value`` respecting [[..]] / {{..}} / <ref>."""
    params: dict[str, str] = {}
    depth = 0
    buf = ""
    for ch in body:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth = max(0, depth - 1)
        if ch == "|" and depth == 0:
            if "=" in buf:
                k, v = buf.split("=", 1)
                params[k.strip().lower()] = v.strip()
            buf = ""
        else:
            buf += ch
    if "=" in buf:
        k, v = buf.split("=", 1)
        params[k.strip().lower()] = v.strip()
    return params


def _first_wikilink(text: str) -> str | None:
    """Return the normalised title of the first ``[[title|...]]`` in ``text``."""
    m = re.search(r"\[\[\s*([^\]|#]+?)\s*(?:[#|][^\]]*)?\]\]", text)
    return _norm_title(m.group(1)) if m else None


def _flag_code(field: str) -> str | None:
    """Extract the 3-letter FIFA/IOC code from a ``{{#invoke:flag|fb...|MEX}}`` field."""
    m = re.search(r"\|\s*([A-Za-z]{3})\s*(?:\||}})", field)
    return m.group(1).upper() if m else None


def _minute_value(tok: str) -> int:
    """'90+2' -> 92, '45' -> 45 (used only to order/cap; capped by caller)."""
    m = re.match(r"(\d{1,3})(?:\+(\d{1,3}))?", tok)
    if not m:
        return 0
    return int(m.group(1)) + (int(m.group(2)) if m.group(2) else 0)


_OG_RE = re.compile(r"\(\s*o\.?\s*g\.?\s*\)|\{\{\s*og\b|own[\s-]?goal", re.I)
_GOAL_TMPL_RE = re.compile(r"\{\{\s*goal\s*\|([^}]*)\}\}", re.I)
_MIN_RE = re.compile(r"(?<!\d)(\d{1,3}(?:\+\d{1,3})?)\s*[\u2032']")


def _count_goals(line: str) -> int:
    """Number of goal events on one ``*[[Player]] ...`` scorer line."""
    n = 0
    stripped = line
    for m in _GOAL_TMPL_RE.finditer(line):
        args = [a for a in m.group(1).split("|") if re.search(r"\d", a)]
        n += len(args)
        stripped = stripped.replace(m.group(0), " ")
    n += len(_MIN_RE.findall(stripped))
    return max(n, 0)


def _parse_goals(field: str) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Parse a ``|goals1=`` / ``|goals2=`` field.

    Returns ``(scored, own_goals)`` where each is a list of ``(wiki_title, count)``.
    Own goals are reported separately and never credited as a normal goal.
    """
    scored: list[tuple[str, int]] = []
    owns: list[tuple[str, int]] = []
    for raw in field.splitlines():
        line = raw.strip()
        if not line.startswith("*"):
            continue
        title = _first_wikilink(line)
        if not title:
            continue
        count = _count_goals(line) or 1
        if _OG_RE.search(line):
            owns.append((title, count))
        else:
            scored.append((title, count))
    return scored, owns


# --------------------------------------------------------------------------- #
# Lineup parsing
# --------------------------------------------------------------------------- #
# A player row looks like:  |GK ||'''1''' ||[[Raúl Rangel (footballer)|Raúl Rangel]] || {{yel|23}} || {{suboff|76}}
_ROW_RE = re.compile(r"^\|\s*([A-Za-z]{1,3})\s*\|\|\s*'''\s*\d+\s*'''\s*\|\|\s*\[\[")
_YEL_RE = re.compile(r"\{\{\s*yel\s*\|\s*(\d{1,3}(?:\+\d{1,3})?)", re.I)
_SENTOFF_RE = re.compile(r"\{\{\s*sent\s*off\s*\|\s*\d+\s*\|\s*(\d{1,3}(?:\+\d{1,3})?)", re.I)
_SUBOFF_RE = re.compile(r"\{\{\s*suboff\s*\|\s*(\d{1,3}(?:\+\d{1,3})?)", re.I)
_SUBON_RE = re.compile(r"\{\{\s*subon\s*\|\s*(\d{1,3}(?:\+\d{1,3})?)", re.I)


def _parse_row(line: str) -> dict | None:
    """Parse one lineup player row into structured card/substitution data."""
    if not _ROW_RE.match(line):
        return None
    title = _first_wikilink(line)
    if not title:
        return None
    yellows = _YEL_RE.findall(line)
    sentoff = _SENTOFF_RE.search(line)
    suboff = _SUBOFF_RE.search(line)
    subon = _SUBON_RE.search(line)
    return {
        "wiki": title,
        "pos": _ROW_RE.match(line).group(1).upper(),
        "yellows": len(yellows),
        "sentoff": _minute_value(sentoff.group(1)) if sentoff else None,
        "suboff": _minute_value(suboff.group(1)) if suboff else None,
        "subon": _minute_value(subon.group(1)) if subon else None,
    }


def _rows_between(chunk: str, start: int, end: int) -> list[dict]:
    out = []
    for line in chunk[start:end].splitlines():
        row = _parse_row(line.strip())
        if row:
            out.append(row)
    return out


def _lineup_with_flags(chunk: str):
    """team1/team2 lineups, each row tagged started=True/False."""
    subs = [m.start() for m in re.finditer(r"'''Substitutions:'''", chunk)]
    mgrs = [m.start() for m in re.finditer(r"'''Manager", chunk)]
    if len(subs) < 2 or len(mgrs) < 2:
        return None

    def team(starter_lo, starter_hi, sub_lo, sub_hi):
        players = []
        for r in _rows_between(chunk, starter_lo, starter_hi):
            r["started"] = True
            players.append(r)
        for r in _rows_between(chunk, sub_lo, sub_hi):
            r["started"] = False
            players.append(r)
        return players

    t1 = team(0, subs[0], subs[0], mgrs[0])
    t2 = team(mgrs[0], subs[1], subs[1], mgrs[1])
    return t1, t2


# --------------------------------------------------------------------------- #
# Match box parsing
# --------------------------------------------------------------------------- #
_SCORE_RE = re.compile(r"(\d{1,2})\s*[\u2013\u2212\-]\s*(\d{1,2})")


def _parse_score(box: dict) -> tuple[int, int, bool] | None:
    field = box.get("score", "")
    aet = bool(re.search(r"a\.?e\.?t|extra[\s-]?time|\{\{\s*aet", field + box.get("aet", ""), re.I))
    m = _SCORE_RE.search(field)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), aet


def _parse_date(box: dict) -> str | None:
    m = re.search(r"\{\{\s*[Ss]tart date\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})",
                  box.get("date", ""))
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


# --------------------------------------------------------------------------- #
# Per-player aggregation
# --------------------------------------------------------------------------- #
def _blank() -> dict:
    return {"appearances": 0, "minutes": 0, "goals": 0, "ownGoals": 0,
            "yellowCards": 0, "redCards": 0, "gkCleanSheets": 0,
            "gkGoalsConceded": 0, "gkStarts": 0, "log": []}


def _apply_lineup(agg: dict, players: list[dict], match_len: int,
                  team_conceded: int, date: str | None, opp: str | None,
                  gf: int, ga: int) -> None:
    """Fold one team's lineup into the aggregate; first started GK owns the goal."""
    gk_owner = None
    for r in players:
        started = r.get("started")
        subon = r.get("subon")
        appeared = started or subon is not None
        if not appeared:
            continue
        on = 0 if started else int(subon)
        off = match_len
        if r.get("suboff") is not None:
            off = min(off, int(r["suboff"]))
        if r.get("sentoff") is not None:
            off = min(off, int(r["sentoff"]))
        minutes = max(0, min(off, match_len) - min(on, match_len))

        a = agg.setdefault(r["wiki"], _blank())
        a["appearances"] += 1
        a["minutes"] += minutes
        a["yellowCards"] += r.get("yellows", 0)
        if r.get("sentoff") is not None:
            a["redCards"] += 1
        if started and r["pos"] == "GK" and gk_owner is None:
            gk_owner = a
            a["gkStarts"] += 1
            a["gkGoalsConceded"] += team_conceded
            if team_conceded == 0:
                a["gkCleanSheets"] += 1
        a["log"].append({
            "date": date, "opp": opp, "gf": gf, "ga": ga,
            "min": minutes, "g": 0, "y": r.get("yellows", 0),
            "r": 1 if r.get("sentoff") is not None else 0,
            "started": bool(started),
        })


def _credit_goals(agg: dict, scored: list[tuple[str, int]],
                  owns: list[tuple[str, int]]) -> None:
    for title, count in scored:
        a = agg.setdefault(title, _blank())
        a["goals"] += count
        # add to the most recent log entry for this player if present this match
    for title, count in owns:
        a = agg.setdefault(title, _blank())
        a["ownGoals"] += count


def _tag_match_goals(agg: dict, scored: list[tuple[str, int]]) -> None:
    """Reflect goals in the player's latest match-log row (best effort)."""
    for title, count in scored:
        a = agg.get(title)
        if a and a["log"]:
            a["log"][-1]["g"] += count


# --------------------------------------------------------------------------- #
# Article driver
# --------------------------------------------------------------------------- #
def parse_article(wt: str, agg: dict) -> int:
    """Parse every completed match box + lineups in one article. Returns match count."""
    starts = [m.start() for m in re.finditer(r"\{\{\s*#invoke:\s*football box", wt, re.I)]
    matches = 0
    for k, s in enumerate(starts):
        end = _match_braces(wt, s)
        box = _split_params(wt[s + 2:end - 2])
        parsed = _parse_score(box)
        if not parsed:
            continue  # future / unplayed match
        gf, ga, aet = parsed
        match_len = 120 if aet else 90
        chunk = wt[end: starts[k + 1] if k + 1 < len(starts) else len(wt)]

        code1 = _flag_code(box.get("team1", ""))
        code2 = _flag_code(box.get("team2", ""))
        date = _parse_date(box)
        scored1, owns1 = _parse_goals(box.get("goals1", ""))
        scored2, owns2 = _parse_goals(box.get("goals2", ""))

        lus = _lineup_with_flags(chunk)
        if lus:
            t1, t2 = lus
            _apply_lineup(agg, t1, match_len, team_conceded=ga, date=date,
                          opp=code2, gf=gf, ga=ga)
            _apply_lineup(agg, t2, match_len, team_conceded=gf, date=date,
                          opp=code1, gf=ga, ga=gf)
        _credit_goals(agg, scored1, owns1)
        _credit_goals(agg, scored2, owns2)
        if lus:
            _tag_match_goals(agg, scored1 + scored2)
        matches += 1
    return matches


def fetch(offline: bool = False) -> dict:
    agg: dict[str, dict] = {}
    total = 0
    articles_done = []
    for title in ARTICLES:
        try:
            wt = _wikitext(title)
        except Exception as exc:  # noqa: BLE001
            print(f"[stats] WARN could not fetch {title!r}: {exc}")
            continue
        n = parse_article(wt, agg)
        total += n
        articles_done.append({"title": title, "matches": n})
        print(f"[stats] {title:42s} matches={n:2d}")

    # Trim the log for compactness and drop internal helpers where not needed.
    players = {}
    for wiki, a in agg.items():
        a["log"] = a["log"][-12:]
        players[wiki] = a

    return {
        "source": "English Wikipedia — 2026 FIFA World Cup match articles "
                   "(FIFA match reports); text CC BY-SA 4.0, sporting facts uncopyrightable",
        "note": "Assists, xG/xA and advanced metrics are NOT published in open "
                "World Cup data and are intentionally omitted (never fabricated).",
        "asOf": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matchesParsed": total,
        "articles": articles_done,
        "players": players,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="validate the existing cache without any network calls")
    args = ap.parse_args(argv)

    os.makedirs(SOURCE_DIR, exist_ok=True)

    if args.offline:
        if not os.path.exists(STATS_CACHE):
            print("[stats] offline: no cache to validate")
            return
        with open(STATS_CACHE, encoding="utf-8") as f:
            data = json.load(f)
        print(f"[stats] offline OK — {len(data.get('players', {}))} players, "
              f"{data.get('matchesParsed')} matches (asOf {data.get('asOf')})")
        return

    data = fetch()
    if data["matchesParsed"] == 0:
        print("[stats] refresh produced 0 matches — keeping existing cache")
        return
    tmp = STATS_CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATS_CACHE)
    scorers = sum(1 for a in data["players"].values() if a["goals"] > 0)
    print(f"[stats] wrote {STATS_CACHE} — {len(data['players'])} players "
          f"({scorers} scorers), {data['matchesParsed']} matches")


if __name__ == "__main__":
    main()
