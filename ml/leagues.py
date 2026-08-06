"""
leagues.py
==========
Central configuration for the club-football (league) prediction pipeline that
powers the EPL + La Liga dashboard.

Everything the pipeline needs that is *not* derived from the downloaded data
lives here:

  * paths & reproducibility seed
  * the league registry (EPL, La Liga) — display metadata + the open-data URLs
  * the season registry (validation vs. deliverable seasons)
  * club metadata (canonical 3-letter code, display/short name, brand colours,
    Wikipedia article for squad lookups) and a robust **name-alias resolver**
    so the many spellings used across openfootball / football-data.co.uk /
    Wikipedia all collapse onto one canonical club.

Club **crests are trademarks**, so no crest image is committed to this repo. The
UI hot-links a verified crest *URL* per club (see `club_crests.py` →
`src/lib/crests.json`) and falls back to a tasteful coloured initials badge, built
from these brand colours, whenever a crest can't load.

All data sources are free / openly licensed (CC0 openfootball, free
football-data.co.uk, CC BY-SA Wikipedia text + free-licensed Commons photos);
see the README "Data sources" section.
"""
from __future__ import annotations

import hashlib
import os
import unicodedata
from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ML_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(ML_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
SOURCE_DIR = os.path.join(DATA_DIR, "source")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CACHED_DIR = os.path.join(DATA_DIR, "cached")
MODELS_DIR = os.path.join(ML_DIR, "models")
OUTPUTS_DIR = os.path.join(ML_DIR, "outputs")
PUBLIC_DATA_DIR = os.path.join(ROOT_DIR, "public", "data")

for _d in (SOURCE_DIR, RAW_DIR, PROCESSED_DIR, CACHED_DIR, MODELS_DIR,
           OUTPUTS_DIR, PUBLIC_DATA_DIR):
    os.makedirs(_d, exist_ok=True)

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
SEED = 2026


def rng(salt: str = "") -> np.random.Generator:
    """Deterministic numpy Generator, optionally namespaced by ``salt``."""
    h = int(hashlib.sha256(f"{SEED}:{salt}".encode()).hexdigest(), 16) % (2**32)
    return np.random.default_rng(h)


# --------------------------------------------------------------------------- #
# Elo / goals model constants (shared by features / modelling)
# --------------------------------------------------------------------------- #
HOME_ADV = 65.0          # Elo-equivalent home advantage (club football)
ELO_K = 20.0             # Elo update factor for league matches
ELO_BASELINE = 1500.0    # every club starts here before its history is walked
LEAGUE_AVG_GOALS = 1.45  # avg goals per team per match (top-5 leagues)
GOALS_GAMMA = 0.60       # sensitivity of expected goals to the rating gap

POINTS_WIN, POINTS_DRAW = 3, 0


# --------------------------------------------------------------------------- #
# Club metadata
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Club:
    code: str
    name: str
    short: str
    primary: str
    secondary: str
    wiki: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


# code, display name, short, primary, secondary, wiki article, extra aliases
_EPL_CLUBS = [
    Club("ARS", "Arsenal", "Arsenal", "#EF0107", "#023474", "Arsenal F.C.",
         ("Arsenal FC",)),
    Club("AVL", "Aston Villa", "Aston Villa", "#95BFE5", "#670E36", "Aston Villa F.C.",
         ("Aston Villa FC",)),
    Club("BOU", "AFC Bournemouth", "Bournemouth", "#DA291C", "#000000", "AFC Bournemouth",
         ("Bournemouth",)),
    Club("BRE", "Brentford", "Brentford", "#E30613", "#140E0C", "Brentford F.C.",
         ("Brentford FC",)),
    Club("BHA", "Brighton & Hove Albion", "Brighton", "#0057B8", "#FFCD00",
         "Brighton & Hove Albion F.C.", ("Brighton & Hove Albion FC", "Brighton")),
    Club("BUR", "Burnley", "Burnley", "#6C1D45", "#99D6EA", "Burnley F.C.",
         ("Burnley FC",)),
    Club("CHE", "Chelsea", "Chelsea", "#034694", "#DBA111", "Chelsea F.C.",
         ("Chelsea FC",)),
    Club("COV", "Coventry City", "Coventry", "#41B6E6", "#231F20", "Coventry City F.C.",
         ("Coventry City FC", "Coventry")),
    Club("CRY", "Crystal Palace", "Crystal Palace", "#1B458F", "#C4122E",
         "Crystal Palace F.C.", ("Crystal Palace FC",)),
    Club("EVE", "Everton", "Everton", "#003399", "#FFFFFF", "Everton F.C.",
         ("Everton FC",)),
    Club("FUL", "Fulham", "Fulham", "#191919", "#CC0000", "Fulham F.C.",
         ("Fulham FC",)),
    Club("HUL", "Hull City", "Hull City", "#F18A01", "#000000", "Hull City A.F.C.",
         ("Hull City AFC", "Hull")),
    Club("IPS", "Ipswich Town", "Ipswich", "#3A64A3", "#DE2110", "Ipswich Town F.C.",
         ("Ipswich Town FC", "Ipswich")),
    Club("LEE", "Leeds United", "Leeds", "#1D428A", "#FFCD00", "Leeds United F.C.",
         ("Leeds United FC", "Leeds")),
    Club("LIV", "Liverpool", "Liverpool", "#C8102E", "#00B2A9", "Liverpool F.C.",
         ("Liverpool FC",)),
    Club("MCI", "Manchester City", "Man City", "#6CABDD", "#1C2C5B",
         "Manchester City F.C.", ("Manchester City FC", "Man City")),
    Club("MUN", "Manchester United", "Man United", "#DA291C", "#FBE122",
         "Manchester United F.C.", ("Manchester United FC", "Man United", "Man Utd")),
    Club("NEW", "Newcastle United", "Newcastle", "#241F20", "#FFFFFF",
         "Newcastle United F.C.", ("Newcastle United FC", "Newcastle")),
    Club("NFO", "Nottingham Forest", "Nott'm Forest", "#DD0000", "#FFFFFF",
         "Nottingham Forest F.C.", ("Nottingham Forest FC", "Nott'm Forest", "Nottm Forest")),
    Club("SUN", "Sunderland", "Sunderland", "#EB172B", "#211E1F", "Sunderland A.F.C.",
         ("Sunderland AFC",)),
    Club("TOT", "Tottenham Hotspur", "Tottenham", "#132257", "#FFFFFF",
         "Tottenham Hotspur F.C.", ("Tottenham Hotspur FC", "Tottenham", "Spurs")),
    Club("WHU", "West Ham United", "West Ham", "#7A263A", "#1BB1E7",
         "West Ham United F.C.", ("West Ham United FC", "West Ham")),
    Club("WOL", "Wolverhampton Wanderers", "Wolves", "#FDB913", "#231F20",
         "Wolverhampton Wanderers F.C.", ("Wolverhampton Wanderers FC", "Wolves")),
]

_LALIGA_CLUBS = [
    Club("ATH", "Athletic Club", "Athletic", "#EE2523", "#FFFFFF", "Athletic Bilbao",
         ("Athletic Club", "Ath Bilbao", "Athletic Bilbao")),
    Club("ATM", "Atlético Madrid", "Atlético", "#CB3524", "#262E62",
         "Atlético Madrid", ("Atlético de Madrid", "Club Atlético de Madrid",
                             "Atletico Madrid", "Ath Madrid", "Atletico de Madrid")),
    Club("BAR", "Barcelona", "Barcelona", "#A50044", "#004D98", "FC Barcelona",
         ("FC Barcelona", "Barcelona")),
    Club("OSA", "CA Osasuna", "Osasuna", "#0A346F", "#D91A21", "CA Osasuna",
         ("Osasuna",)),
    Club("ALA", "Deportivo Alavés", "Alavés", "#1F6FB2", "#FFFFFF", "Deportivo Alavés",
         ("Deportivo Alaves", "Alaves", "Alavés")),
    Club("ELC", "Elche CF", "Elche", "#00913F", "#FFFFFF", "Elche CF", ("Elche",)),
    Club("GET", "Getafe CF", "Getafe", "#005999", "#FFFFFF", "Getafe CF", ("Getafe",)),
    Club("GIR", "Girona FC", "Girona", "#CD2534", "#E30613", "Girona FC", ("Girona",)),
    Club("LEV", "Levante UD", "Levante", "#0055A5", "#B4053F", "Levante UD",
         ("Levante",)),
    Club("MLL", "RCD Mallorca", "Mallorca", "#E20613", "#000000", "RCD Mallorca",
         ("Mallorca",)),
    Club("RAY", "Rayo Vallecano", "Rayo", "#E53027", "#FFFFFF", "Rayo Vallecano",
         ("Rayo Vallecano de Madrid", "Vallecano", "Rayo")),
    Club("CEL", "RC Celta", "Celta", "#8AC3EE", "#E4373D", "RC Celta",
         ("RC Celta de Vigo", "Celta Vigo", "Celta", "RC Celta")),
    Club("ESP", "RCD Espanyol", "Espanyol", "#0069B4", "#FFFFFF", "RCD Espanyol",
         ("RCD Espanyol de Barcelona", "Espanol", "Espanyol")),
    Club("BET", "Real Betis", "Betis", "#00954C", "#FFFFFF", "Real Betis",
         ("Real Betis Balompié", "Real Betis Balompie", "Betis")),
    Club("RMA", "Real Madrid", "Real Madrid", "#00529F", "#FEBE10", "Real Madrid CF",
         ("Real Madrid C.F.", "Real Madrid CF", "Real Madrid")),
    Club("OVI", "Real Oviedo", "Oviedo", "#0B5AA2", "#FFFFFF", "Real Oviedo",
         ("Oviedo",)),
    Club("RSO", "Real Sociedad", "Real Sociedad", "#0067B1", "#FFFFFF", "Real Sociedad",
         ("Real Sociedad de Fútbol", "Real Sociedad de Futbol", "Sociedad")),
    Club("SEV", "Sevilla FC", "Sevilla", "#D91A21", "#FFFFFF", "Sevilla FC",
         ("Sevilla",)),
    Club("VAL", "Valencia CF", "Valencia", "#F18E00", "#000000", "Valencia CF",
         ("Valencia",)),
    Club("VIL", "Villarreal CF", "Villarreal", "#FFD100", "#005187", "Villarreal CF",
         ("Villarreal",)),
    # Promoted for 2026-27 (openfootball projected field)
    Club("MAL", "Málaga CF", "Málaga", "#003DA5", "#FFFFFF", "Málaga CF",
         ("Malaga CF", "Malaga", "Málaga")),
    Club("DEP", "Deportivo La Coruña", "Deportivo", "#009FE3", "#FFFFFF",
         "Deportivo de La Coruña", ("RC Deportivo La Coruña", "Deportivo La Coruna",
                                    "Deportivo", "La Coruna")),
    Club("RAC", "Racing Santander", "Racing", "#009B48", "#FFFFFF",
         "Racing de Santander", ("Real Racing Club de Santander", "Racing Santander",
                                 "Racing")),
]


# --------------------------------------------------------------------------- #
# League registry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class League:
    id: str
    name: str
    short: str
    country: str
    iso2: str          # for the league badge flag
    accent: str        # brand accent colour used in the UI
    of_repo: str       # openfootball repo
    of_file: str       # openfootball file within a season directory
    fd_code: str       # football-data.co.uk division code (E0 / SP1)
    clubs: tuple[Club, ...]


LEAGUES: dict[str, League] = {
    "epl": League(
        id="epl", name="English Premier League", short="Premier League",
        country="England", iso2="gb-eng", accent="#37003C",
        of_repo="england", of_file="1-premierleague.txt", fd_code="E0",
        clubs=tuple(_EPL_CLUBS),
    ),
    "laliga": League(
        id="laliga", name="Spanish La Liga", short="La Liga",
        country="Spain", iso2="es", accent="#E4002B",
        of_repo="espana", of_file="1-liga.txt", fd_code="SP1",
        clubs=tuple(_LALIGA_CLUBS),
    ),
}

LEAGUE_IDS = list(LEAGUES.keys())


# --------------------------------------------------------------------------- #
# Season registry
#   role="validation" -> a completed season used to prove the pipeline works
#   role="deliverable" -> the upcoming season (may be fixtures-only)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Season:
    id: str            # "2025-26"
    label: str         # "2025/26"
    role: str          # validation | deliverable
    start_year: int    # 2025


SEASONS: dict[str, Season] = {
    "2025-26": Season("2025-26", "2025/26", "validation", 2025),
    "2026-27": Season("2026-27", "2026/27", "deliverable", 2026),
}

SEASON_IDS = list(SEASONS.keys())

# The combinations the pipeline builds and the app exposes.
COMBOS = [(lg, sn) for lg in LEAGUE_IDS for sn in SEASON_IDS]

# Default view the app opens on: a completed season (rich data on first load).
DEFAULT_LEAGUE = "epl"
DEFAULT_SEASON = "2025-26"


# --------------------------------------------------------------------------- #
# Name normalisation + alias resolution
# --------------------------------------------------------------------------- #
def normalize_name(s: str) -> str:
    """Fold a club name to a comparable key (lower, de-accented, punctuation-free)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    for ch in ".,'`&-/":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def _build_alias_index(league: League) -> dict[str, str]:
    idx: dict[str, str] = {}
    for club in league.clubs:
        keys = {club.name, club.short, club.code, *club.aliases}
        for k in keys:
            idx[normalize_name(k)] = club.code
    return idx


_ALIAS_INDEX: dict[str, dict[str, str]] = {
    lg_id: _build_alias_index(lg) for lg_id, lg in LEAGUES.items()
}
_CLUB_BY_CODE: dict[str, dict[str, Club]] = {
    lg_id: {c.code: c for c in lg.clubs} for lg_id, lg in LEAGUES.items()
}


def resolve_club(league_id: str, raw_name: str) -> str | None:
    """Map a raw club name (any known spelling) to its canonical code, or None."""
    idx = _ALIAS_INDEX[league_id]
    key = normalize_name(raw_name)
    if key in idx:
        return idx[key]
    # tolerant fallback: strip a trailing generic club token then retry
    tokens = key.split()
    generic = {"fc", "cf", "afc", "ud", "ca", "rc", "rcd", "cd", "sad", "club",
               "de", "sd", "cp"}
    stripped = [t for t in tokens if t not in generic]
    if stripped:
        cand = " ".join(stripped)
        for alias_key, code in idx.items():
            ak = " ".join(t for t in alias_key.split() if t not in generic)
            if ak == cand:
                return code
    return None


def resolve_club_loose(league_id: str, raw_name: str) -> str:
    """Like ``resolve_club`` but never fails: unknown historical clubs (teams that
    have since been relegated out of the league) get a stable synthetic code so
    they still contribute to Elo history and model training. Synthetic codes are
    prefixed ``~`` and are filtered out of the published current-season data."""
    code = resolve_club(league_id, raw_name)
    if code:
        return code
    return "~" + normalize_name(raw_name).replace(" ", "-")


def club(league_id: str, code: str) -> Club:
    return _CLUB_BY_CODE[league_id][code]


def league_clubs(league_id: str) -> list[Club]:
    return list(LEAGUES[league_id].clubs)


# --------------------------------------------------------------------------- #
# Output paths (namespaced by league/season)
# --------------------------------------------------------------------------- #
def combo_slug(league_id: str, season_id: str) -> str:
    return f"{league_id}/{season_id}"


def public_dir(league_id: str, season_id: str) -> str:
    d = os.path.join(PUBLIC_DATA_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return d


def cached_dir(league_id: str, season_id: str) -> str:
    d = os.path.join(CACHED_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return d


def raw_path(league_id: str, season_id: str, name: str) -> str:
    d = os.path.join(RAW_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def processed_path(league_id: str, season_id: str, name: str) -> str:
    d = os.path.join(PROCESSED_DIR, league_id, season_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)
