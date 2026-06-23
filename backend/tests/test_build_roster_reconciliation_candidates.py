import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_roster_reconciliation_candidates import (
    build_team_candidates,
    classify_add_candidate,
    classify_seed_player,
    fuzzy_overlap_score,
    seed_roster_sizes,
)


def test_classify_add_candidate_low_risk_when_roster_shallow():
    risk, reason = classify_add_candidate(12)
    assert risk == "low"
    assert "12 players" in reason


def test_classify_add_candidate_medium_risk_when_roster_deep():
    risk, reason = classify_add_candidate(19)
    assert risk == "medium"


def test_classify_seed_player_risk_scales_with_score():
    assert classify_seed_player(0)[0] == "medium"
    assert classify_seed_player(1)[0] == "medium"
    assert classify_seed_player(3)[0] == "medium"
    assert "No name-token overlap" in classify_seed_player(0)[1]
    assert "Shares 3 name tokens" in classify_seed_player(3)[1]


def test_fuzzy_overlap_score_counts_shared_tokens():
    assert fuzzy_overlap_score("Julio Gonzalez", "GONZALEZ Julio GONZALEZ TORRES JULIO G.") >= 1
    assert fuzzy_overlap_score("Totally Different", "NOBODY ALIKE AT ALL") == 0


def test_seed_roster_sizes_counts_per_team():
    players = [{"team_id": "BRA"}, {"team_id": "BRA"}, {"team_id": "USA"}]
    assert seed_roster_sizes(players) == {"BRA": 2, "USA": 1}


def test_build_team_candidates_pairs_same_position_group_by_name_overlap():
    seed_unmatched = [{"playerId": "MEX_VEGA", "name": "Julio Gonzalez", "primaryPosition": "GK"}]
    official_unmatched = [
        {"name_block": "GONZALEZ Julio GONZALEZ TORRES JULIO G.", "position": "GK", "club": "Foo FC", "caps": 5},
        {"name_block": "SOMEONE ELSE ENTIRELY", "position": "GK", "club": "Bar FC", "caps": 1},
    ]
    result = build_team_candidates("MEX", seed_unmatched, official_unmatched, roster_size=16)

    assert len(result["ambiguous_pairs"]) == 1
    assert result["ambiguous_pairs"][0]["seed_player_id"] == "MEX_VEGA"
    assert len(result["likely_stale_seed_players"]) == 0
    # The matched official candidate should be claimed and excluded from add candidates.
    remaining_add = result["high_confidence_add_candidates"] + result["other_add_candidates"]
    assert len(remaining_add) == 1
    assert remaining_add[0]["official_name_block"] == "SOMEONE ELSE ENTIRELY"


def test_build_team_candidates_marks_unmatched_seed_player_as_likely_stale_when_no_overlap():
    seed_unmatched = [{"playerId": "BRA_WESLEY", "name": "Wesley", "primaryPosition": "RB"}]
    official_unmatched = [{"name_block": "COMPLETELY UNRELATED NAME", "position": "MF", "club": None, "caps": None}]
    result = build_team_candidates("BRA", seed_unmatched, official_unmatched, roster_size=15)

    assert len(result["likely_stale_seed_players"]) == 1
    assert result["likely_stale_seed_players"][0]["seed_player_id"] == "BRA_WESLEY"
    assert len(result["ambiguous_pairs"]) == 0


def test_build_team_candidates_low_risk_add_when_roster_shallow():
    official_unmatched = [{"name_block": "SOME PLAYER", "position": "FW", "club": None, "caps": None}]
    result = build_team_candidates("ECU", [], official_unmatched, roster_size=12)
    assert len(result["high_confidence_add_candidates"]) == 1
    assert len(result["other_add_candidates"]) == 0
