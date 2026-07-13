"""
fetch_players.py  —  real national-team squads + free headshots (no paid APIs)
==============================================================================
Downloads the **real, current** squad for each of the 48 qualified nations from
the corresponding Wikipedia "national football team" article (the maintained
``{{nat fs ... player}}`` squad templates) and, where a **freely-licensed**
portrait exists on Wikimedia Commons, a small headshot thumbnail.

Everything is cached so the rest of the pipeline stays offline & reproducible:

  * ``data/source/squads_wikipedia.json``  — parsed squads per nation (the
    source of truth ``ml/sources.load_squads`` reads)
  * ``public/headshots/<CODE>-<NN>.jpg``    — headshot thumbnails (committed so
    the app shows them out of the box)
  * ``data/source/headshot_credits.json``   — per-photo attribution (author +
    licence + Commons file page), for the credits shown in the UI

Data & licensing
----------------
* Squad **facts** (name, shirt no., position, DOB, caps, goals, club) come from
  English Wikipedia (text is CC BY-SA 4.0; facts themselves aren't copyrightable
  — Wikipedia is credited in the README / Methodology anyway).
* Headshots are only kept when the Commons file carries a **free licence**
  (public domain / CC0 / CC BY / CC BY-SA). Non-free or missing images fall back
  to the app's clean initials avatar. Each kept photo records its author, licence
  and source page so it can be attributed (CC BY-SA requires attribution).

No API keys, no paid services — plain HTTPS to the public MediaWiki APIs with a
descriptive User-Agent, and a polite delay between requests. Runs are idempotent:
existing headshots are not re-downloaded unless ``--force-images`` is given, and
a partial/failed fetch never discards a good cached squad.

    python ml/fetch_players.py                 # refresh squads + headshots
    python ml/fetch_players.py --no-images     # squads only (skip downloads)
    python ml/fetch_players.py --force-images  # re-download every headshot
    python ml/fetch_players.py --only ARG,ESP  # a subset of nations
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA_DIR, load_teams  # noqa: E402

SOURCE_DIR = os.path.join(DATA_DIR, "source")
PUBLIC_DIR = os.path.join(os.path.dirname(DATA_DIR), "public")
HEADSHOT_DIR = os.path.join(PUBLIC_DIR, "headshots")
SQUADS_CACHE = os.path.join(SOURCE_DIR, "squads_wikipedia.json")
CREDITS_CACHE = os.path.join(SOURCE_DIR, "headshot_credits.json")

UA = ("worldcup-2026-dashboard/1.0 (portfolio project; "
      "https://github.com/davidhyoo/epl-prediction-model-2)")
TIMEOUT = 45
POLITE = 0.2  # seconds between network calls (throttling-safe)

# The reference date used to turn a date-of-birth into an age (the opener).
AS_OF = (2026, 6, 11)

# --------------------------------------------------------------------------- #
# 48 nation code -> English Wikipedia article title
# --------------------------------------------------------------------------- #
WIKI_TITLE = {
    "MEX": "Mexico national football team",
    "RSA": "South Africa national soccer team",
    "KOR": "South Korea national football team",
    "CZE": "Czech Republic national football team",
    "CAN": "Canada men's national soccer team",
    "BIH": "Bosnia and Herzegovina national football team",
    "QAT": "Qatar national football team",
    "SUI": "Switzerland national football team",
    "BRA": "Brazil national football team",
    "MAR": "Morocco national football team",
    "HAI": "Haiti national football team",
    "SCO": "Scotland national football team",
    "USA": "United States men's national soccer team",
    "PAR": "Paraguay national football team",
    "AUS": "Australia men's national soccer team",
    "TUR": "Turkey national football team",
    "GER": "Germany national football team",
    "CUW": "Curaçao national football team",
    "CIV": "Ivory Coast national football team",
    "ECU": "Ecuador national football team",
    "NED": "Netherlands national football team",
    "JPN": "Japan national football team",
    "SWE": "Sweden men's national football team",
    "TUN": "Tunisia national football team",
    "BEL": "Belgium national football team",
    "EGY": "Egypt national football team",
    "IRN": "Iran national football team",
    "NZL": "New Zealand men's national football team",
    "ESP": "Spain national football team",
    "CPV": "Cape Verde national football team",
    "SAU": "Saudi Arabia national football team",
    "URU": "Uruguay national football team",
    "FRA": "France national football team",
    "SEN": "Senegal national football team",
    "IRQ": "Iraq national football team",
    "NOR": "Norway national football team",
    "ARG": "Argentina national football team",
    "ALG": "Algeria national football team",
    "AUT": "Austria national football team",
    "JOR": "Jordan national football team",
    "POR": "Portugal national football team",
    "COD": "DR Congo national football team",
    "UZB": "Uzbekistan national football team",
    "COL": "Colombia national football team",
    "ENG": "England national football team",
    "CRO": "Croatia national football team",
    "GHA": "Ghana national football team",
    "PAN": "Panama national football team",
}

# clubnat (FIFA-ish 3-letter) -> country name, for the player's club country.
CLUBNAT = {
    "ENG": "England", "ESP": "Spain", "ITA": "Italy", "GER": "Germany",
    "FRA": "France", "POR": "Portugal", "NED": "Netherlands", "BEL": "Belgium",
    "TUR": "Turkey", "SCO": "Scotland", "USA": "United States", "SAU": "Saudi Arabia",
    "MEX": "Mexico", "BRA": "Brazil", "ARG": "Argentina", "GRE": "Greece",
    "RUS": "Russia", "UKR": "Ukraine", "SUI": "Switzerland", "AUT": "Austria",
    "CRO": "Croatia", "SRB": "Serbia", "JPN": "Japan", "KOR": "South Korea",
    "QAT": "Qatar", "UAE": "United Arab Emirates", "CHN": "China", "COL": "Colombia",
    "DEN": "Denmark", "NOR": "Norway", "SWE": "Sweden", "POL": "Poland",
    "CZE": "Czech Republic", "EGY": "Egypt", "MAR": "Morocco", "RSA": "South Africa",
    "AUS": "Australia", "CAN": "Canada", "IRN": "Iran", "IRQ": "Iraq",
    "URU": "Uruguay", "PAR": "Paraguay", "ECU": "Ecuador", "CHI": "Chile",
    "CYP": "Cyprus", "ISR": "Israel", "HUN": "Hungary", "ROU": "Romania",
    "BUL": "Bulgaria", "SVK": "Slovakia", "SVN": "Slovenia", "IND": "India",
}

POS_MAP = {"GK": "GK", "DF": "DEF", "MF": "MID", "FW": "FWD"}
POS_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
POS_WORD = {"GK": "Goalkeeper", "DEF": "Defender", "MID": "Midfielder", "FWD": "Forward"}

PLAYER_START_RE = re.compile(r"\{\{\s*nat fs (g |r )?player\b", re.IGNORECASE)
BDAY_RE = re.compile(r"(?:bda|birth date)[^}]*?(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})",
                     re.IGNORECASE)
FREE_LICENCE_RE = re.compile(r"^(cc0|cc-by|public domain|pdm|no restrictions)", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# HTTP helpers (stdlib only)
# --------------------------------------------------------------------------- #
def _get(url: str, tries: int = 4) -> bytes:
    """GET with a polite pause + exponential backoff on throttling/errors.

    Wikimedia rate-limits bursts, so every call waits ``POLITE`` seconds first
    and retries on 429/503 (honouring ``Retry-After``) or transient network
    errors before giving up.
    """
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


def _api(host: str, params: dict) -> dict:
    params = {**params, "format": "json", "maxlag": "5"}
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    return json.loads(_get(url).decode("utf-8", "replace"))


# --------------------------------------------------------------------------- #
# Wikitext parsing
# --------------------------------------------------------------------------- #
def _split_params(body: str) -> dict:
    """Split a template body into ``key -> value`` respecting [[..]] / {{..}}."""
    params, depth, buf = {}, 0, ""
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


def _delink(s: str) -> tuple[str, str]:
    """Return (display, target) for a possible ``[[target|display]]`` wikilink."""
    s = s.strip()
    m = re.search(r"\[\[\s*([^\]|]+?)\s*(?:\|\s*([^\]]+?)\s*)?\]\]", s)
    if m:
        target = m.group(1).strip()
        display = (m.group(2) or m.group(1)).strip()
        return display, target
    return re.sub(r"\{\{.*?\}\}", "", s).strip(), s


def _top_segments(body: str) -> list[str]:
    """Split on top-level ``|`` respecting ``[[..]]`` / ``{{..}}`` nesting."""
    segs, depth, buf = [], 0, ""
    for ch in body:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth = max(0, depth - 1)
        if ch == "|" and depth == 0:
            segs.append(buf)
            buf = ""
        else:
            buf += ch
    segs.append(buf)
    return segs


def _player_name(raw: str) -> tuple[str, str]:
    """Resolve a squad-row ``name=`` into (display, article-title).

    Handles the two common encodings: a plain ``[[wikilink]]`` (Argentina, most
    nations) **and** ``{{sortname|First|Last|dab=...}}`` (USA/Canada and other
    US-soccer articles), plus a plain-text fallback.
    """
    raw = raw.strip()
    m = re.search(r"\[\[\s*([^\]|]+?)\s*(?:\|\s*([^\]]+?)\s*)?\]\]", raw)
    if m:
        return (m.group(2) or m.group(1)).strip(), m.group(1).strip()
    m = re.search(r"\{\{\s*sortname\s*\|(.*)\}\}\s*$", raw, re.IGNORECASE | re.DOTALL)
    if m:
        segs = _top_segments(m.group(1))
        pos = [s.strip() for s in segs if "=" not in s]
        named = {k.strip().lower(): v.strip()
                 for s in segs if "=" in s for k, v in [s.split("=", 1)]}
        display = " ".join(x for x in pos[:2] if x).strip()
        if not display:
            return "", ""
        if named.get("nolink") not in (None, "", "0", "no"):
            target = display
        elif named.get("dab"):
            target = f"{display} ({named['dab']})"
        else:
            target = display
        return display, target
    txt = re.sub(r"\{\{.*?\}\}", "", raw).strip()
    return txt, txt


def _squad_segment(wikitext: str) -> str:
    """Isolate the current-squad table (heading -> first ``{{nat fs end}}``)."""
    heading = re.search(r"==+\s*(?:current squad|most recent squad|recent squad|"
                        r"current call[- ]?up)\s*==+", wikitext, re.IGNORECASE)
    start = heading.end() if heading else 0
    end = wikitext.find("{{nat fs end}}", start)
    if end == -1:
        end = wikitext.find("{{nat fs r end}}", start)
    if end == -1:
        end = start + 8000
    return wikitext[start:end + 20]


def _iter_player_templates(seg: str):
    """Yield (is_recent, body) for each ``{{nat fs [g|r ]player ...}}`` template.

    Brace-aware so it copes with **multi-line** templates and nested
    ``{{birth date and age|...}}`` sub-templates (some articles inline the whole
    row on one line, others wrap it across several).
    """
    for m in PLAYER_START_RE.finditer(seg):
        is_recent = bool(m.group(1) and m.group(1).strip().lower() == "r")
        depth, j = 0, m.start()
        while j < len(seg):
            two = seg[j:j + 2]
            if two == "{{":
                depth += 1
                j += 2
            elif two == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        yield is_recent, seg[m.start():j]


def parse_squad(wikitext: str) -> list[dict]:
    seg = _squad_segment(wikitext)
    out = []
    for is_recent, body in _iter_player_templates(seg):
        if is_recent:  # skip "recent call-ups"
            continue
        p = _split_params(body[2:-2])  # strip the outer {{ }}; name chunk has no "="
        raw_pos = (p.get("pos", "") or "").upper()[:2]
        pos = POS_MAP.get(raw_pos)
        if not pos:
            continue
        name_disp, name_title = _player_name(p.get("name", ""))
        if not name_disp:
            continue
        club_disp, _ = _delink(p.get("club", ""))
        bd = BDAY_RE.search(p.get("age", "") + p.get("dob", "") + p.get("birth_date", ""))
        dob = f"{bd.group(1)}-{int(bd.group(2)):02d}-{int(bd.group(3)):02d}" if bd else None

        def _int(key):
            mm = re.search(r"-?\d+", p.get(key, "") or "")
            return int(mm.group()) if mm else None

        out.append({
            "no": _int("no"), "pos": pos, "name": name_disp, "wiki": name_title,
            "dob": dob, "caps": _int("caps"), "intlGoals": _int("goals"),
            "club": club_disp or None, "clubnat": (p.get("clubnat", "") or "").upper() or None,
        })
    # de-duplicate by name (some tables repeat), keep first occurrence
    seen, uniq = set(), []
    for pl in out:
        if pl["name"] in seen:
            continue
        seen.add(pl["name"])
        uniq.append(pl)
    return uniq


def _age(dob: str | None) -> int | None:
    if not dob:
        return None
    y, mth, d = (int(x) for x in dob.split("-"))
    ay, am, ad = AS_OF
    return ay - y - ((am, ad) < (mth, d))


def assign_ids(code: str, players: list[dict]) -> list[dict]:
    players.sort(key=lambda p: (POS_ORDER[p["pos"]], p["no"] if p["no"] else 99))
    # captain heuristic: most-capped outfield/keeper
    cap_idx = max(range(len(players)), key=lambda i: players[i]["caps"] or -1, default=-1)
    for i, p in enumerate(players):
        p["id"] = f"{code}-{i + 1:02d}"
        p["age"] = _age(p["dob"])
        p["isCaptain"] = (i == cap_idx)
    return players


# --------------------------------------------------------------------------- #
# Headshots (Wikipedia page image -> Commons free-licence check -> download)
# --------------------------------------------------------------------------- #
def fetch_page_images(titles: list[str]) -> dict[str, dict]:
    """Requested title -> {thumb, file} for articles that have a lead image.

    Wikipedia may *normalize* (e.g. spacing/underscores) **and** *redirect* a
    requested title to the real article, so the returned page title rarely equals
    what we asked for.  We resolve requested -> normalized -> redirect target and
    key the result by the **original** requested title so callers can look it up
    with the wikilink they parsed out of the squad table.
    """
    out: dict[str, dict] = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        data = _api("en.wikipedia.org", {
            "action": "query", "prop": "pageimages", "piprop": "thumbnail|name",
            "pithumbsize": "240", "titles": "|".join(chunk), "redirects": "1"})
        q = data.get("query", {})
        norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
        redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
        by_final: dict[str, dict] = {}
        for pg in q.get("pages", {}).values():
            if "thumbnail" in pg and "pageimage" in pg:
                by_final[pg["title"]] = {"thumb": pg["thumbnail"]["source"], "file": pg["pageimage"]}
        for req in chunk:
            step = norm.get(req, req)
            final = redir.get(step, step)
            if final in by_final:
                out[req] = by_final[final]
    return out


def commons_licence(files: list[str]) -> dict[str, dict]:
    """File name -> {author, licence, licenceUrl, source} for free Commons files."""
    out: dict[str, dict] = {}
    for i in range(0, len(files), 40):
        chunk = ["File:" + f for f in files[i:i + 40]]
        data = _api("commons.wikimedia.org", {
            "action": "query", "prop": "imageinfo",
            "iiprop": "extmetadata|url", "titles": "|".join(chunk)})
        for pg in data.get("query", {}).get("pages", {}).values():
            if "missing" in pg or "imageinfo" not in pg:
                continue
            info = pg["imageinfo"][0]
            ex = info.get("extmetadata", {})
            lic = ex.get("LicenseShortName", {}).get("value", "")
            code = ex.get("License", {}).get("value", "")
            free = FREE_LICENCE_RE.match(code) or FREE_LICENCE_RE.match(lic)
            if not free:
                continue
            author = re.sub(r"<[^>]+>", "", ex.get("Artist", {}).get("value", "")).strip()
            author = re.sub(r"\s+", " ", author)[:120] or "Wikimedia Commons"
            name = pg["title"].split(":", 1)[-1].replace("_", " ").strip()
            out[name] = {
                "author": author, "licence": lic or code,
                "licenceUrl": ex.get("LicenseUrl", {}).get("value", ""),
                "source": info.get("descriptionurl",
                                   "https://commons.wikimedia.org/wiki/" + pg["title"].replace(" ", "_")),
            }
    return out


def download(url: str, dest: str) -> bool:
    try:
        data = _get(url)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    if len(data) < 800:  # too small to be a real photo
        return False
    tmp = dest + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return True


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def fetch_team(code: str, title: str) -> list[dict]:
    data = _api("en.wikipedia.org", {"action": "parse", "prop": "wikitext",
                                     "page": title, "redirects": "1"})
    if "parse" not in data:
        raise RuntimeError(f"no article for {title!r}")
    wt = data["parse"]["wikitext"]["*"]
    players = parse_squad(wt)
    if not players:
        raise RuntimeError(f"no squad parsed from {title!r}")
    return assign_ids(code, players)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fetch real squads + free headshots")
    ap.add_argument("--no-images", action="store_true", help="skip headshot downloads")
    ap.add_argument("--force-images", action="store_true", help="re-download existing headshots")
    ap.add_argument("--only", default="", help="comma-separated nation codes")
    args = ap.parse_args(argv)

    os.makedirs(SOURCE_DIR, exist_ok=True)
    os.makedirs(HEADSHOT_DIR, exist_ok=True)

    existing: dict = {}
    if os.path.exists(SQUADS_CACHE):
        with open(SQUADS_CACHE, encoding="utf-8") as fh:
            existing = json.load(fh).get("squads", {})
    credits: dict = {}
    if os.path.exists(CREDITS_CACHE):
        with open(CREDITS_CACHE, encoding="utf-8") as fh:
            credits = {c["id"]: c for c in json.load(fh)}

    teams = load_teams()
    only = {c.strip().upper() for c in args.only.split(",") if c.strip()}
    squads: dict = dict(existing)
    ok = imgs = 0

    for t in teams:
        if only and t.code not in only:
            continue
        title = WIKI_TITLE.get(t.code, f"{t.name} national football team")
        try:
            players = fetch_team(t.code, title)
        except Exception as exc:  # noqa: BLE001 - keep going, keep cached squad
            print(f"  ! {t.code} {title}: {exc} — keeping cache")
            continue

        # attach club country + clean fields
        for p in players:
            p["country"] = t.name
            p["countryCode"] = t.code
            p["iso2"] = t.iso2
            p["position"] = p.pop("pos")
            p["detailedPosition"] = POS_WORD[p["position"]]
            p["shirtNumber"] = p.pop("no") or 0
            p["clubCountry"] = CLUBNAT.get(p.get("clubnat") or "", p.get("clubnat") or "")
            p["headshot"] = None
            p["photoCredit"] = None

        # headshots (best-effort: a network hiccup must not lose the squad)
        if not args.no_images:
            try:
                wiki_titles = [p["wiki"] for p in players]
                pi = fetch_page_images(wiki_titles)
                need_lic = [pi[p["wiki"]]["file"] for p in players if p["wiki"] in pi]
                lic = commons_licence(sorted(set(need_lic)))
                for p in players:
                    info = pi.get(p["wiki"])
                    lic_key = info["file"].replace("_", " ").strip() if info else None
                    if not info or lic_key not in lic:
                        continue
                    rel = f"headshots/{p['id']}.jpg"
                    dest = os.path.join(PUBLIC_DIR, rel)
                    have = os.path.exists(dest)
                    if have and not args.force_images:
                        got = True
                    else:
                        got = download(info["thumb"], dest)
                    if got:
                        p["headshot"] = "/" + rel
                        meta = lic[lic_key]
                        p["photoCredit"] = {"author": meta["author"], "license": meta["licence"],
                                            "sourceUrl": meta["source"]}
                        credits[p["id"]] = {"id": p["id"], "name": p["name"], "country": t.name,
                                            "file": rel, **meta}
                        imgs += 1
            except Exception as exc:  # noqa: BLE001 - degrade to initials avatars
                print(f"    (headshots for {t.code} skipped: {exc})")

        squads[t.code] = players
        ok += 1
        withimg = sum(1 for p in players if p["headshot"])
        print(f"  {t.code} {title:44.44} {len(players):2d} players, {withimg:2d} headshots")

    if ok < 40 and existing and not only:
        print(f"[fetch_players] only {ok} nations fetched — keeping previous cache, not overwriting")
        return

    payload = {"source": "en.wikipedia.org (nat fs squad templates)",
               "asOf": "%04d-%02d-%02d" % AS_OF, "teams": len(squads),
               "players": sum(len(v) for v in squads.values()), "squads": squads}
    with open(SQUADS_CACHE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    cred_list = [credits[k] for k in sorted(credits)]
    with open(CREDITS_CACHE, "w", encoding="utf-8") as fh:
        json.dump(cred_list, fh, ensure_ascii=False, indent=1)

    print(f"[fetch_players] {ok} nations, {payload['players']} players, "
          f"{imgs} headshots this run ({len(cred_list)} credited) -> {SQUADS_CACHE}")


if __name__ == "__main__":
    main()
