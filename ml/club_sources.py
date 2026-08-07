"""
club_sources.py  —  parsers for the cached club-football source files
=====================================================================
Pure parsing only (no network) so the pipeline stays offline & reproducible.
Two source formats are merged into one normalised match record per fixture:

  1. **openfootball** ``.txt`` (CC0) — the schedule, results, and (2025-26+)
     inline goalscorers with minutes. Two on-disk layouts exist and both are
     handled here:
        * newer:  ``HH:MM  Home  2-1 (1-0)  Away``  + a ``(scorers…)`` block
        * older:  ``HH:MM  Home  v Away  2-1 (1-0)`` (no scorers)
        * fixture: ``HH:MM  Home  v Away`` (no score yet — upcoming match)
  2. **football-data.co.uk** CSV (free) — per-match shots, shots-on-target,
     corners, fouls, cards and closing market odds, merged by (home, away).

The goalscorer grammar (openfootball):
    (Home scorer 12', Other 45+1'(p); Away scorer 70', 88'(og))
  * home scorers precede the ``;``, away scorers follow it
  * ``(p)`` = penalty (still a goal for the taker), ``(og)`` = own goal
    (credited to the *listed* team's tally, but NOT to the named player)
  * ``90+4'`` = stoppage time; a player may list several minutes: ``64', 76'``
"""
from __future__ import annotations

import csv
import io
import os
import re
from datetime import date, datetime, timezone

from leagues import LEAGUES, SOURCE_DIR, resolve_club, resolve_club_loose

# --------------------------------------------------------------------------- #
# openfootball parsing
# --------------------------------------------------------------------------- #
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

_DATE_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w{3})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
_ROUND_RE = re.compile(r"[▪»].*?(\d+)\s*$")
_SCORE = r"(\d+)-(\d+)(?:\s*\((\d+)-(\d+)\))?"
# newer: Home  2-1 (1-0)  Away
_NEW_RE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+" + _SCORE + r"\s+(.+?)\s*$")
# older with score: Home v Away  2-1 (1-0)
_OLD_RE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+" + _SCORE + r"\s*$")
# fixture only: Home v Away
_FIX_RE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s*$")

# one scoring event: optional name, then a minute (with optional +stoppage and (p)/(og))
_EVENT_RE = re.compile(
    r"([A-Za-zÀ-ÿ0-9'.\-\u00A0 ]*?)\s*(\d{1,3})(?:\+(\d{1,2}))?'\s*(\(p\)|\(og\))?")


def _clean_team(s: str) -> str:
    return " ".join(s.replace("\u00a0", " ").split())


def _parse_side(text: str, team_code: str, opp_code: str) -> list[dict]:
    """Parse one side of a scorer block into goal events for that team's tally."""
    events: list[dict] = []
    current = ""
    for m in _EVENT_RE.finditer(text):
        name = _clean_team(m.group(1))
        base = int(m.group(2))
        extra = int(m.group(3)) if m.group(3) else 0
        ann = m.group(4) or ""
        if name:
            current = name
        who = current
        if not who:
            continue
        is_og = ann == "(og)"
        events.append({
            "player": who,
            "minute": base,
            "stoppage": extra,
            "minuteLabel": f"{base}+{extra}'" if extra else f"{base}'",
            "penalty": ann == "(p)",
            "ownGoal": is_og,
            # own goals count for `team_code` (the listed side) but the player
            # is on the OTHER team, so the goal is credited to `opp_code`.
            "scorerTeam": opp_code if is_og else team_code,
            "forTeam": team_code,
        })
    return events


def _parse_scorers(block: str, home_code: str, away_code: str,
                   home_goals: int, away_goals: int) -> list[dict]:
    inner = block.strip()
    if inner.startswith("("):
        inner = inner[1:]
    if inner.endswith(")"):
        inner = inner[:-1]
    if ";" in inner:
        home_txt, away_txt = inner.split(";", 1)
        home_ev = _parse_side(home_txt, home_code, away_code)
        away_ev = _parse_side(away_txt, away_code, home_code)
    else:
        # single side scored (no ';'): assign to whichever team has goals
        if home_goals > 0 and away_goals == 0:
            home_ev, away_ev = _parse_side(inner, home_code, away_code), []
        elif away_goals > 0 and home_goals == 0:
            home_ev, away_ev = [], _parse_side(inner, away_code, home_code)
        else:
            home_ev, away_ev = _parse_side(inner, home_code, away_code), []
    return home_ev + away_ev


