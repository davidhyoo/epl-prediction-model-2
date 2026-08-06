"""
club_fetch_squads.py  —  real club squads + free-licensed headshots
===================================================================
Downloads the **real, current first-team squad** for each EPL + La Liga club
from its English-Wikipedia article (the maintained ``{{Fs player …}}`` squad
templates) and, where a **freely-licensed** portrait exists on Wikimedia
Commons, a small headshot thumbnail.

Everything is cached so the rest of the pipeline stays offline & reproducible:

  * ``data/source/{league}/squads_wikipedia.json`` — parsed squads per club
  * ``public/headshots/{league}/{CLUB}-{NN}.jpg``   — headshot thumbnails
  * ``data/source/{league}/headshot_credits.json``  — per-photo attribution

Data & licensing
----------------
* Squad **facts** (name, shirt number, position, nationality) come from English
  Wikipedia (text CC BY-SA 4.0; facts aren't copyrightable — Wikipedia credited
  in the README anyway).
* Headshots are only kept when the Commons file carries a **free licence**
  (public domain / CC0 / CC BY / CC BY-SA). Non-free/missing images fall back to
  the app's clean initials avatar. Each kept photo records author + licence +
  source page for attribution.

No API keys, no paid services — plain HTTPS to the public MediaWiki APIs with a
descriptive User-Agent and a polite delay. Runs are idempotent and a partial
failure never discards a good cached squad.

    python ml/club_fetch_squads.py                     # all clubs, both leagues
    python ml/club_fetch_squads.py --league epl        # one league
    python ml/club_fetch_squads.py --only ARS,LIV      # a subset of clubs
    python ml/club_fetch_squads.py --no-images         # squads only
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

from leagues import LEAGUES, PUBLIC_DATA_DIR, SOURCE_DIR, league_clubs
from nations import nation_info

ROOT = os.path.dirname(PUBLIC_DATA_DIR.rstrip(os.sep).rsplit(os.sep, 1)[0])
PUBLIC_DIR = os.path.dirname(PUBLIC_DATA_DIR)  # .../public
HEADSHOT_ROOT = os.path.join(PUBLIC_DIR, "headshots")

UA = ("epl-laliga-dashboard/1.0 (portfolio project; "
      "https://github.com/davidhyoo/epl-prediction-model-2)")
TIMEOUT = 45
POLITE = 0.2

POS_MAP = {"GK": "GK", "DF": "DEF", "MF": "MID", "FW": "FWD"}
POS_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
POS_WORD = {"GK": "Goalkeeper", "DEF": "Defender", "MID": "Midfielder", "FWD": "Forward"}

FS_PLAYER_RE = re.compile(r"\{\{\s*[Ff]s player\b")
FREE_LICENCE_RE = re.compile(r"^(cc0|cc-by|public domain|pdm|no restrictions)", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# HTTP helpers (stdlib only)
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


def _api(host: str, params: dict) -> dict:
    params = {**params, "format": "json", "maxlag": "5"}
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    return json.loads(_get(url).decode("utf-8", "replace"))


# --------------------------------------------------------------------------- #
# Wikitext parsing
# --------------------------------------------------------------------------- #
def _split_params(body: str) -> dict:
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


def _player_name(raw: str) -> tuple[str, str]:
    """(display, article-title) from a squad-row ``name=`` value."""
    raw = raw.strip()
    m = re.search(r"\[\[\s*([^\]|]+?)\s*(?:\|\s*([^\]]+?)\s*)?\]\]", raw)
    if m:
        return (m.group(2) or m.group(1)).strip(), m.group(1).strip()
    txt = re.sub(r"\{\{.*?\}\}", "", raw).strip()
    return txt, txt


def _iter_fs_players(seg: str):
    """Yield the full body of each ``{{Fs player …}}`` template (brace-aware)."""
    for m in FS_PLAYER_RE.finditer(seg):
        depth, j = 0, m.start()
        while j < len(seg):
            two = seg[j:j + 2]
            if two == "{{":
                depth += 1; j += 2
            elif two == "}}":
                depth -= 1; j += 2
                if depth == 0:
                    break
            else:
                j += 1
        yield seg[m.start():j]


def _squad_segment(wikitext: str) -> str:
    """Isolate the first-team squad table only.

    Locates the squad heading, then returns exactly the first
    ``{{Fs start}} … {{Fs end}}`` block after it (case-insensitive) so that
    "Out on loan" / "Under-21s and Academy" tables — which also use
    ``{{Fs player}}`` rows — are never swept in.
    """
    heading = re.search(
        r"==+\s*(?:first[- ]team squad|current squad|players|squad)\s*==+",
        wikitext, re.IGNORECASE)
    start = heading.end() if heading else 0
    fs_start = re.search(r"\{\{\s*fs start", wikitext[start:], re.IGNORECASE)
    if fs_start:
        start += fs_start.start()
    fs_end = re.search(r"\{\{\s*fs end\s*\}\}", wikitext[start:], re.IGNORECASE)
    end = start + fs_end.end() if fs_end else start + 12000
    return wikitext[start:end]


def parse_club_squad(wikitext: str) -> list[dict]:
    seg = _squad_segment(wikitext)
    out, seen = [], set()
    for body in _iter_fs_players(seg):
        p = _split_params(body[2:-2])
        raw_pos = (p.get("pos", "") or "").upper()[:2]
        pos = POS_MAP.get(raw_pos)
        if not pos:
            continue
        name_disp, name_title = _player_name(p.get("name", ""))
        if not name_disp or name_disp in seen:
            continue
        seen.add(name_disp)
        no = re.search(r"\d+", p.get("no", "") or "")
        out.append({
            "no": int(no.group()) if no else None,
            "pos": pos,
            "name": name_disp,
            "wiki": name_title,
            "nat": (p.get("nat", "") or "").strip().upper(),
        })
    return out


# --------------------------------------------------------------------------- #
# Headshots
# --------------------------------------------------------------------------- #
def fetch_page_images(titles: list[str]) -> dict[str, dict]:
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
    if len(data) < 800:
        return False
    tmp = dest + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return True


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _assign(code: str, players: list[dict]) -> list[dict]:
    players.sort(key=lambda p: (POS_ORDER[p["pos"]], p["no"] if p["no"] else 99))
    for i, p in enumerate(players):
        iso2, natname = nation_info(p["nat"])
        p["id"] = f"{code}-{i + 1:02d}"
        p["position"] = p.pop("pos")
        p["detailedPosition"] = POS_WORD[p["position"]]
        p["shirtNumber"] = p.pop("no") or 0
        p["nationIso2"] = iso2
        p["nationName"] = natname
        p["headshot"] = None
        p["photoCredit"] = None
    return players


def fetch_club(code: str, title: str) -> list[dict]:
    data = _api("en.wikipedia.org", {"action": "parse", "prop": "wikitext",
                                     "page": title, "redirects": "1"})
    if "parse" not in data:
        raise RuntimeError(f"no article for {title!r}")
    players = parse_club_squad(data["parse"]["wikitext"]["*"])
    if not players:
        raise RuntimeError(f"no squad parsed from {title!r}")
    return _assign(code, players)


def _attach_headshots(league_id: str, code: str, players: list[dict],
                      credits: dict, force: bool) -> int:
    dest_dir = os.path.join(HEADSHOT_ROOT, league_id)
    os.makedirs(dest_dir, exist_ok=True)
    got = 0
    wiki_titles = [p["wiki"] for p in players]
    pi = fetch_page_images(wiki_titles)
    need = [pi[p["wiki"]]["file"] for p in players if p["wiki"] in pi]
    lic = commons_licence(sorted(set(need)))
    for p in players:
        info = pi.get(p["wiki"])
        key = info["file"].replace("_", " ").strip() if info else None
        if not info or key not in lic:
            continue
        rel = f"headshots/{league_id}/{p['id']}.jpg"
        dest = os.path.join(PUBLIC_DIR, rel)
        if os.path.exists(dest) and not force:
            ok = True
        else:
            ok = download(info["thumb"], dest)
        if ok:
            meta = lic[key]
            p["headshot"] = "/" + rel
            p["photoCredit"] = {"author": meta["author"], "license": meta["licence"],
                                "sourceUrl": meta["source"]}
            credits[p["id"]] = {"id": p["id"], "name": p["name"], "club": code,
                                "file": rel, **meta}
            got += 1
    return got


def refresh_league(league_id: str, only: set[str], no_images: bool, force: bool) -> dict:
    clubs = league_clubs(league_id)
    cache_path = os.path.join(SOURCE_DIR, league_id, "squads_wikipedia.json")
    cred_path = os.path.join(SOURCE_DIR, league_id, "headshot_credits.json")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    existing = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as fh:
            existing = json.load(fh).get("squads", {})
    credits = {}
    if os.path.exists(cred_path):
        with open(cred_path, encoding="utf-8") as fh:
            credits = {c["id"]: c for c in json.load(fh)}

    squads = dict(existing)
    ok = imgs = 0
    for c in clubs:
        if only and c.code not in only:
            continue
        try:
            players = fetch_club(c.code, c.wiki)
        except Exception as exc:  # noqa: BLE001 - keep cached squad on failure
            print(f"  ! {c.code} {c.wiki}: {exc} — keeping cache")
            continue
        for p in players:
            p["clubCode"] = c.code
            p["clubName"] = c.name
        if not no_images:
            try:
                imgs += _attach_headshots(league_id, c.code, players, credits, force)
            except Exception as exc:  # noqa: BLE001
                print(f"    (headshots for {c.code} skipped: {exc})")
        squads[c.code] = players
        ok += 1
        withimg = sum(1 for p in players if p["headshot"])
        print(f"  {league_id} {c.code} {c.wiki:34.34} {len(players):2d} players, {withimg:2d} headshots")

    # don't clobber a good cache with a mostly-failed run
    if ok < max(1, len(clubs) // 2) and existing and not only:
        print(f"[squads] only {ok}/{len(clubs)} {league_id} clubs fetched — keeping cache")
        return {"league": league_id, "clubs": ok, "images": imgs, "skipped": True}

    payload = {"source": "en.wikipedia.org (Fs player squad templates)",
               "league": league_id, "clubs": len(squads),
               "players": sum(len(v) for v in squads.values()), "squads": squads}
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    with open(cred_path, "w", encoding="utf-8") as fh:
        json.dump([credits[k] for k in sorted(credits)], fh, ensure_ascii=False, indent=1)

    print(f"[squads] {league_id}: {ok} clubs, {payload['players']} players, "
          f"{imgs} headshots this run -> {cache_path}")
    return {"league": league_id, "clubs": ok, "images": imgs, "skipped": False}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fetch real club squads + free headshots")
    ap.add_argument("--league", default="", help="epl | laliga (default: both)")
    ap.add_argument("--only", default="", help="comma-separated club codes")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--force-images", action="store_true")
    args = ap.parse_args(argv)

    leagues = [args.league] if args.league else list(LEAGUES)
    only = {c.strip().upper() for c in args.only.split(",") if c.strip()}
    for lg in leagues:
        refresh_league(lg, only, args.no_images, args.force_images)


if __name__ == "__main__":
    main()
