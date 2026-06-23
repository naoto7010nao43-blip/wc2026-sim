import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_prediction_benchmark_baseline import (
    build_player_lookup,
    is_implausible_favorite,
    minimum_expected_favorite_win_pct,
    rank_gap_bucket,
    summarize_by_bucket,
    summarize_matchups,
    summarize_watchlist,
    top_ranked_teams,
    watchlist_team_ids,
)


def test_rank_gap_bucket_boundaries():
    assert rank_gap_bucket(0) == "00-02"
    assert rank_gap_bucket(2) == "00-02"
    assert rank_gap_bucket(3) == "03-05"
    assert rank_gap_bucket(10) == "06-10"
    assert rank_gap_bucket(11) == "11-20"
    assert rank_gap_bucket(21) == "21+"


def test_minimum_expected_favorite_win_pct_is_gentle_and_capped():
    assert minimum_expected_favorite_win_pct(0) == 33.0
    assert minimum_expected_favorite_win_pct(10) == 45.0
    assert minimum_expected_favorite_win_pct(100) == 55.0
    assert is_implausible_favorite(40.0, 10) is True
    assert is_implausible_favorite(50.0, 10) is False


def test_top_ranked_teams_ignores_missing_ranks_and_sorts():
    teams = [
        {"id": "B", "fifa_rank": 2},
        {"id": "A", "fifa_rank": 1},
        {"id": "Z", "fifa_rank": None},
    ]
    assert [row["id"] for row in top_ranked_teams(teams, limit=2)] == ["A", "B"]


def test_watchlist_team_ids_uses_report_order_and_limit():
    report = {"teams": [{"team_id": "CRO"}, {"team_id": "NED"}, {"team_id": "POR"}]}
    assert watchlist_team_ids(report, limit=2) == ["CRO", "NED"]
    assert watchlist_team_ids(None) == []


def test_build_player_lookup_joins_seed_players_to_rating_rows():
    seed_players = [
        {"id": "P1", "team_id": "AAA", "name": "One", "primary_position": "FW", "stamina_max": 80},
        {"id": "P2", "team_id": "AAA", "name": "Two", "primary_position": "MF"},
    ]
    rating_rows = [
        {"playerId": "P1", "teamId": "AAA", "overall": 70, "finishing": 71, "stamina": 82},
    ]
    lookup = build_player_lookup(seed_players, rating_rows)
    assert len(lookup["AAA"]) == 1
    assert lookup["AAA"][0]["overall"] == 70
    assert lookup["AAA"][0]["attributes"]["finishing"] == 71
    assert lookup["AAA"][0]["stamina_max"] == 80


def test_summarize_matchups_handles_empty_and_nonempty():
    assert summarize_matchups([])["matchup_count"] == 0
    rows = [
        {"favorite_win_pct": 40.0, "implausible_favorite": True},
        {"favorite_win_pct": 60.0, "implausible_favorite": False},
    ]
    summary = summarize_matchups(rows)
    assert summary["matchup_count"] == 2
    assert summary["average_favorite_win_pct"] == 50.0
    assert summary["minimum_favorite_win_pct"] == 40.0
    assert summary["implausible_favorite_count"] == 1


def test_summarize_by_bucket_groups_rows():
    rows = [
        {"rank_gap_bucket": "00-02", "favorite_win_pct": 40.0, "implausible_favorite": False},
        {"rank_gap_bucket": "06-10", "favorite_win_pct": 45.0, "implausible_favorite": True},
        {"rank_gap_bucket": "06-10", "favorite_win_pct": 55.0, "implausible_favorite": False},
    ]
    result = summarize_by_bucket(rows)
    assert [row["rank_gap_bucket"] for row in result] == ["00-02", "06-10"]
    assert result[1]["matchup_count"] == 2
    assert result[1]["average_favorite_win_pct"] == 50.0


def test_summarize_watchlist_includes_lowest_matchups():
    rows = [
        {
            "favorite_team_id": "CRO", "away_team_id": "AAA", "rank_gap": 5,
            "favorite_win_pct": 41.0, "minimum_expected_favorite_win_pct": 39.0,
            "implausible_favorite": False,
        },
        {
            "favorite_team_id": "CRO", "away_team_id": "BBB", "rank_gap": 10,
            "favorite_win_pct": 39.0, "minimum_expected_favorite_win_pct": 45.0,
            "implausible_favorite": True,
        },
    ]
    result = summarize_watchlist(rows, ["CRO", "NED"])
    assert result[0]["team_id"] == "CRO"
    assert result[0]["matchup_count"] == 2
    assert result[0]["lowest_favorite_matchups"][0]["away_team_id"] == "BBB"
    assert result[1]["team_id"] == "NED"
    assert result[1]["matchup_count"] == 0
