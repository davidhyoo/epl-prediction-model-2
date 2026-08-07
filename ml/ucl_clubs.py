"""
ucl_clubs.py  —  UEFA Champions League club registry
=====================================================
The 54 clubs that contest the two seasons the dashboard ships (2024-25 and
2025-26 — 36 clubs each, with overlap). Kept in a separate module so
``leagues.py`` stays readable; imported from there into the league registry.

Each entry mirrors the domestic ``Club`` dataclass:

    Club(code, name, short, primary, secondary, wiki, aliases)

  * ``code``    — a stable 3-letter code, unique *within* the UCL field (codes are
                  namespaced per league, so they may repeat a domestic club's code).
  * ``name``    — clean display name.
  * ``wiki``    — the English-Wikipedia article title used by ``club_fetch_squads``
                  to pull the real first-team squad + free-licensed headshots.
  * ``aliases`` — every spelling the club appears under across openfootball's
                  Champions-League files (current *and* older seasons) so the
                  name-alias resolver in ``leagues.py`` collapses them onto one
                  club. The **first** alias is the exact current openfootball
                  spelling (post country-code strip).

Colours are the clubs' brand colours (used only for the initials-badge fallback
when a crest can't load — crests themselves are hot-linked, never committed).
All data sources are free / openly licensed; see the README "Data sources".
"""
from __future__ import annotations

