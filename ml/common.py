"""
common.py
=========
Shared constants and helpers for the 2026 World Cup data/ML pipeline.

Data is built from REAL, openly-licensed (CC0) football datasets and cached
locally so the pipeline stays fully offline & reproducible:

  * martj42/international_results  — every men's international 1872→present
    (used for training history and for computing real Elo ratings).
  * openfootball/worldcup (2026--usa) — the real 2026 group draw, fixtures,
    results and knockout bracket.

See ml/sources.py for the parsers and the README "Data Sources" section for
licensing. Player-level squad data has no clean CC0 source, so squads/player
stats remain deterministically *generated* (documented in the README) and keyed
to the real 48-team field. Re-running `python ml/pipeline.py` from the cached
sources always yields identical data.
"""
from __future__ import annotations

import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ML_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(ML_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CACHED_DIR = os.path.join(DATA_DIR, "cached")
MODELS_DIR = os.path.join(ML_DIR, "models")
OUTPUTS_DIR = os.path.join(ML_DIR, "outputs")
PUBLIC_DATA_DIR = os.path.join(ROOT_DIR, "public", "data")

for _d in (RAW_DIR, PROCESSED_DIR, CACHED_DIR, MODELS_DIR, OUTPUTS_DIR, PUBLIC_DATA_DIR):
    os.makedirs(_d, exist_ok=True)

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
SEED = 2026


def rng(salt: str = "") -> np.random.Generator:
    """Return a deterministic numpy Generator, optionally namespaced by `salt`."""
    h = int(hashlib.sha256(f"{SEED}:{salt}".encode()).hexdigest(), 16) % (2**32)
    return np.random.default_rng(h)


# --------------------------------------------------------------------------- #
# Tournament calendar (real 2026 FIFA World Cup window)
# --------------------------------------------------------------------------- #
TOURNAMENT = "2026 FIFA World Cup"
HOST = "United States, Canada & Mexico"
GROUP_START = datetime(2026, 6, 11, tzinfo=timezone.utc)
# Any international match BEFORE the tournament opener is training history; the
# World Cup itself is never used to train (leakage-free). Match *status*
# (completed vs upcoming) is derived from whether a real result exists in the
# source data — NOT from a fixed cutoff — so the app tracks the live tournament.
HISTORY_END = GROUP_START
CUTOFF = GROUP_START  # retained for backwards-compatible imports

# Elo / goals model constants
HOME_ADV = 55.0          # Elo-equivalent host advantage
NEUTRAL_ADV = 0.0
LEAGUE_AVG_GOALS = 1.36
GOALS_GAMMA = 0.55       # sensitivity of expected goals to rating gap
ELO_K = 32.0             # Elo update factor for competitive matches

GROUPS = list("ABCDEFGHIJKL")  # 12 groups

# --------------------------------------------------------------------------- #
# The real 48-team field for the 2026 FIFA World Cup, with the OFFICIAL group
# draw (December 2025). Values: FIFA code, ISO2 (for flag-icons), display name,
# confederation, an approximate Elo *prior* (only a display fallback — the real
# rating shown in the app is computed from actual match history in features.py),
# primary/secondary national colours, host flag, and group letter.
#
# Team membership & groups are parsed-verified against the CC0 openfootball
# `2026--usa` dataset (see ml/sources.py). Do not hand-edit the groups here
# without updating that source of truth.
# --------------------------------------------------------------------------- #
TEAMS_RAW = [
    # code, iso2, name, confed, elo_prior, primary, secondary, host, group
    # Group A
    ("MEX", "mx", "Mexico", "CONCACAF", 1732, "#006847", "#CE1126", True, "A"),
    ("RSA", "za", "South Africa", "CAF", 1610, "#007A4D", "#FFB915", False, "A"),
    ("KOR", "kr", "South Korea", "AFC", 1637, "#C70039", "#041E42", False, "A"),
    ("CZE", "cz", "Czech Republic", "UEFA", 1670, "#11457E", "#D7141A", False, "A"),
    # Group B
    ("CAN", "ca", "Canada", "CONCACAF", 1690, "#FF0000", "#FFFFFF", True, "B"),
    ("BIH", "ba", "Bosnia & Herzegovina", "UEFA", 1600, "#002F6C", "#FFCE00", False, "B"),
    ("QAT", "qa", "Qatar", "AFC", 1560, "#8A1538", "#FFFFFF", False, "B"),
    ("SUI", "ch", "Switzerland", "UEFA", 1790, "#FF0000", "#FFFFFF", False, "B"),
    # Group C
    ("BRA", "br", "Brazil", "CONMEBOL", 2020, "#FEDF00", "#009B3A", False, "C"),
    ("MAR", "ma", "Morocco", "CAF", 1835, "#C1272D", "#006233", False, "C"),
    ("HAI", "ht", "Haiti", "CONCACAF", 1490, "#00209F", "#D21034", False, "C"),
    ("SCO", "gb-sct", "Scotland", "UEFA", 1700, "#0065BF", "#FFFFFF", False, "C"),
    # Group D
    ("USA", "us", "United States", "CONCACAF", 1770, "#0A3161", "#B31942", True, "D"),
    ("PAR", "py", "Paraguay", "CONMEBOL", 1680, "#DA121A", "#0038A8", False, "D"),
    ("AUS", "au", "Australia", "AFC", 1700, "#00843D", "#FFCD00", False, "D"),
    ("TUR", "tr", "Turkey", "UEFA", 1780, "#E30A17", "#FFFFFF", False, "D"),
    # Group E
    ("GER", "de", "Germany", "UEFA", 1930, "#000000", "#DD0000", False, "E"),
    ("CUW", "cw", "Curaçao", "CONCACAF", 1470, "#002B7F", "#F9E814", False, "E"),
    ("CIV", "ci", "Ivory Coast", "CAF", 1740, "#F77F00", "#009E60", False, "E"),
    ("ECU", "ec", "Ecuador", "CONMEBOL", 1780, "#FFDD00", "#034EA2", False, "E"),
    # Group F
    ("NED", "nl", "Netherlands", "UEFA", 1970, "#F36C21", "#21468B", False, "F"),
    ("JPN", "jp", "Japan", "AFC", 1810, "#BC002D", "#FFFFFF", False, "F"),
    ("SWE", "se", "Sweden", "UEFA", 1690, "#006AA7", "#FECC00", False, "F"),
    ("TUN", "tn", "Tunisia", "CAF", 1690, "#E70013", "#FFFFFF", False, "F"),
    # Group G
    ("BEL", "be", "Belgium", "UEFA", 1910, "#E30613", "#FDDA24", False, "G"),
    ("EGY", "eg", "Egypt", "CAF", 1690, "#CE1126", "#000000", False, "G"),
    ("IRN", "ir", "Iran", "AFC", 1780, "#239F40", "#DA0000", False, "G"),
    ("NZL", "nz", "New Zealand", "OFC", 1500, "#000000", "#FFFFFF", False, "G"),
    # Group H
    ("ESP", "es", "Spain", "UEFA", 2050, "#C60B1E", "#FFC400", False, "H"),
    ("CPV", "cv", "Cape Verde", "CAF", 1560, "#003893", "#CF2027", False, "H"),
    ("SAU", "sa", "Saudi Arabia", "AFC", 1620, "#006C35", "#FFFFFF", False, "H"),
    ("URU", "uy", "Uruguay", "CONMEBOL", 1890, "#5CBFEB", "#FFFFFF", False, "H"),
    # Group I
    ("FRA", "fr", "France", "UEFA", 2040, "#1E3A8A", "#EF4444", False, "I"),
    ("SEN", "sn", "Senegal", "CAF", 1800, "#00853F", "#FDEF42", False, "I"),
    ("IRQ", "iq", "Iraq", "AFC", 1560, "#CE1126", "#000000", False, "I"),
    ("NOR", "no", "Norway", "UEFA", 1820, "#BA0C2F", "#00205B", False, "I"),
    # Group J
    ("ARG", "ar", "Argentina", "CONMEBOL", 2100, "#6CACE4", "#FFFFFF", False, "J"),
    ("ALG", "dz", "Algeria", "CAF", 1750, "#006233", "#D21034", False, "J"),
    ("AUT", "at", "Austria", "UEFA", 1790, "#ED2939", "#FFFFFF", False, "J"),
    ("JOR", "jo", "Jordan", "AFC", 1540, "#007A3D", "#CE1126", False, "J"),
    # Group K
    ("POR", "pt", "Portugal", "UEFA", 1990, "#DA020E", "#006600", False, "K"),
    ("COD", "cd", "DR Congo", "CAF", 1650, "#007FFF", "#F7D618", False, "K"),
    ("UZB", "uz", "Uzbekistan", "AFC", 1620, "#1EB53A", "#0099B5", False, "K"),
    ("COL", "co", "Colombia", "CONMEBOL", 1850, "#FCD116", "#003893", False, "K"),
    # Group L
    ("ENG", "gb-eng", "England", "UEFA", 1970, "#FFFFFF", "#CE1124", False, "L"),
    ("CRO", "hr", "Croatia", "UEFA", 1850, "#FF0000", "#FFFFFF", False, "L"),
    ("GHA", "gh", "Ghana", "CAF", 1680, "#006B3F", "#FCD116", False, "L"),
    ("PAN", "pa", "Panama", "CONCACAF", 1570, "#DA121A", "#005293", False, "L"),
]

CONFEDERATIONS = ["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"]

# Host cities / stadiums (subset of the real 16 host venues) used to give
# fixtures a sense of place. Purely cosmetic.
VENUES = [
    ("MetLife Stadium", "New York/New Jersey"),
    ("SoFi Stadium", "Los Angeles"),
    ("AT&T Stadium", "Dallas"),
    ("Mercedes-Benz Stadium", "Atlanta"),
    ("NRG Stadium", "Houston"),
    ("Arrowhead Stadium", "Kansas City"),
    ("Lincoln Financial Field", "Philadelphia"),
    ("Levi's Stadium", "San Francisco Bay Area"),
    ("Lumen Field", "Seattle"),
    ("Hard Rock Stadium", "Miami"),
    ("Gillette Stadium", "Boston"),
    ("Lévi Stadium", "Santa Clara"),
    ("BMO Field", "Toronto"),
    ("BC Place", "Vancouver"),
    ("Estadio Azteca", "Mexico City"),
    ("Estadio Akron", "Guadalajara"),
    ("Estadio BBVA", "Monterrey"),
]

# --------------------------------------------------------------------------- #
# Name pools for GENERATED squads (documented as synthetic demo data).
# Mapped by a coarse "name culture" per country.
# --------------------------------------------------------------------------- #
NAME_CULTURE = {
    "ARG": "latam", "BRA": "brazil", "URU": "latam", "COL": "latam", "ECU": "latam",
    "PER": "latam", "PAR": "latam", "MEX": "latam", "CRC": "latam", "PAN": "latam",
    "ESP": "spanish", "POR": "portuguese", "FRA": "french", "BEL": "french",
    "ENG": "english", "USA": "english", "CAN": "english", "AUS": "english",
    "NZL": "english", "JAM": "english", "GHA": "english", "NGA": "english",
    "GER": "german", "AUT": "german", "SUI": "german", "NED": "dutch",
    "ITA": "italian", "CRO": "slavic", "SRB": "slavic", "UKR": "slavic",
    "POL": "slavic", "DEN": "nordic", "NOR": "nordic", "SEN": "french",
    "CIV": "french", "CMR": "french", "ALG": "arabic", "MAR": "arabic",
    "EGY": "arabic", "TUN": "arabic", "SAU": "arabic", "QAT": "arabic",
    "IRQ": "arabic", "IRN": "persian", "TUR": "turkish", "UZB": "turkish",
    "JPN": "japanese", "KOR": "korean",
}

FIRST_NAMES = {
    "latam": ["Mateo", "Santiago", "Lucas", "Diego", "Julian", "Nicolas", "Gonzalo",
              "Emiliano", "Facundo", "Alejandro", "Rodrigo", "Cristian", "Tomas",
              "Agustin", "Franco", "Lautaro", "Bruno", "Ivan", "Marcelo", "Sergio"],
    "brazil": ["Gabriel", "Lucas", "Matheus", "Rafael", "Bruno", "Vinicius", "Rodrygo",
               "Thiago", "Danilo", "Caio", "Joao", "Pedro", "Gustavo", "Andre",
               "Marquinhos", "Felipe", "Everton", "Wesley", "Douglas", "Igor"],
    "spanish": ["Sergio", "Pablo", "Alvaro", "Marco", "Dani", "Fabian", "Hugo", "Marcos",
                "Iker", "Aitor", "Nico", "Gavi", "Pedri", "Rodri", "Ferran", "Mikel",
                "Unai", "Bryan", "Javi", "Alex"],
    "portuguese": ["Joao", "Bruno", "Rafael", "Diogo", "Ruben", "Bernardo", "Goncalo",
                   "Nuno", "Vitinha", "Andre", "Tiago", "Rui", "Pedro", "Fabio",
                   "Renato", "Matheus", "Francisco", "Otavio", "Ricardo", "Nelson"],
    "french": ["Kylian", "Antoine", "Ousmane", "Aurelien", "Eduardo", "Ibrahima",
               "Randal", "Marcus", "Theo", "Lucas", "Jules", "Youssouf", "Moussa",
               "Boubacar", "Cheikh", "Sadio", "Nicolas", "Wilfried", "Serge", "Amadou"],
    "english": ["Harry", "Jude", "Phil", "Bukayo", "Marcus", "Jack", "Declan", "Cole",
                "Trent", "Mason", "Reece", "Kyle", "Levi", "Ollie", "James", "Ethan",
                "Tyler", "Jordan", "Jamal", "Connor"],
    "german": ["Jamal", "Florian", "Kai", "Leon", "Joshua", "Serge", "Niklas", "Thomas",
               "Timo", "Julian", "Robin", "Marc", "David", "Pascal", "Nico", "Felix",
               "Jonas", "Maximilian", "Lukas", "Benedikt"],
    "dutch": ["Cody", "Frenkie", "Memphis", "Virgil", "Denzel", "Nathan", "Xavi",
              "Tijjani", "Steven", "Wout", "Jurrien", "Matthijs", "Donyell", "Teun",
              "Ryan", "Bart", "Joey", "Sven", "Daan", "Lars"],
    "italian": ["Federico", "Nicolo", "Lorenzo", "Gianluca", "Sandro", "Davide",
                "Matteo", "Alessandro", "Giacomo", "Riccardo", "Bryan", "Manuel",
                "Andrea", "Marco", "Stefano", "Giovanni", "Simone", "Fabio", "Luca", "Mattia"],
    "slavic": ["Luka", "Marko", "Ivan", "Andrej", "Nikola", "Dusan", "Filip", "Mateo",
               "Josip", "Mario", "Petar", "Vlad", "Roman", "Oleksandr", "Mykhailo",
               "Robert", "Piotr", "Jakub", "Kamil", "Sergej"],
    "nordic": ["Erling", "Martin", "Alexander", "Christian", "Rasmus", "Pierre",
               "Mikkel", "Joakim", "Kristian", "Andreas", "Mathias", "Jonas", "Emil",
               "Victor", "Oscar", "Simon", "Anders", "Thomas", "Fredrik", "Magnus"],
    "arabic": ["Mohamed", "Youssef", "Achraf", "Hakim", "Riyad", "Ismael", "Bilal",
               "Amine", "Sofyan", "Karim", "Yassine", "Nayef", "Salem", "Omar",
               "Hassan", "Ali", "Ahmed", "Ayoub", "Walid", "Nabil"],
    "persian": ["Mehdi", "Alireza", "Sardar", "Karim", "Saman", "Ehsan", "Milad",
                "Omid", "Ramin", "Vahid", "Saeid", "Ali", "Hossein", "Reza", "Amir",
                "Morteza", "Kaveh", "Shoja", "Mohammad", "Majid"],
    "turkish": ["Arda", "Hakan", "Kerem", "Cengiz", "Yusuf", "Ferdi", "Ozan", "Baris",
                "Merih", "Kaan", "Orkun", "Salih", "Eldor", "Abbos", "Jaloliddin",
                "Otabek", "Ilya", "Bobur", "Sardor", "Azizbek"],
    "japanese": ["Takefusa", "Ritsu", "Kaoru", "Wataru", "Daichi", "Takumi", "Ao",
                 "Junya", "Hidemasa", "Ko", "Reo", "Ayase", "Kyogo", "Yukinari",
                 "Shogo", "Hiroki", "Genki", "Yuki", "Takehiro", "Daizen"],
    "korean": ["Heung-min", "Kang-in", "Min-jae", "Hwang", "Jae-sung", "Woo-young",
               "Ui-jo", "Chang-hoon", "Seung-ho", "Young-gwon", "Tae-hwan", "In-beom",
               "Gue-sung", "Jin-su", "Moon-hwan", "Hee-chan", "Sang-ho", "Ji-soo",
               "Do-yeong", "Seol"],
}

LAST_NAMES = {
    "latam": ["Martinez", "Gomez", "Rodriguez", "Fernandez", "Lopez", "Alvarez",
              "Suarez", "Romero", "Torres", "Diaz", "Herrera", "Castro", "Rojas",
              "Cabrera", "Molina", "Vargas", "Acosta", "Paredes", "Correa", "Nunez"],
    "brazil": ["Silva", "Santos", "Oliveira", "Souza", "Costa", "Pereira", "Lima",
               "Almeida", "Ferreira", "Ribeiro", "Carvalho", "Gomes", "Martins",
               "Rocha", "Barbosa", "Araujo", "Nascimento", "Cardoso", "Correia", "Teixeira"],
    "spanish": ["Garcia", "Fernandez", "Gonzalez", "Rodriguez", "Lopez", "Martin",
                "Sanchez", "Perez", "Gomez", "Ruiz", "Torres", "Navarro", "Molina",
                "Ortega", "Serrano", "Blanco", "Marquez", "Reyes", "Vega", "Iglesias"],
    "portuguese": ["Silva", "Santos", "Ferreira", "Pereira", "Costa", "Fernandes",
                   "Rodrigues", "Martins", "Sousa", "Carvalho", "Lopes", "Goncalves",
                   "Pinto", "Cardoso", "Nunes", "Ramos", "Neves", "Machado", "Antunes", "Dias"],
    "french": ["Diallo", "Traore", "Kone", "Ndiaye", "Camara", "Fofana", "Bakayoko",
               "Sarr", "Mendy", "Cisse", "Toure", "Keita", "Diakhate", "Dembele",
               "Coulibaly", "Doucoure", "Gueye", "Sylla", "Faye", "Niang"],
    "english": ["Smith", "Johnson", "Williams", "Brown", "Walker", "Wright", "Taylor",
                "Hughes", "Palmer", "Foden", "Bell", "Rice", "Hall", "Clarke",
                "Watkins", "Gordon", "Mount", "Stones", "Grealish", "Saka"],
    "german": ["Muller", "Schmidt", "Wagner", "Werner", "Kimmich", "Sane", "Havertz",
               "Gnabry", "Fischer", "Weber", "Meyer", "Klein", "Wolf", "Schulz",
               "Neuhaus", "Brandt", "Gunter", "Baumgartner", "Sabitzer", "Laimer"],
    "dutch": ["de Jong", "van Dijk", "Dumfries", "Gakpo", "Depay", "de Vrij", "Ake",
              "Weghorst", "Blind", "Timber", "Bergwijn", "Koopmeiners", "Malen",
              "Reijnders", "Frimpong", "Geertruida", "Simons", "Veerman", "Wieffer", "Brobbey"],
    "italian": ["Rossi", "Chiesa", "Barella", "Locatelli", "Tonali", "Bastoni",
                "Verratti", "Zaniolo", "Scamacca", "Raspadori", "Cristante", "Politano",
                "Frattesi", "Dimarco", "Buongiorno", "Retegui", "Ferrari", "Ricci",
                "Gatti", "Cambiaso"],
    "slavic": ["Modric", "Kovacic", "Perisic", "Brozovic", "Vlasic", "Sucic",
               "Milinkovic", "Mitrovic", "Tadic", "Vlahovic", "Zabarnyi", "Yarmolenko",
               "Zinchenko", "Mudryk", "Lewandowski", "Zielinski", "Szymanski",
               "Gvardiol", "Sosa", "Petkovic"],
    "nordic": ["Haaland", "Odegaard", "Sorloth", "Berge", "Nusa", "Ryerson",
               "Eriksen", "Hojlund", "Hojbjerg", "Andersen", "Dolberg", "Wind",
               "Skov", "Damsgaard", "Maehle", "Christensen", "Lindstrom", "Bah",
               "Norgaard", "Bruun"],
    "arabic": ["Hakimi", "Ziyech", "Amrabat", "Mazraoui", "En-Nesyri", "Ounahi",
               "Salah", "Mahrez", "Bennacer", "Aouar", "Slimani", "Msakni",
               "Al-Dawsari", "Al-Shehri", "Kanno", "Al-Owais", "Hassan", "Marmoush",
               "Zizou", "Bounou"],
    "persian": ["Taremi", "Azmoun", "Jahanbakhsh", "Ansarifard", "Hajsafi",
                "Mohammadi", "Ghoddos", "Cheshmi", "Noorollahi", "Karimi", "Torabi",
                "Amiri", "Rezaei", "Ezatolahi", "Gholizadeh", "Moharrami", "Pouraliganji",
                "Beiranvand", "Hosseini", "Sadeghi"],
    "turkish": ["Guler", "Calhanoglu", "Akturkoglu", "Under", "Yildiz", "Kadioglu",
                "Demiral", "Ayhan", "Yilmaz", "Kokcu", "Kabak", "Yokuslu", "Bardhi",
                "Shomurodov", "Masharipov", "Turgunboev", "Erkin", "Ozdoev", "Sergeev",
                "Fayzullaev"],
    "japanese": ["Kubo", "Doan", "Mitoma", "Endo", "Kamada", "Minamino", "Tanaka",
                 "Ito", "Tomiyasu", "Morita", "Hatate", "Nakamura", "Ueda", "Asano",
                 "Machida", "Sugawara", "Furuhashi", "Maeda", "Taniguchi", "Nagatomo"],
    "korean": ["Son", "Lee", "Kim", "Hwang", "Jung", "Cho", "Park", "Hong", "Kwon",
               "Seol", "Na", "Oh", "Baek", "Yoon", "Kang", "Bae", "Moon", "Cho",
               "Nam", "Koo"],
}

# Real club names (facts) used to give players a plausible club. Weighted so that
# higher-rated players tend to land at bigger clubs.
BIG_CLUBS = [
    ("Manchester City", "England"), ("Real Madrid", "Spain"), ("Barcelona", "Spain"),
    ("Bayern Munich", "Germany"), ("Paris Saint-Germain", "France"),
    ("Liverpool", "England"), ("Arsenal", "England"), ("Inter Milan", "Italy"),
    ("Manchester United", "England"), ("Chelsea", "England"), ("Juventus", "Italy"),
    ("Atletico Madrid", "Spain"), ("Borussia Dortmund", "Germany"), ("AC Milan", "Italy"),
    ("Tottenham Hotspur", "England"), ("Napoli", "Italy"), ("Bayer Leverkusen", "Germany"),
    ("Newcastle United", "England"), ("Aston Villa", "England"), ("RB Leipzig", "Germany"),
]
MID_CLUBS = [
    ("Ajax", "Netherlands"), ("Benfica", "Portugal"), ("Porto", "Portugal"),
    ("Sporting CP", "Portugal"), ("PSV Eindhoven", "Netherlands"), ("Feyenoord", "Netherlands"),
    ("Sevilla", "Spain"), ("Villarreal", "Spain"), ("Real Sociedad", "Spain"),
    ("AS Monaco", "France"), ("Lyon", "France"), ("Marseille", "France"),
    ("AS Roma", "Italy"), ("Lazio", "Italy"), ("Atalanta", "Italy"),
    ("West Ham United", "England"), ("Brighton", "England"), ("Fenerbahce", "Turkey"),
    ("Galatasaray", "Turkey"), ("Celtic", "Scotland"), ("Shakhtar Donetsk", "Ukraine"),
    ("Al-Hilal", "Saudi Arabia"), ("Al-Nassr", "Saudi Arabia"), ("Flamengo", "Brazil"),
    ("Palmeiras", "Brazil"), ("River Plate", "Argentina"), ("Boca Juniors", "Argentina"),
]
SMALL_CLUBS = [
    ("Urawa Red Diamonds", "Japan"), ("Ulsan HD", "South Korea"), ("Club America", "Mexico"),
    ("LAFC", "United States"), ("Inter Miami", "United States"), ("Toronto FC", "Canada"),
    ("Al-Ahly", "Egypt"), ("Esperance", "Tunisia"), ("Mamelodi Sundowns", "South Africa"),
    ("Wydad AC", "Morocco"), ("Persepolis", "Iran"), ("Melbourne City", "Australia"),
    ("Auckland City", "New Zealand"), ("Independiente", "Argentina"), ("Penarol", "Uruguay"),
    ("Atletico Nacional", "Colombia"), ("Barcelona SC", "Ecuador"), ("Alianza Lima", "Peru"),
    ("Legia Warsaw", "Poland"), ("Dinamo Zagreb", "Croatia"), ("Red Star Belgrade", "Serbia"),
    ("Kaizer Chiefs", "South Africa"), ("Raja CA", "Morocco"), ("Pachuca", "Mexico"),
]

POSITION_DETAIL = {
    "GK": ["Goalkeeper"],
    "DEF": ["Right-Back", "Left-Back", "Centre-Back", "Centre-Back", "Wing-Back"],
    "MID": ["Defensive Midfield", "Central Midfield", "Attacking Midfield",
            "Left Midfield", "Right Midfield"],
    "FWD": ["Centre-Forward", "Left Winger", "Right Winger", "Second Striker"],
}

# Human-readable labels for engineered features (used in explanations & the
# methodology page).
FEATURE_LABELS = {
    "elo_diff": "Elo / FIFA-style rating difference",
    "form_diff": "Recent form (points per game)",
    "gf_diff": "Attacking output (goals scored trend)",
    "ga_diff": "Defensive solidity (goals conceded trend)",
    "xg_diff": "Expected goals (xG) trend",
    "squad_diff": "Squad / player strength score",
    "rest_diff": "Rest & recovery advantage",
    "h2h_diff": "Head-to-head history",
    "host_adv": "Host-nation advantage",
    "stage_knockout": "Knockout-stage experience",
}

FEATURE_ORDER = [
    "elo_diff", "form_diff", "gf_diff", "ga_diff", "xg_diff",
    "squad_diff", "rest_diff", "h2h_diff", "host_adv", "stage_knockout",
]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def expected_goals(rating_a: float, rating_b: float) -> tuple[float, float]:
    """Expected goals for A and B given effective ratings (Elo scale)."""
    d = (rating_a - rating_b) / 400.0
    lam_a = LEAGUE_AVG_GOALS * float(np.exp(GOALS_GAMMA * d))
    lam_b = LEAGUE_AVG_GOALS * float(np.exp(-GOALS_GAMMA * d))
    return max(0.18, lam_a), max(0.18, lam_b)


def elo_win_prob(rating_a: float, rating_b: float) -> float:
    """Classic Elo expected score for A vs B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def write_json_pretty(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def publish(name: str, obj, pretty_copy: bool = True) -> None:
    """Write a dataset to BOTH data/cached (repo artifact) and public/data
    (served by Next.js). The cached copy is pretty-printed for readability."""
    write_json(os.path.join(PUBLIC_DATA_DIR, name), obj)
    if pretty_copy:
        write_json_pretty(os.path.join(CACHED_DIR, name), obj)
    else:
        write_json(os.path.join(CACHED_DIR, name), obj)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def scale_0_100(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 50.0
    return clamp(round((value - lo) / (hi - lo) * 100, 1), 1.0, 99.0)


@dataclass
class Team:
    code: str
    iso2: str
    name: str
    confederation: str
    elo0: float           # base / pre-tournament Elo
    primary: str
    secondary: str
    host: bool
    group: str = ""
    pot: int = 0
    fifa_rank: int = 0

    def ref(self) -> dict:
        return {
            "code": self.code,
            "iso2": self.iso2,
            "name": self.name,
            "colors": {"primary": self.primary, "secondary": self.secondary},
        }


def load_teams() -> list[Team]:
    teams = [
        Team(code=c, iso2=i, name=n, confederation=cf, elo0=float(e),
             primary=p, secondary=s, host=h, group=g)
        for (c, i, n, cf, e, p, s, h, g) in TEAMS_RAW
    ]
    # Placeholder FIFA rank by Elo prior (desc). The app displays a rank derived
    # from the REAL pre-tournament Elo computed in features.py / predict.py.
    for rank, t in enumerate(sorted(teams, key=lambda x: -x.elo0), start=1):
        t.fifa_rank = rank
    return teams
