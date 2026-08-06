"""
Unit tests for ``club_crests`` verification — the guard that stops a wrong crest
being attached to a club. Pure logic, no network.
"""
import club_crests
from leagues import club


def _team(name, country="England", sport="Soccer", alt=None, badge="x.png"):
    return {"strTeam": name, "strCountry": country, "strSport": sport,
            "strTeamAlternate": alt, "strBadge": badge}


def test_verify_accepts_exact_alias():
    ars = club("epl", "ARS")
    assert club_crests._verify("epl", ars, _team("Arsenal")) is True


def test_verify_accepts_spelling_variant_by_token_subset():
    # "Brighton and Hove Albion" (CDN) vs "Brighton & Hove Albion" (registry).
    bha = club("epl", "BHA")
    assert club_crests._verify("epl", bha, _team("Brighton and Hove Albion")) is True


def test_verify_rejects_wrong_sport():
    nfo = club("epl", "NFO")
    assert club_crests._verify("epl", nfo, _team("Nottingham Forest", sport="Netball")) is False


def test_verify_rejects_wrong_country():
    ars = club("epl", "ARS")
    assert club_crests._verify("epl", ars, _team("Arsenal", country="Spain")) is False


def test_verify_rejects_different_club():
    rma = club("laliga", "RMA")
    assert club_crests._verify("laliga", rma, _team("Real Betis", country="Spain")) is False