def _roll_date(mon: int, day: int, year: int, last: date | None) -> tuple[date, int]:
    """Build a date, bumping the year if the season has rolled past New Year."""
    d = date(year, mon, day)
    if last is not None and d < last and (last - d).days > 250:
        year += 1
        d = date(year, mon, day)
    return d, year


def parse_openfootball(text: str, league_id: str) -> list[dict]:
    matches: list[dict] = []
    year: int | None = None
    cur_date: date | None = None
    cur_time = ""
    rnd = 0
    pending_block: list[str] | None = None
    depth = 0

    def flush_block():
        nonlocal pending_block, depth
        if pending_block and matches:
            block = "\n".join(pending_block)
            m = matches[-1]
            if m["homeGoals"] is not None:
                m["scorers"] = _parse_scorers(
                    block, m["home"], m["away"], m["homeGoals"], m["awayGoals"])
        pending_block, depth = None, 0

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue

        # accumulate a multi-line scorer block until parentheses balance
        if pending_block is not None:
            pending_block.append(line)
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                flush_block()
            continue

        # round header
        rh = _ROUND_RE.search(line)
        if line.strip().startswith(("▪", "»")) and rh:
            rnd = int(rh.group(1))
            continue

        # date line
        dm = _DATE_RE.match(line.strip())
        if dm:
            mon = _MONTHS.get(dm.group(2))
            day = int(dm.group(3))
            if dm.group(4):
                year = int(dm.group(4))
            if mon and year:
                cur_date, year = _roll_date(mon, day, year, cur_date)
            cur_time = ""
            continue

        # a scorer block on its own indented line
        if line.strip().startswith("("):
            pending_block = [line]
            depth = line.count("(") - line.count(")")
            if depth <= 0:
                flush_block()
            continue

        # match lines — decide which of the three layouts this is
        has_score = re.search(_SCORE, line) is not None
        has_v = re.search(r"\sv\s", line) is not None

        parsed = None
        if has_score and not has_v:
            mm = _NEW_RE.match(line)
            if mm:
                t, home, hg, ag, hh, ah, away = mm.groups()
                parsed = (t, home, away, hg, ag, hh, ah)
        elif has_v and has_score:
            mm = _OLD_RE.match(line)
            if mm:
                t, home, away, hg, ag, hh, ah = mm.groups()
                parsed = (t, home, away, hg, ag, hh, ah)
        elif has_v:
            mm = _FIX_RE.match(line)
            if mm:
                t, home, away = mm.groups()
                parsed = (t, home, away, None, None, None, None)

        if not parsed:
            continue

        t, home_raw, away_raw, hg, ag, hh, ah = parsed
        if t:
            cur_time = t
        home_code = resolve_club(league_id, _clean_team(home_raw))
        away_code = resolve_club(league_id, _clean_team(away_raw))
        if not home_code or not away_code:
            # unknown club (should not happen once leagues.py is complete)
            continue

        dt_iso = None
        if cur_date is not None:
            hh_mm = cur_time or "15:00"
            hour, minute = (int(x) for x in hh_mm.split(":"))
            dt = datetime(cur_date.year, cur_date.month, cur_date.day,
                          hour, minute, tzinfo=timezone.utc)
            dt_iso = dt.isoformat()

        matches.append({
            "round": rnd,
            "date": cur_date.isoformat() if cur_date else None,
            "datetime": dt_iso,
            "home": home_code,
            "away": away_code,
            "homeGoals": int(hg) if hg is not None else None,
            "awayGoals": int(ag) if ag is not None else None,
            "htHome": int(hh) if hh is not None else None,
            "htAway": int(ah) if ah is not None else None,
            "scorers": [],
        })

    if pending_block is not None:
        flush_block()
    return matches


# --------------------------------------------------------------------------- #
# openfootball Champions-League parsing
# --------------------------------------------------------------------------- #
# UCL team lines carry a 3-letter country code suffix, e.g. "Real Madrid CF (ESP)".
_UCL_COUNTRY_RE = re.compile(r"\s*\([A-Z]{3}\)\s*$")
# whole match line: optional kickoff time, Home (XXX) v Away (XXX), optional score
_UCL_LINE_RE = re.compile(
    r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?\([A-Z]{3}\))\s+v\s+(.+?\([A-Z]{3}\))\s*(.*?)\s*$")
# stage round assigned to knockout matches so they sort after the league phase
_UCL_STAGE_ROUND = {"playoff": 20, "r16": 30, "qf": 40, "sf": 50, "final": 60}


def _ucl_strip_country(name: str) -> str:
    return _UCL_COUNTRY_RE.sub("", name).strip()


