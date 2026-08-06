"""
Unit tests for ``club_fpl`` — the real assists / minutes / cards enrichment.

Pure logic, no network: we monkeypatch the cache loader with synthetic FPL rows
and assert the name-matching, the "did the player actually feature" gate, the
La-Liga (unsupported league) no-op, and the pre-season ``played`` gate.
"""
import club_fpl


def _rows():
    # Two "Fernandes" at Man Utd to exercise surname + first-initial disambiguation.
    return [
        {"team": "Man Utd", "first_name": "Bruno Borges", "second_name": "Fernandes",
         "web_name": "B.Fernandes", "minutes": "3065", "goals_scored": "9",
         "assists": "18", "yellow_cards": "6", "red_cards": "1",
         "expected_assists": "9.5", "expected_goals": "7.1", "starts": "34"},
        {"team": "Man Utd", "first_name": "Diogo", "second_name": "Dalot Teixeira",
         "web_name": "Dalot", "minutes": "2500", "goals_scored": "2",
         "assists": "4", "yellow_cards": "7", "red_cards": "0",
         "expected_assists": "3.0", "expected_goals": "1.5", "starts": "28"},
        {"team": "Arsenal", "first_name": "Bukayo", "second_name": "Saka",
         "web_name": "Saka", "minutes": "2218", "goals_scored": "7",
         "assists": "10", "yellow_cards": "2", "red_cards": "0",
         "expected_assists": "8.0", "expected_goals": "6.5", "starts": "26"},
        # A player who did not feature (0 minutes) must stay null, not read as 0.
        {"team": "Arsenal", "first_name": "Reserve", "second_name": "Keeper",
         "web_name": "Keeper", "minutes": "0", "goals_scored": "0",
         "assists": "0", "yellow_cards": "0", "red_cards": "0",
         "expected_assists": "0", "expected_goals": "0", "starts": "0"},
    ]


def _players():
    return [
        {"id": "MUN-8", "name": "Bruno Fernandes", "club": "MUN", "goals": 9,
         "assists": None, "minutes": None, "yellowCards": None, "redCards": None},
        {"id": "MUN-20", "name": "Diogo Dalot", "club": "MUN", "goals": 2,
         "assists": None, "minutes": None, "yellowCards": None, "redCards": None},
        {"id": "ARS-7", "name": "Bukayo Saka", "club": "ARS", "goals": 7,
         "assists": None, "minutes": None, "yellowCards": None, "redCards": None},
        {"id": "ARS-31", "name": "Reserve Keeper", "club": "ARS", "goals": 0,
         "assists": None, "minutes": None, "yellowCards": None, "redCards": None},
        {"id": "ARS-99", "name": "Totally Unknown", "club": "ARS", "goals": 0,
         "assists": None, "minutes": None, "yellowCards": None, "redCards": None},
    ]


def test_enrich_matches_by_surname_and_initial(monkeypatch):
    monkeypatch.setattr(club_fpl, "_load_cache", lambda lg, sn: _rows())
    players = _players()
    cov = club_fpl.enrich_players("epl", "2025-26", players)

    by_id = {p["id"]: p for p in players}
    # Bruno Fernandes (two Fernandes at the club -> disambiguated by first initial B).
    assert by_id["MUN-8"]["assists"] == 18
    assert by_id["MUN-8"]["minutes"] == 3065
    assert by_id["MUN-8"]["yellowCards"] == 6
    assert by_id["MUN-8"]["redCards"] == 1
    # Diogo Dalot matched despite the CDN's longer "Dalot Teixeira" surname.
    assert by_id["MUN-20"]["assists"] == 4
    assert by_id["ARS-7"]["assists"] == 10
    assert cov["matched"] == 3
    assert cov["assists"] == 3


def test_player_who_did_not_feature_stays_null(monkeypatch):
    monkeypatch.setattr(club_fpl, "_load_cache", lambda lg, sn: _rows())
    players = _players()
    club_fpl.enrich_players("epl", "2025-26", players)
    keeper = next(p for p in players if p["id"] == "ARS-31")
    assert keeper["assists"] is None  # 0 minutes -> no real contribution recorded
    unknown = next(p for p in players if p["id"] == "ARS-99")
    assert unknown["assists"] is None  # no FPL record at all


def test_unsupported_league_is_a_noop(monkeypatch):
    monkeypatch.setattr(club_fpl, "_load_cache", lambda lg, sn: _rows())
    players = _players()
    cov = club_fpl.enrich_players("laliga", "2025-26", players)
    assert cov["matched"] == 0
    assert all(p["assists"] is None for p in players)


def test_preseason_gate_skips_enrichment(monkeypatch):
    monkeypatch.setattr(club_fpl, "_load_cache", lambda lg, sn: _rows())
    players = _players()
    # played=0 -> a not-yet-started season must not inherit last season's totals.
    cov = club_fpl.enrich_players("epl", "2026-27", players, played=0)
    assert cov["matched"] == 0
    assert all(p["assists"] is None for p in players)


def test_missing_cache_is_a_noop(monkeypatch):
    monkeypatch.setattr(club_fpl, "_load_cache", lambda lg, sn: None)
    players = _players()
    cov = club_fpl.enrich_players("epl", "2025-26", players)
    assert cov["matched"] == 0
    assert all(p["assists"] is None for p in players)