# Imported lazily by leagues.py to build the UCL League. Declared here as raw
# tuples (not Club instances) so this module has no import of leagues.py — that
# would be circular. leagues.py maps each tuple through its Club dataclass.
#
# tuple layout: (code, name, short, primary, secondary, wiki, (aliases...))
UCL_CLUB_ROWS: list[tuple] = [
    # ---- England ---------------------------------------------------------- #
    ("ARS", "Arsenal", "Arsenal", "#EF0107", "#023474", "Arsenal F.C.",
     ("Arsenal FC", "Arsenal")),
    ("AVL", "Aston Villa", "Aston Villa", "#95BFE5", "#670E36", "Aston Villa F.C.",
     ("Aston Villa FC", "Aston Villa")),
    ("CHE", "Chelsea", "Chelsea", "#034694", "#DBA111", "Chelsea F.C.",
     ("Chelsea FC", "Chelsea")),
    ("LIV", "Liverpool", "Liverpool", "#C8102E", "#00B2A9", "Liverpool F.C.",
     ("Liverpool FC", "Liverpool")),
    ("MCI", "Manchester City", "Man City", "#6CABDD", "#1C2C5B", "Manchester City F.C.",
     ("Manchester City FC", "Manchester City", "Man City")),
    ("NEW", "Newcastle United", "Newcastle", "#241F20", "#FFFFFF", "Newcastle United F.C.",
     ("Newcastle United FC", "Newcastle United", "Newcastle")),
    ("TOT", "Tottenham Hotspur", "Tottenham", "#132257", "#FFFFFF", "Tottenham Hotspur F.C.",
     ("Tottenham Hotspur FC", "Tottenham Hotspur", "Tottenham", "Spurs")),
    # ---- Spain ------------------------------------------------------------ #
    ("ATH", "Athletic Club", "Athletic", "#EE2523", "#FFFFFF", "Athletic Bilbao",
     ("Athletic Club", "Athletic Bilbao", "Ath Bilbao")),
    ("ATM", "Atlético Madrid", "Atlético", "#CB3524", "#262E62", "Atlético Madrid",
     ("Club Atlético de Madrid", "Atlético Madrid", "Atletico Madrid", "Atlético de Madrid")),
    ("BAR", "Barcelona", "Barcelona", "#A50044", "#004D98", "FC Barcelona",
     ("FC Barcelona", "Barcelona")),
    ("GIR", "Girona", "Girona", "#D5122E", "#FFFFFF", "Girona FC",
     ("Girona FC", "Girona")),
    ("RMA", "Real Madrid", "Real Madrid", "#00529F", "#FEBE10", "Real Madrid CF",
     ("Real Madrid CF", "Real Madrid")),
    ("VIL", "Villarreal", "Villarreal", "#FFD100", "#005187", "Villarreal CF",
     ("Villarreal CF", "Villarreal")),
    # ---- Germany ---------------------------------------------------------- #
    ("B04", "Bayer Leverkusen", "Leverkusen", "#E32219", "#000000", "Bayer 04 Leverkusen",
     ("Bayer 04 Leverkusen", "Bayer Leverkusen", "Leverkusen")),
    ("BVB", "Borussia Dortmund", "Dortmund", "#FDE100", "#000000", "Borussia Dortmund",
     ("Borussia Dortmund", "Dortmund")),
    ("SGE", "Eintracht Frankfurt", "Frankfurt", "#E1000F", "#000000", "Eintracht Frankfurt",
     ("Eintracht Frankfurt", "Frankfurt")),
    ("FCB", "Bayern München", "Bayern", "#DC052D", "#0066B2", "FC Bayern Munich",
     ("FC Bayern München", "Bayern München", "Bayern Munich", "Bayern Munchen")),
    ("RBL", "RB Leipzig", "Leipzig", "#DD0741", "#001F47", "RB Leipzig",
     ("RB Leipzig", "RasenBallsport Leipzig", "Leipzig")),
    ("VFB", "VfB Stuttgart", "Stuttgart", "#E32219", "#FFFFFF", "VfB Stuttgart",
     ("VfB Stuttgart", "Stuttgart")),
    # ---- France ----------------------------------------------------------- #
    ("LIL", "Lille", "Lille", "#E01E13", "#0B1E3C", "Lille OSC",
     ("Lille OSC", "Lille", "LOSC Lille")),
    ("OMA", "Olympique de Marseille", "Marseille", "#2FAEE0", "#FFFFFF", "Olympique de Marseille",
     ("Olympique de Marseille", "Marseille", "Olympique Marseille")),
    ("PSG", "Paris Saint-Germain", "PSG", "#004170", "#DA291C", "Paris Saint-Germain F.C.",
     ("Paris Saint-Germain FC", "Paris Saint-Germain", "Paris Saint Germain", "Paris SG")),
    ("SB2", "Stade Brestois 29", "Brest", "#E30613", "#FFFFFF", "Stade Brestois 29",
     ("Stade Brestois 29", "Brest", "Stade Brestois")),
    ("ASM", "AS Monaco", "Monaco", "#E51B22", "#FFFFFF", "AS Monaco FC",
     ("AS Monaco FC", "AS Monaco", "Monaco")),
    # ---- Italy ------------------------------------------------------------ #
    ("ACM", "AC Milan", "Milan", "#FB090B", "#000000", "AC Milan",
     ("AC Milan", "Milan")),
    ("ATA", "Atalanta", "Atalanta", "#1D82C6", "#000000", "Atalanta BC",
     ("Atalanta BC", "Atalanta")),
    ("BOL", "Bologna", "Bologna", "#A21C27", "#1A2F48", "Bologna F.C. 1909",
     ("Bologna FC 1909", "Bologna")),
    ("INT", "Inter Milan", "Inter", "#1E71B8", "#000000", "Inter Milan",
     ("FC Internazionale Milano", "Inter Milan", "Internazionale", "Inter")),
    ("JUV", "Juventus", "Juventus", "#000000", "#FFFFFF", "Juventus FC",
     ("Juventus FC", "Juventus", "Juventus Turin")),
    ("NAP", "Napoli", "Napoli", "#0080C8", "#FFFFFF", "S.S.C. Napoli",
     ("SSC Napoli", "Napoli")),
    # ---- Portugal --------------------------------------------------------- #
    ("BEN", "Benfica", "Benfica", "#E00034", "#FFFFFF", "S.L. Benfica",
     ("Sport Lisboa e Benfica", "Benfica", "Benfica Lisboa", "SL Benfica")),
    ("SCP", "Sporting CP", "Sporting", "#008057", "#FFFFFF", "Sporting CP",
     ("Sporting Clube de Portugal", "Sporting CP", "Sporting Lisbon", "Sporting")),
    # ---- Netherlands ------------------------------------------------------ #
    ("AJA", "Ajax", "Ajax", "#D2122E", "#FFFFFF", "AFC Ajax",
     ("AFC Ajax", "Ajax", "Ajax Amsterdam")),
    ("PSV", "PSV Eindhoven", "PSV", "#ED1C24", "#FFFFFF", "PSV Eindhoven",
     ("PSV", "PSV Eindhoven")),
    ("FEY", "Feyenoord", "Feyenoord", "#E30613", "#000000", "Feyenoord",
     ("Feyenoord Rotterdam", "Feyenoord")),
    # ---- Belgium ---------------------------------------------------------- #
    ("CLB", "Club Brugge", "Club Brugge", "#0A50A1", "#000000", "Club Brugge KV",
     ("Club Brugge KV", "Club Brugge", "Club Bruges")),
    ("USG", "Union Saint-Gilloise", "Union SG", "#FFDD00", "#004B9B", "Royale Union Saint-Gilloise",
     ("Royale Union Saint-Gilloise", "Union Saint-Gilloise", "Union SG")),
    # ---- Rest of Europe --------------------------------------------------- #
    ("GAL", "Galatasaray", "Galatasaray", "#A90432", "#FBB33F", "Galatasaray S.K. (football)",
     ("Galatasaray SK", "Galatasaray")),
    ("CTC", "Celtic", "Celtic", "#018749", "#FFFFFF", "Celtic F.C.",
     ("Celtic FC", "Celtic", "Celtic Glasgow")),
    ("FCK", "FC Copenhagen", "Copenhagen", "#002E5F", "#FFFFFF", "F.C. Copenhagen",
     ("FC København", "FC Copenhagen", "Copenhagen", "Kobenhavn")),
    ("BOD", "Bodø/Glimt", "Bodø/Glimt", "#FFD100", "#000000", "FK Bodø/Glimt",
     ("FK Bodø/Glimt", "Bodo/Glimt", "Bodø/Glimt")),
    ("SHK", "Shakhtar Donetsk", "Shakhtar", "#F68B1F", "#000000", "FC Shakhtar Donetsk",
     ("FK Shakhtar Donetsk", "Shakhtar Donetsk", "Shakhtar")),
    ("RST", "Red Star Belgrade", "Red Star", "#D6001C", "#FFFFFF", "Red Star Belgrade",
     ("FK Crvena Zvezda", "Crvena Zvezda", "Red Star Belgrade", "Red Star")),
    ("YBO", "Young Boys", "Young Boys", "#FFD100", "#000000", "BSC Young Boys",
     ("BSC Young Boys", "Young Boys")),
    ("SLO", "Slovan Bratislava", "Slovan", "#004B9B", "#FFFFFF", "ŠK Slovan Bratislava",
     ("ŠK Slovan Bratislava", "Slovan Bratislava", "Slovan")),
    ("STU", "Sturm Graz", "Sturm Graz", "#000000", "#FFFFFF", "SK Sturm Graz",
     ("SK Sturm Graz", "Sturm Graz")),
    ("RBS", "Red Bull Salzburg", "Salzburg", "#D3001C", "#FFFFFF", "FC Red Bull Salzburg",
     ("FC Red Bull Salzburg", "Red Bull Salzburg", "Salzburg")),
    ("DIN", "Dinamo Zagreb", "Dinamo Zagreb", "#0A50A1", "#FFFFFF", "GNK Dinamo Zagreb",
     ("GNK Dinamo Zagreb", "Dinamo Zagreb")),
    ("SPA", "Sparta Prague", "Sparta", "#8B1A2B", "#FFD200", "AC Sparta Prague",
     ("AC Sparta Praha", "Sparta Prague", "Sparta Praha")),
    ("SLA", "Slavia Prague", "Slavia", "#C8102E", "#FFFFFF", "SK Slavia Prague",
     ("SK Slavia Praha", "Slavia Prague", "Slavia Praha")),
    ("OLY", "Olympiacos", "Olympiacos", "#E30613", "#FFFFFF", "Olympiacos F.C.",
     ("PAE Olympiakos SFP", "Olympiacos", "Olympiakos")),
    ("PAF", "Pafos", "Pafos", "#003DA5", "#FFFFFF", "Pafos FC",
     ("Paphos FC", "Pafos FC", "Pafos", "Paphos")),
    ("KAI", "Kairat Almaty", "Kairat", "#FFD100", "#000000", "FC Kairat",
     ("FK Kairat", "Kairat Almaty", "Kairat")),
    ("QAR", "Qarabağ", "Qarabağ", "#000000", "#FFFFFF", "Qarabağ FK",
     ("Qarabağ Ağdam FK", "Qarabag FK", "Qarabağ", "Qarabag")),
]