def _ucl_stage(header: str) -> tuple[str | None, int | None]:
    """Map a ``▪`` stage header to (stage, matchday). Handles the modern
    league-phase files ("League, Matchday N" / "Playoffs, ..." / "Finals, ...")
    and the pre-2024 group-stage files ("Group A" / "Round of 16" / ...)."""
    h = header.lstrip("▪» ").strip().lower()
    if h.startswith("league"):
        md = re.search(r"matchday\s+(\d+)", h)
        return "league", int(md.group(1)) if md else 0
    if h.startswith("group"):
        return "league", 0
    if h.startswith("playoff"):
        md = re.search(r"matchday\s+(\d+)", h)
        return "playoff", int(md.group(1)) if md else 1
    if "round of 16" in h:
        return "r16", None
    if "quarterfinal" in h:
        return "qf", None
    if "semifinal" in h:
        return "sf", None
    if h.endswith("final"):
        return "final", None
    return None, None


def _parse_ucl_score(tail: str) -> tuple[int | None, int | None,
                                         tuple[int, int] | None]:
    """Extract (homeGoals, awayGoals, penalties) from a UCL score tail.

    Handles ``4-2 (1-0)`` / ``0-0`` (normal), ``0-1 a.e.t. (0-1, 0-1)``
    (extra time — the pre-a.e.t. number is the match result) and
    ``1-4 pen. 0-1 a.e.t. (0-1, 0-1)`` (shootout — penalties come first,
    then the on-pitch result). ``@ Venue`` annotations are ignored.
    """
    tail = tail.strip()
    if not tail:
        return None, None, None
    pens: tuple[int, int] | None = None
    mp = re.match(r"(\d+)-(\d+)\s+pen\.\s+(.*)$", tail)
    if mp:
        pens = (int(mp.group(1)), int(mp.group(2)))
        tail = mp.group(3).strip()
    ms = re.match(r"(\d+)-(\d+)", tail)
    if not ms:
        return None, None, pens
    return int(ms.group(1)), int(ms.group(2)), pens


def parse_openfootball_ucl(text: str, league_id: str,
                           loose: bool = False) -> list[dict]:
    """Parse an openfootball Champions-League file into normalised match rows.

    ``loose`` uses the fuzzy resolver (synthetic codes for clubs outside the
    registry) so the historical back-catalogue can train the models even though
    only the two shipped seasons' clubs are in ``ucl_clubs.py``.
    """
    resolve = resolve_club_loose if loose else resolve_club
    matches: list[dict] = []
    year: int | None = None
    cur_date: date | None = None
    cur_time = ""
    stage = "league"
    matchday = 0

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # stage header
        if stripped.startswith(("▪", "»")):
            st, md = _ucl_stage(stripped)
            if st:
                stage = st
                matchday = md if md is not None else 0
            continue

        # date line
        dm = _DATE_RE.match(stripped)
        if dm:
            mon = _MONTHS.get(dm.group(2))
            day = int(dm.group(3))
            if dm.group(4):
                year = int(dm.group(4))
            if mon and year:
                cur_date, year = _roll_date(mon, day, year, cur_date)
            cur_time = ""
            continue

        lm = _UCL_LINE_RE.match(line)
        if not lm:
            continue
        t, home_raw, away_raw, tail = lm.groups()
        if t:
            cur_time = t

        home_code = resolve(league_id, _ucl_strip_country(home_raw))
        away_code = resolve(league_id, _ucl_strip_country(away_raw))
        if not home_code or not away_code:
            continue

        hg, ag, pens = _parse_ucl_score(tail or "")

        if stage == "league":
            rnd = matchday
        else:
            rnd = _UCL_STAGE_ROUND.get(stage, 0) + matchday

        dt_iso = None
        if cur_date is not None:
            hh_mm = cur_time or "21:00"
            hour, minute = (int(x) for x in hh_mm.split(":"))
            dt = datetime(cur_date.year, cur_date.month, cur_date.day,
                          hour, minute, tzinfo=timezone.utc)
            dt_iso = dt.isoformat()

        matches.append({
            "round": rnd,
            "stage": stage,
            "date": cur_date.isoformat() if cur_date else None,
            "datetime": dt_iso,
            "home": home_code,
            "away": away_code,
            "homeGoals": hg,
            "awayGoals": ag,
            "htHome": None,
            "htAway": None,
            "homePens": pens[0] if pens else None,
            "awayPens": pens[1] if pens else None,
            "scorers": [],
        })

    return matches


