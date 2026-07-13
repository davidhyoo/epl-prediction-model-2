"""
sources.py  —  real, openly-licensed data parsers
=================================================
Turns the cached CC0 source files in ``data/source/`` into the structured
records the pipeline needs. NO network access happens here (the refresh script
is what re-downloads the caches); these parsers are pure and deterministic so
``python ml/pipeline.py`` reproduces identical data offline.

Sources
-------
* martj42/international_results (``results.csv``) — every men's international
  1872→present. Public domain (CC0). Used for training history + real Elo.
* openfootball/worldcup ``2026--usa`` (``cup.txt`` + ``cup_finals.txt``) — the
  real 2026 group draw, fixtures, results and knockout bracket. Public domain
  (CC0). Football.TXT DSL — parsed below.

See the README "Data Sources" section for licensing notes.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone

import pandas as pd

from common import DATA_DIR

SOURCE_DIR = os.path.join(DATA_DIR, "source")
MARTJ42_RESULTS = os.path.join(SOURCE_DIR, "martj42_results.csv")
OPENFOOTBALL_GROUPS = os.path.join(SOURCE_DIR, "openfootball_cup.txt")
OPENFOOTBALL_FINALS = os.path.join(SOURCE_DIR, "openfootball_cup_finals.txt")
SQUADS_WIKIPEDIA = os.path.join(SOURCE_DIR, "squads_wikipedia.json")

# The World Cup opener — any earlier international is training history; the
# tournament itself is never used to train (leakage-free).
WC_START = datetime(2026, 6, 11, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Team-name → FIFA-code mapping (covers openfootball + martj42 spellings)
# --------------------------------------------------------------------------- #
# Every alias is normalised (see ``_norm``) before lookup, so accents / spacing
# differences are tolerant. Only the 48 real 2026 qualifiers are mapped; every
# other national side stays keyed by its raw name for Elo purposes.
_ALIASES: dict[str, list[str]] = {
    "MEX": ["Mexico"],
    "RSA": ["South Africa"],
    "KOR": ["South Korea", "Korea Republic", "Korea, South"],
    "CZE": ["Czech Republic", "Czechia"],
    "CAN": ["Canada"],
    "BIH": ["Bosnia & Herzegovina", "Bosnia and Herzegovina", "Bosnia-Herzegovina"],
    "QAT": ["Qatar"],
    "SUI": ["Switzerland"],
    "BRA": ["Brazil"],
    "MAR": ["Morocco"],
    "HAI": ["Haiti"],
    "SCO": ["Scotland"],
    "USA": ["USA", "United States"],
    "PAR": ["Paraguay"],
    "AUS": ["Australia"],
    "TUR": ["Turkey", "Turkiye", "Türkiye"],
    "GER": ["Germany"],
    "CUW": ["Curacao", "Curaçao"],
    "CIV": ["Ivory Coast", "Cote d'Ivoire", "Côte d'Ivoire"],
    "ECU": ["Ecuador"],
    "NED": ["Netherlands"],
    "JPN": ["Japan"],
    "SWE": ["Sweden"],
    "TUN": ["Tunisia"],
    "BEL": ["Belgium"],
    "EGY": ["Egypt"],
    "IRN": ["Iran", "IR Iran"],
    "NZL": ["New Zealand"],
    "ESP": ["Spain"],
    "CPV": ["Cape Verde", "Cabo Verde"],
    "SAU": ["Saudi Arabia"],
    "URU": ["Uruguay"],
    "FRA": ["France"],
    "SEN": ["Senegal"],
    "IRQ": ["Iraq"],
    "NOR": ["Norway"],
    "ARG": ["Argentina"],
    "ALG": ["Algeria"],
    "AUT": ["Austria"],
    "JOR": ["Jordan"],
    "POR": ["Portugal"],
    "COD": ["DR Congo", "Congo DR", "Congo Kinshasa", "Democratic Republic of the Congo"],
    "UZB": ["Uzbekistan"],
    "COL": ["Colombia"],
    "ENG": ["England"],
    "CRO": ["Croatia"],
    "GHA": ["Ghana"],
    "PAN": ["Panama"],
}


def _norm(name: str) -> str:
    """Normalise a team name for tolerant matching (strip accents/spacing)."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", "and").replace(".", "").replace("'", "'")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


_CODE_BY_NAME: dict[str, str] = {}
for _code, _names in _ALIASES.items():
    for _n in _names:
        _CODE_BY_NAME[_norm(_n)] = _code


def wc_code(name: str) -> str | None:
    """Return the FIFA code for a 2026 qualifier, or None for any other team."""
    return _CODE_BY_NAME.get(_norm(name))


