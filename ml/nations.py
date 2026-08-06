"""
nations.py  —  IOC/FIFA 3-letter code → (ISO-3166 alpha-2, display name)
========================================================================
Wikipedia club squad templates tag each player's nationality with a 3-letter
code (``nat=ENG``/``BRA``/``ESP`` …). The UI shows a small flag next to the
player, so we translate those codes to an ISO-3166 alpha-2 code (for the flag
CDN / emoji) and a clean display name. Covers every nationality that appears in
current EPL + La Liga squads; unknown codes fall back gracefully to the raw code.
"""
from __future__ import annotations

# code: (iso2, display name)
NATIONS: dict[str, tuple[str, str]] = {
    "ENG": ("gb-eng", "England"), "SCO": ("gb-sct", "Scotland"),
    "WAL": ("gb-wls", "Wales"), "NIR": ("gb-nir", "Northern Ireland"),
    "IRL": ("ie", "Republic of Ireland"), "FRA": ("fr", "France"),
    "ESP": ("es", "Spain"), "POR": ("pt", "Portugal"), "GER": ("de", "Germany"),
    "ITA": ("it", "Italy"), "NED": ("nl", "Netherlands"), "BEL": ("be", "Belgium"),
    "BRA": ("br", "Brazil"), "ARG": ("ar", "Argentina"), "URU": ("uy", "Uruguay"),
    "COL": ("co", "Colombia"), "CHI": ("cl", "Chile"), "ECU": ("ec", "Ecuador"),
    "PAR": ("py", "Paraguay"), "PER": ("pe", "Peru"), "VEN": ("ve", "Venezuela"),
    "MEX": ("mx", "Mexico"), "USA": ("us", "United States"), "CAN": ("ca", "Canada"),
    "CRC": ("cr", "Costa Rica"), "JAM": ("jm", "Jamaica"), "HON": ("hn", "Honduras"),
    "CRO": ("hr", "Croatia"), "SRB": ("rs", "Serbia"), "SUI": ("ch", "Switzerland"),
    "AUT": ("at", "Austria"), "POL": ("pl", "Poland"), "CZE": ("cz", "Czechia"),
    "DEN": ("dk", "Denmark"), "SWE": ("se", "Sweden"), "NOR": ("no", "Norway"),
    "FIN": ("fi", "Finland"), "ISL": ("is", "Iceland"), "UKR": ("ua", "Ukraine"),
    "RUS": ("ru", "Russia"), "TUR": ("tr", "Türkiye"), "GRE": ("gr", "Greece"),
    "HUN": ("hu", "Hungary"), "ROU": ("ro", "Romania"), "SVK": ("sk", "Slovakia"),
    "SVN": ("si", "Slovenia"), "BUL": ("bg", "Bulgaria"), "ALB": ("al", "Albania"),
    "KOS": ("xk", "Kosovo"), "MKD": ("mk", "North Macedonia"), "BIH": ("ba", "Bosnia"),
    "MNE": ("me", "Montenegro"), "SÉN": ("sn", "Senegal"), "SEN": ("sn", "Senegal"),
    "CIV": ("ci", "Ivory Coast"), "GHA": ("gh", "Ghana"), "NGA": ("ng", "Nigeria"),
    "CMR": ("cm", "Cameroon"), "MLI": ("ml", "Mali"), "SEN": ("sn", "Senegal"),
    "MAR": ("ma", "Morocco"), "ALG": ("dz", "Algeria"), "TUN": ("tn", "Tunisia"),
    "EGY": ("eg", "Egypt"), "RSA": ("za", "South Africa"), "COD": ("cd", "DR Congo"),
    "GUI": ("gn", "Guinea"), "GAB": ("ga", "Gabon"), "BFA": ("bf", "Burkina Faso"),
    "ANG": ("ao", "Angola"), "CPV": ("cv", "Cape Verde"), "ZAM": ("zm", "Zambia"),
    "GAM": ("gm", "Gambia"), "TOG": ("tg", "Togo"), "BEN": ("bj", "Benin"),
    "JPN": ("jp", "Japan"), "KOR": ("kr", "South Korea"), "AUS": ("au", "Australia"),
    "IRN": ("ir", "Iran"), "KSA": ("sa", "Saudi Arabia"), "QAT": ("qa", "Qatar"),
    "UZB": ("uz", "Uzbekistan"), "CHN": ("cn", "China"), "ISR": ("il", "Israel"),
    "GEO": ("ge", "Georgia"), "ARM": ("am", "Armenia"), "NZL": ("nz", "New Zealand"),
    "PAN": ("pa", "Panama"), "CUW": ("cw", "Curaçao"), "TRI": ("tt", "Trinidad"),
    "DOM": ("do", "Dominican Republic"), "MTQ": ("mq", "Martinique"),
    "GLP": ("gp", "Guadeloupe"), "CGO": ("cg", "Congo"), "MOZ": ("mz", "Mozambique"),
    "LUX": ("lu", "Luxembourg"), "CYP": ("cy", "Cyprus"), "MLT": ("mt", "Malta"),
    "SUR": ("sr", "Suriname"), "GNB": ("gw", "Guinea-Bissau"), "SLE": ("sl", "Sierra Leone"),
    "COM": ("km", "Comoros"), "MAD": ("mg", "Madagascar"), "KEN": ("ke", "Kenya"),
    "BOL": ("bo", "Bolivia"), "GUA": ("gt", "Guatemala"), "SVG": ("vc", "St Vincent"),
}


def nation_info(code: str) -> tuple[str, str]:
    """Return (iso2, name); falls back to (lowercased code, code)."""
    code = (code or "").strip().upper()
    if code in NATIONS:
        return NATIONS[code]
    return (code.lower(), code or "—")