# --------------------------------------------------------------------------- #
# football-data.co.uk parsing
# --------------------------------------------------------------------------- #
def _to_int(v: str) -> int | None:
    v = (v or "").strip()
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _to_float(v: str) -> float | None:
    v = (v or "").strip()
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _fd_rows(csv_text: str, league_id: str) -> list[dict]:
    """Parse a football-data.co.uk CSV into ordered match rows (with dates)."""
    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    for row in reader:
        home = resolve_club_loose(league_id, (row.get("HomeTeam") or "").strip())
        away = resolve_club_loose(league_id, (row.get("AwayTeam") or "").strip())
        if not home or not away:
            continue
        hg, ag = _to_int(row.get("FTHG", "")), _to_int(row.get("FTAG", ""))
        d = _parse_fd_date(row.get("Date", ""))

        def stat(k):
            return _to_int(row.get(k, ""))

        odds = None
        for h, dd, a in (("AvgH", "AvgD", "AvgA"), ("B365H", "B365D", "B365A"),
                         ("PSH", "PSD", "PSA")):
            oh, od, oa = _to_float(row.get(h)), _to_float(row.get(dd)), _to_float(row.get(a))
            if oh and od and oa and oh > 1 and od > 1 and oa > 1:
                inv = [1 / oh, 1 / od, 1 / oa]
                s = sum(inv)
                odds = {"home": round(inv[0] / s, 4),
                        "draw": round(inv[1] / s, 4),
                        "away": round(inv[2] / s, 4)}
                break

        rows.append({
            "date": d.isoformat() if d else None,
            "home": home, "away": away,
            "homeGoals": hg, "awayGoals": ag,
            "shots": {"home": stat("HS"), "away": stat("AS")},
            "shotsOnTarget": {"home": stat("HST"), "away": stat("AST")},
            "corners": {"home": stat("HC"), "away": stat("AC")},
            "fouls": {"home": stat("HF"), "away": stat("AF")},
            "yellows": {"home": stat("HY"), "away": stat("AY")},
            "reds": {"home": stat("HR"), "away": stat("AR")},
            "marketOdds": odds,
            "referee": (row.get("Referee") or "").strip() or None,
        })
    return rows


def _parse_fd_date(s: str):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_football_data(csv_text: str, league_id: str) -> dict[tuple[str, str], dict]:
    """Return {(home_code, away_code): {stats + odds}} for finished matches."""
    out: dict[tuple[str, str], dict] = {}
    for r in _fd_rows(csv_text, league_id):
        out[(r["home"], r["away"])] = {
            "shots": r["shots"], "shotsOnTarget": r["shotsOnTarget"],
            "corners": r["corners"], "fouls": r["fouls"],
            "yellows": r["yellows"], "reds": r["reds"],
            "marketOdds": r["marketOdds"], "referee": r["referee"],
        }
    return out


def parse_fd_history(csv_text: str, league_id: str) -> list[dict]:
    """Ordered, completed match rows from a football-data CSV (for training/Elo)."""
    return [r for r in _fd_rows(csv_text, league_id)
            if r["homeGoals"] is not None and r["awayGoals"] is not None]


# --------------------------------------------------------------------------- #
# Loaders (read the committed caches)
# --------------------------------------------------------------------------- #
def _combo_source_dir(league_id: str, season_id: str) -> str:
    return os.path.join(SOURCE_DIR, league_id, season_id)


def load_matches(league_id: str, season_id: str) -> list[dict]:
    """Load + merge openfootball results with football-data stats for one combo.

    A tournament season whose openfootball file has not been published yet (the
    Champions League 2026-27 before the late-August draw) has no fixtures source
    on disk. That is expected for a preseason edition, so we return an empty
    match list rather than raising — the club field is seeded from the committed
    ``participants.json`` bootstrap instead (see ``club_ingest.ingest_season``).
    """
    d = _combo_source_dir(league_id, season_id)
    of_path = os.path.join(d, "openfootball.txt")
    fd_path = os.path.join(d, "footballdata.csv")

    if not os.path.exists(of_path):
        return []

    with open(of_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    if LEAGUES[league_id].format == "tournament":
        # the Champions League has no football-data feed (no shots/odds); its
        # matches are results-only plus knockout metadata (stage, penalties).
        matches = parse_openfootball_ucl(text, league_id)
        for m in matches:
            m["matchStats"] = None
            m["marketOdds"] = None
        return matches

    matches = parse_openfootball(text, league_id)

    stats: dict[tuple[str, str], dict] = {}
    if os.path.exists(fd_path):
        with open(fd_path, "r", encoding="utf-8", errors="replace") as fh:
            stats = parse_football_data(fh.read(), league_id)

    for m in matches:
        extra = stats.get((m["home"], m["away"]))
        m["matchStats"] = extra or None
        m["marketOdds"] = (extra or {}).get("marketOdds")

    return matches