# --------------------------------------------------------------------------- #
# Host stadiums (from the openfootball header) keyed by the '@ city' text
# --------------------------------------------------------------------------- #
STADIUMS = {
    "Mexico City": "Estadio Azteca",
    "Guadalajara (Zapopan)": "Estadio Akron",
    "Monterrey (Guadalupe)": "Estadio BBVA",
    "Atlanta": "Mercedes-Benz Stadium",
    "Boston (Foxborough)": "Gillette Stadium",
    "Dallas (Arlington)": "AT&T Stadium",
    "Houston": "NRG Stadium",
    "Kansas City": "Arrowhead Stadium",
    "Los Angeles (Inglewood)": "SoFi Stadium",
    "Miami (Miami Gardens)": "Hard Rock Stadium",
    "New York/New Jersey (East Rutherford)": "MetLife Stadium",
    "Philadelphia": "Lincoln Financial Field",
    "San Francisco Bay Area (Santa Clara)": "Levi's Stadium",
    "Seattle": "Lumen Field",
    "Toronto": "BMO Field",
    "Vancouver": "BC Place",
}

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["", "January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"])}
for _i, _abbr in enumerate(
        ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
    _MONTHS[_abbr.lower()] = _i


# --------------------------------------------------------------------------- #
# martj42 international results  →  history rows
# --------------------------------------------------------------------------- #
def parse_martj42(path: str = MARTJ42_RESULTS) -> list[dict]:
    """
    Read every played international and return chronological history rows:

        {date, home_name, away_name, home_code|None, away_code|None,
         gh, ga, neutral(0/1), tournament}

    Rows with no score (future/unplayed fixtures) are dropped. The World Cup
    itself (date >= WC_START) is EXCLUDED — those results come from openfootball
    and must never leak into training/pre-tournament Elo.
    """
    df = pd.read_csv(path)
    df = df.dropna(subset=["home_score", "away_score"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df[df["date"] < pd.Timestamp(WC_START.replace(tzinfo=None))]
    df = df.sort_values("date", kind="stable")

    rows: list[dict] = []
    for i, r in enumerate(df.itertuples(index=False)):
        home, away = str(r.home_team), str(r.away_team)
        rows.append({
            "id": f"H{i:06d}",
            "date": r.date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "home_name": home, "away_name": away,
            "home_code": wc_code(home), "away_code": wc_code(away),
            "gh": int(r.home_score), "ga": int(r.away_score),
            "neutral": 1 if str(r.neutral).strip().lower() == "true" else 0,
            "tournament": str(r.tournament),
        })
    return rows


# --------------------------------------------------------------------------- #
# openfootball Football.TXT parsing helpers
# --------------------------------------------------------------------------- #
_SCORE_RE = re.compile(
    r"^(?P<home>.+?)\s+"
    r"(?P<g1>\d+)-(?P<g2>\d+)"                       # main score (a.e.t. if flagged)
    r"(?P<aet>\s+a\.e\.t\.)?"
    r"(?:\s*\((?P<paren>[^)]*)\))?"                  # (FT, HT) or (HT)
    r"(?:\s*,?\s*(?P<ph>\d+)-(?P<pa>\d+)\s+pen\.?)?"  # penalty shootout
    r"\s+(?P<away>.+?)\s*$"
)
_TIME_RE = re.compile(r"^\s*\d{1,2}:\d{2}\s+UTC[+-]\d+\s+")
_MATCHNUM_RE = re.compile(r"^\s*\((\d+)\)\s*")
_DATE_RE = re.compile(r"^[A-Za-z]{3}\s+([A-Za-z]+)\s+(\d{1,2})\s*$")
_TIME_ONLY_RE = re.compile(r"(\d{1,2}):(\d{2})\s+UTC([+-]\d+)")


def _parse_date(text: str, hh: int = 16, mm: int = 0, off: int = 0) -> str:
    """Football.TXT date header ('Thu June 11' / 'Sun Jun 28') → ISO UTC."""
    m = _DATE_RE.match(text.strip())
    mon = _MONTHS[m.group(1).lower()]
    day = int(m.group(2))
    # local kickoff time at UTC offset `off` → convert to UTC
    dt = datetime(2026, mon, day, hh, mm, tzinfo=timezone.utc)
    # UTC = local - offset (offset is negative in the Americas, e.g. UTC-6)
    from datetime import timedelta
    dt = dt - timedelta(hours=off)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _split_venue(core: str) -> tuple[str, str, str]:
    """Split a match line on '@' and '##' → (match_part, city, refs)."""
    match_part, _, rest = core.partition("@")
    city, _, refs = rest.partition("##")
    return match_part.strip(), city.strip(), refs.strip()


def _feeder(token: str):
    """Parse a 'W74' / 'L101' bracket reference → ('W'|'L', num); else None."""
    m = re.match(r"^([WL])(\d+)$", token.strip())
    return (m.group(1), int(m.group(2))) if m else None


def _parse_scored(match_part: str) -> dict | None:
    """Parse the '<home> <score> <away>' core into a normalised result dict."""
    m = _SCORE_RE.match(match_part)
    if not m:
        return None
    aet = bool(m.group("aet"))
    g1, g2 = int(m.group("g1")), int(m.group("g2"))
    paren = (m.group("paren") or "").strip()
    ph = int(m.group("ph")) if m.group("ph") else None
    pa = int(m.group("pa")) if m.group("pa") else None

    if aet:
        # main score is after extra time; first paren pair is the 90-minute score
        fh, fa = g1, g2                              # final on-pitch (a.e.t.)
        reg = paren.split(",")[0].strip() if paren else f"{g1}-{g2}"
        rm = re.match(r"(\d+)-(\d+)", reg)
        gh, ga = (int(rm.group(1)), int(rm.group(2))) if rm else (g1, g2)
    else:
        gh, ga = g1, g2                              # 90-minute score
        fh, fa = g1, g2

    pens = [ph, pa] if (ph is not None and pa is not None) else None
    # advancing side (knockouts): final score, else penalties
    if fh > fa:
        winner = "home"
    elif fa > fh:
        winner = "away"
    elif pens:
        winner = "home" if pens[0] > pens[1] else "away"
    else:
        winner = None                                # a genuine draw (group stage)
    return {"home": m.group("home").strip(), "away": m.group("away").strip(),
            "gh": gh, "ga": ga, "fh": fh, "fa": fa, "pens": pens,
            "winner": winner, "aet": aet}


# --------------------------------------------------------------------------- #
# openfootball group stage  →  WC group matches
# --------------------------------------------------------------------------- #
def parse_group_stage(path: str = OPENFOOTBALL_GROUPS) -> list[dict]:
    """Parse ``cup.txt`` → list of group-stage match dicts (all completed)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    matches: list[dict] = []
    cur_group: str | None = None
    cur_date: str | None = None
    group_counts: dict[str, int] = {}

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        gm = re.match(r"^▪\s*Group\s+([A-L])\s*$", stripped)
        if gm:
            cur_group = gm.group(1)
            group_counts.setdefault(cur_group, 0)
            continue
        if stripped.startswith("▪") or stripped.startswith("#") or stripped.startswith("="):
            continue                                  # matchday calendar / comments
        if stripped.startswith("Group "):
            continue                                  # group membership definition line
        if cur_group is None:
            continue
        if _DATE_RE.match(stripped):
            cur_date = stripped
            continue
        if "@" not in line:
            continue                                  # goalscorer continuation line

        tm = _TIME_ONLY_RE.search(line)
        hh, mm, off = (int(tm.group(1)), int(tm.group(2)), int(tm.group(3))) if tm else (16, 0, 0)
        core = _TIME_RE.sub("", line).strip()
        match_part, city, _ = _split_venue(core)
        res = _parse_scored(match_part)
        if res is None:
            continue
        hc, ac = wc_code(res["home"]), wc_code(res["away"])
        if not (hc and ac):
            raise ValueError(f"Unmapped group team: {res['home']!r} / {res['away']!r}")

        idx = group_counts[cur_group]
        group_counts[cur_group] += 1
        matches.append({
            "id": f"G{cur_group}{idx}",
            "stage": "group", "group": cur_group,
            "matchday": idx // 2 + 1, "slot": idx, "num": None,
            "date": _parse_date(cur_date, hh, mm, off),
            "venue": STADIUMS.get(city, city), "city": city,
            "home": hc, "away": ac,
            "home_adv": _host_adv(hc, ac),
            "gh": res["gh"], "ga": res["ga"], "fh": res["fh"], "fa": res["fa"],
            "pens": res["pens"], "winner": res["winner"], "played": True,
            "feedHome": None, "feedAway": None,
        })
    return matches


# --------------------------------------------------------------------------- #
# openfootball knockout stage  →  WC knockout matches (with bracket feeders)
# --------------------------------------------------------------------------- #
_STAGE_BY_HEADER = {
    "round of 32": "round-of-32", "round of 16": "round-of-16",
    "quarter-final": "quarter-final", "quarter-finals": "quarter-final",
    "semi-final": "semi-final", "semi-finals": "semi-final",
    "match for third place": "third-place", "third place": "third-place",
    "final": "final",
}
_STAGE_BASE = {"round-of-32": 73, "round-of-16": 89, "quarter-final": 97,
               "semi-final": 101, "third-place": 103, "final": 104}


def parse_knockouts(path: str = OPENFOOTBALL_FINALS) -> list[dict]:
    """Parse ``cup_finals.txt`` → list of knockout match dicts.

    Unplayed matches (``France v Spain``) and TBD matches (``W101 v W102``) are
    included with ``home``/``away`` = None where the participant is not yet
    known; bracket feeders (``feedHome``/``feedAway`` = ('W'|'L', num)) let the
    simulator resolve them from earlier results.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    matches: list[dict] = []
    cur_stage: str | None = None
    cur_date: str | None = None

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("▪"):
            key = stripped.lstrip("▪").strip().lower()
            cur_stage = _STAGE_BY_HEADER.get(key)
            continue
        if stripped.startswith("#") or stripped.startswith("="):
            continue
        if _DATE_RE.match(stripped):
            cur_date = stripped
            continue
        num_m = _MATCHNUM_RE.match(line)
        if not num_m:
            continue                                  # goalscorer continuation line
        num = int(num_m.group(1))

        tm = _TIME_ONLY_RE.search(line)
        hh, mm, off = (int(tm.group(1)), int(tm.group(2)), int(tm.group(3))) if tm else (16, 0, 0)
        core = _MATCHNUM_RE.sub("", line)
        core = _TIME_RE.sub("", core).strip()
        match_part, city, refs = _split_venue(core)

        feed_home = feed_away = None
        if refs:
            parts = [p.strip() for p in refs.split("/")]
            if len(parts) == 2:
                feed_home, feed_away = _feeder(parts[0]), _feeder(parts[1])

        res = _parse_scored(match_part)
        if res is not None:
            hc, ac = wc_code(res["home"]), wc_code(res["away"])
            if not (hc and ac):
                raise ValueError(f"Unmapped knockout team: {res['home']!r}/{res['away']!r}")
            row = {
                "home": hc, "away": ac,
                "gh": res["gh"], "ga": res["ga"], "fh": res["fh"], "fa": res["fa"],
                "pens": res["pens"], "winner": res["winner"], "played": True,
            }
        else:
            # unplayed — split on ' v '; tokens are team names or W##/L## refs
            hv, _, av = match_part.partition(" v ")
            ht, at = hv.strip(), av.strip()
            if feed_home is None:
                feed_home = _feeder(ht)
            if feed_away is None:
                feed_away = _feeder(at)
            row = {
                "home": wc_code(ht), "away": wc_code(at),
                "gh": None, "ga": None, "fh": None, "fa": None,
                "pens": None, "winner": None, "played": False,
            }

        stage = cur_stage
        base = _STAGE_BASE.get(stage, num)
        ha = _host_adv(row["home"], row["away"]) if (row["home"] and row["away"]) else 0
        matches.append({
            "id": f"K{num:03d}", "num": num,
            "stage": stage, "group": None, "matchday": None,
            "slot": num - base,
            "date": _parse_date(cur_date, hh, mm, off),
            "venue": STADIUMS.get(city, city), "city": city,
            "home_adv": ha,
            "feedHome": list(feed_home) if feed_home else None,
            "feedAway": list(feed_away) if feed_away else None,
            **row,
        })
    return matches


# --------------------------------------------------------------------------- #
# Host advantage indicator (signed): +1 home host, -1 away host, else 0
# --------------------------------------------------------------------------- #
_HOSTS = {"USA", "CAN", "MEX"}


def _host_adv(home_code: str | None, away_code: str | None) -> int:
    if home_code in _HOSTS and away_code not in _HOSTS:
        return 1
    if away_code in _HOSTS and home_code not in _HOSTS:
        return -1
    return 0


# --------------------------------------------------------------------------- #
# Real national-team squads (cached from Wikipedia by ml/fetch_players.py)
# --------------------------------------------------------------------------- #
def load_squads(path: str = SQUADS_WIKIPEDIA) -> dict | None:
    """Return the cached real squads as ``{code: [player_row, ...]}``.

    Each player row carries the fields ``ml/fetch_players.py`` wrote: ``id``,
    ``name``, ``position`` (GK/DEF/MID/FWD), ``detailedPosition``,
    ``shirtNumber``, ``age``, ``caps``, ``intlGoals``, ``club``, ``clubCountry``,
    ``isCaptain``, ``headshot`` and ``photoCredit``.

    Returns ``None`` when the cache is missing or unreadable so the pipeline can
    fall back to deterministically generated squads (keeping the app runnable
    fully offline even if the fetch has never been run).
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    squads = data.get("squads")
    if not isinstance(squads, dict) or not squads:
        return None
    return squads
