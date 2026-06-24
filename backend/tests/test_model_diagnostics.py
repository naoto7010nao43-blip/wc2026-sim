import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.model_diagnostics import (
    REPORTS_DIR,
    get_external_data_verification_summary,
    get_manager_tactical_trust_summary,
    get_model_calibration_summary,
    get_rating_decision_audit_summary,
    get_rating_review_workbench_summary,
    get_release_readiness_summary,
    get_simulation_stability_summary,
    get_squad_gap_summary,
    get_source_provenance_audit_summary,
    get_substitution_model_gap_summary,
    get_team_review_summary,
)


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_team_review_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/team-review")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "teamCount" in body
    assert "teams" in body
    assert body["teamCount"] == len(body["teams"])


def test_team_review_endpoint_top_team_has_full_row_shape(client):
    response = client.get("/api/model-diagnostics/team-review")
    body = response.json()
    assert body["teamCount"] > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "fifa_rank", "seed_roster_size",
        "rank_underperformance_flags", "priority_score", "priority_band",
        "review_reasons", "recommended_next_action",
    ):
        assert field in row


def test_release_readiness_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/release-readiness")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "generatedAt", "note", "readyForManualPush", "blockers", "currentTask",
        "gitStatusShort", "modelVersions", "rank75Benchmark", "requiredReports", "requiredCommands",
    ):
        assert field in body


def test_release_readiness_endpoint_uses_order_neutral_versions(client):
    response = client.get("/api/model-diagnostics/release-readiness")
    body = response.json()
    assert body["modelVersions"]["baselineModelVersion"] == "poisson-v1-rank60-order-neutral"
    assert body["modelVersions"]["currentModelVersion"] == "poisson-v2-rank75-order-neutral"
    assert body["rank75Benchmark"]["benchmarkMethod"] == "dual_order_average"


def test_external_data_verification_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/external-data-verification")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "generatedAt", "note", "valid", "errorCount", "warningCount", "candidateCount",
        "coveredTeamCount", "totalTeamCount", "remainingTeamCount", "scope",
        "categoryCounts", "impactCounts", "useTierCounts", "teamSignalBandCounts",
        "sparseTeamIds", "topTeamPriorities", "teamSignalProfiles", "decisionQueue", "warnings", "errors",
    ):
        assert field in body


def test_external_data_verification_endpoint_exposes_partial_progress(client):
    response = client.get("/api/model-diagnostics/external-data-verification")
    body = response.json()
    assert body["valid"] is True
    assert body["coveredTeamCount"] == 16
    assert body["remainingTeamCount"] == 32
    assert body["candidateCount"] == 121
    assert body["teamSignalBandCounts"]["strong"] == 16
    assert body["decisionQueue"]["currentFieldReviewCount"] == 73
    assert body["decisionQueue"]["warningHoldCount"] == 4
    assert body["decisionQueue"]["futureEngineCount"] == 15


def test_external_data_verification_missing_report_falls_back_to_calm_empty_state(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "teams.json").write_text('[{"id":"AAA"},{"id":"BBB"}]', encoding="utf-8")
    summary = get_external_data_verification_summary(reports_dir=tmp_path, seed_dir=seed_dir)
    assert summary["generatedAt"] is None
    assert summary["valid"] is False
    assert summary["coveredTeamCount"] == 0
    assert summary["totalTeamCount"] == 2
    assert summary["remainingTeamCount"] == 2
    assert summary["note"]


def test_get_external_data_verification_summary_is_read_only(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "teams.json").write_text('[{"id":"AAA"}]', encoding="utf-8")
    validation_report = {
        "valid": True,
        "errorCount": 0,
        "warningCount": 0,
        "candidateCount": 1,
        "coveredTeamCount": 1,
        "categoryCounts": {},
        "impactCounts": {},
        "useTierCounts": {},
        "teamSignalBandCounts": {"strong": 1},
        "sparseTeamIds": [],
        "topTeamPriorities": [],
        "teamSignalProfiles": [],
        "decisionQueue": None,
        "warnings": [],
        "errors": [],
    }
    candidate_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "scope": {"coveredTeams": ["AAA"], "remainingUnresearchedTeams": []},
        "teams": [],
    }
    validation_path = tmp_path / "external_data_verification_validation_2026-01-01.json"
    candidates_path = tmp_path / "external_data_verification_candidates_2026-01-01.json"
    validation_path.write_text(json.dumps(validation_report), encoding="utf-8")
    candidates_path.write_text(json.dumps(candidate_report), encoding="utf-8")
    before = validation_path.read_text(encoding="utf-8")

    get_external_data_verification_summary(reports_dir=tmp_path, seed_dir=seed_dir)

    assert validation_path.read_text(encoding="utf-8") == before


def test_release_readiness_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_release_readiness_summary(reports_dir=tmp_path)
    assert summary["generatedAt"] is None
    assert summary["readyForManualPush"] is False
    assert summary["blockers"]
    assert summary["requiredReports"] == []


def test_get_release_readiness_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "note": "test",
        "readyForManualPush": True,
        "blockers": [],
        "currentTask": {"hasActiveReadyTask": False, "awaitingNextSpec": True, "latestCompletedSpecText": None},
        "gitStatusShort": [],
        "modelVersions": {"baselineModelVersion": "a", "currentModelVersion": "b"},
        "rank75Benchmark": {
            "present": True,
            "path": "x",
            "status": "pass",
            "benchmarkMethod": "dual_order_average",
            "watchlistImplausibleReduction": 0.0,
            "overallImplausibleFavoriteCountDelta": 0.0,
            "averageFavoriteWinPctDelta": 0.0,
        },
        "requiredReports": [],
        "requiredCommands": [],
    }
    report_path = tmp_path / "release_readiness_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_release_readiness_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_team_review_summary(reports_dir=tmp_path)
    assert summary["teamCount"] == 0
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["note"]


def test_real_reports_directory_exists():
    assert REPORTS_DIR.exists()


def test_get_team_review_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "teamCount": 1,
        "teams": [{"team_id": "AAA"}],
    }
    report_path = tmp_path / "team_data_review_plan_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_team_review_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_squad_gaps_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/squad-gaps")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "teams" in body


def test_squad_gaps_endpoint_top_team_has_expected_fields(client):
    response = client.get("/api/model-diagnostics/squad-gaps")
    body = response.json()
    assert len(body["teams"]) > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "fifa_rank", "priority_score", "rank_underperformance_flags",
        "position_groups", "rating_distribution", "trust_profile", "roster_reconciliation",
        "diagnostic_flags", "review_summary_ja", "recommended_next_action",
    ):
        assert field in row
    assert row["recommended_next_action"] == "rating_data_review"


def test_squad_gap_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_squad_gap_summary(reports_dir=tmp_path)
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["note"]


def test_get_squad_gap_summary_is_read_only(tmp_path):
    seed_report = {"generatedAt": "2026-01-01T00:00:00+00:00", "sourceReports": [], "note": "test", "teams": [{"team_id": "AAA"}]}
    report_path = tmp_path / "squad_rating_gap_review_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_squad_gap_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_manager_tactical_trust_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/manager-tactical-trust")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "teamCount" in body
    assert "bandCounts" in body
    assert "teams" in body
    assert body["teamCount"] == len(body["teams"])


def test_manager_tactical_trust_endpoint_top_team_has_full_row_shape(client):
    response = client.get("/api/model-diagnostics/manager-tactical-trust")
    body = response.json()
    assert body["teamCount"] > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "fifa_rank", "default_formation",
        "manager_name_seed", "manager_name_official", "manager_name_official_profile",
        "manager_name_mismatch", "manager_rating_confidence", "missing_manager_rating",
        "has_tactical_basis", "tactical_profile", "duplicate_profile_team_ids",
        "team_review_priority_band", "review_score", "review_band", "review_reasons",
    ):
        assert field in row


def test_manager_tactical_trust_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_manager_tactical_trust_summary(reports_dir=tmp_path)
    assert summary["teamCount"] == 0
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["bandCounts"] == {"high": 0, "medium": 0, "low": 0}
    assert summary["note"]


def test_get_manager_tactical_trust_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "teamCount": 1,
        "bandCounts": {"high": 1, "medium": 0, "low": 0},
        "teams": [{"team_id": "AAA"}],
    }
    report_path = tmp_path / "manager_tactical_data_audit_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_manager_tactical_trust_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_rating_review_workbench_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/rating-review-workbench")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "teamCount" in body
    assert "teams" in body
    assert body["teamCount"] == len(body["teams"])


def test_rating_review_workbench_endpoint_top_team_and_candidate_have_full_shape(client):
    response = client.get("/api/model-diagnostics/rating-review-workbench")
    body = response.json()
    assert body["teamCount"] > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "fifa_rank", "squad_gap_priority_score",
        "rank_underperformance_flags", "recommended_next_action",
        "position_group_summary", "rating_review_candidates",
    ):
        assert field in row
    assert len(row["rating_review_candidates"]) > 0
    candidate = row["rating_review_candidates"][0]
    for field in (
        "player_id", "name", "primary_position", "current_overall", "starting_probability",
        "data_confidence", "review_score", "review_band", "review_flags",
        "review_summary_ja", "suggested_codex_action",
    ):
        assert field in candidate


def test_rating_review_workbench_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_rating_review_workbench_summary(reports_dir=tmp_path)
    assert summary["teamCount"] == 0
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["note"]


def test_get_rating_review_workbench_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "teamCount": 1,
        "teams": [{"team_id": "AAA"}],
    }
    report_path = tmp_path / "rating_review_workbench_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_rating_review_workbench_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_source_provenance_audit_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/source-provenance-audit")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "seedSourceSummary" in body
    assert "decisionCandidateCount" in body
    assert "clearLaterProposalCandidateCount" in body
    assert "sourceReviewCandidateCount" in body
    assert "teamCount" in body
    assert "teams" in body
    assert "recommendations_ja" in body
    assert body["teamCount"] == len(body["teams"])


def test_source_provenance_audit_endpoint_top_team_has_expected_shape(client):
    response = client.get("/api/model-diagnostics/source-provenance-audit")
    body = response.json()
    assert body["teamCount"] > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "candidate_count", "source_risk_candidate_count",
        "decision_bucket_counts", "clear_later_proposal_candidates", "source_review_candidates",
    ):
        assert field in row
    assert body["seedSourceSummary"]["seed_player_count"] > 0


def test_source_provenance_audit_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_source_provenance_audit_summary(reports_dir=tmp_path)
    assert summary["teamCount"] == 0
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["seedSourceSummary"]["seed_player_count"] == 0
    assert summary["recommendations_ja"]


def test_get_source_provenance_audit_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "seedSourceSummary": {
            "seed_player_count": 1,
            "players_with_source_risk": 0,
            "marker_counts": {},
            "severity_counts": {},
            "top_risky_seed_players": [],
        },
        "decisionCandidateCount": 0,
        "clearLaterProposalCandidateCount": 0,
        "sourceReviewCandidateCount": 0,
        "teamCount": 0,
        "teams": [],
        "recommendations_ja": ["test"],
    }
    report_path = tmp_path / "source_provenance_audit_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_source_provenance_audit_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_rating_decision_audit_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/rating-decision-audit")
    assert response.status_code == 200
    body = response.json()
    assert "generatedAt" in body
    assert "sourceReports" in body
    assert "note" in body
    assert "teamCount" in body
    assert "bucketCounts" in body
    assert "teams" in body
    assert body["teamCount"] == len(body["teams"])


def test_rating_decision_audit_endpoint_top_team_has_expected_shape(client):
    response = client.get("/api/model-diagnostics/rating-decision-audit")
    body = response.json()
    assert body["teamCount"] > 0
    row = body["teams"][0]
    for field in (
        "team_id", "team_name", "dominant_negative_driver", "rank_underperformance_flags",
        "bucketCounts", "candidate_for_later_proposal", "source_review_first",
        "do_not_use_for_upgrade_proposal", "monitor_only",
    ):
        assert field in row


def test_rating_decision_audit_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_rating_decision_audit_summary(reports_dir=tmp_path)
    assert summary["teamCount"] == 0
    assert summary["teams"] == []
    assert summary["generatedAt"] is None
    assert summary["bucketCounts"] == {}
    assert summary["note"]


def test_get_rating_decision_audit_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "teamCount": 1,
        "bucketCounts": {"monitor_only": 1},
        "teams": [{"team_id": "AAA"}],
    }
    report_path = tmp_path / "rating_decision_audit_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_rating_decision_audit_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_model_calibration_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/model-calibration")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "generatedAt", "sourceReports", "modelVersionBefore", "modelVersionAfter",
        "status", "benchmarkMethod", "overall", "watchlist", "bestSandboxVariantId", "note", "recommendations_ja",
    ):
        assert field in body


def test_model_calibration_endpoint_has_expected_overall_and_watchlist_shape(client):
    response = client.get("/api/model-diagnostics/model-calibration")
    body = response.json()
    assert body["modelVersionAfter"].startswith("poisson-v2-rank75")
    assert body["status"] == "pass"
    for field in (
        "before_matchup_count", "after_matchup_count", "average_favorite_win_pct_delta",
        "implausible_favorite_count_delta", "minimum_favorite_win_pct_delta", "maximum_favorite_win_pct_delta",
    ):
        assert field in body["overall"]
    assert "watchlist_implausible_reduction" in body["watchlist"]
    assert len(body["watchlist"]["teams"]) > 0
    for field in ("team_id", "average_favorite_win_pct_delta", "implausible_favorite_count_delta"):
        assert field in body["watchlist"]["teams"][0]


def test_model_calibration_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_model_calibration_summary(reports_dir=tmp_path)
    assert summary["generatedAt"] is None
    assert summary["overall"] is None
    assert summary["watchlist"] is None
    assert summary["benchmarkMethod"] is None
    assert summary["note"]
    assert summary["recommendations_ja"] == []


def test_get_model_calibration_summary_is_read_only(tmp_path):
    seed_report = {
        "beforeGeneratedAt": "2026-01-01T00:00:00+00:00",
        "afterGeneratedAt": "2026-01-02T00:00:00+00:00",
        "modelVersionBefore": "poisson-v1",
        "modelVersionAfter": "poisson-v2-rank75",
        "benchmarkMethod": "dual_order_average",
        "overall": {
            "before_matchup_count": 1, "after_matchup_count": 1,
            "average_favorite_win_pct_delta": 0.1, "implausible_favorite_count_delta": 0.0,
            "minimum_favorite_win_pct_delta": 0.1, "maximum_favorite_win_pct_delta": 0.1,
        },
        "rankGapBuckets": [],
        "watchlistTeams": [],
        "evaluation": {"status": "pass", "watchlist_implausible_reduction": 0.0, "warnings": []},
    }
    report_path = tmp_path / "prediction_benchmark_comparison_rank75_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_model_calibration_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_model_calibration_summary_prefers_order_neutral_report(tmp_path):
    old_report = {
        "beforeGeneratedAt": "2026-01-01T00:00:00+00:00",
        "afterGeneratedAt": "2026-01-02T00:00:00+00:00",
        "modelVersionBefore": "poisson-v1",
        "modelVersionAfter": "poisson-v2-rank75",
        "overall": {
            "before_matchup_count": 1, "after_matchup_count": 1,
            "average_favorite_win_pct_delta": 0.1, "implausible_favorite_count_delta": 0.0,
            "minimum_favorite_win_pct_delta": 0.1, "maximum_favorite_win_pct_delta": 0.1,
        },
        "rankGapBuckets": [],
        "watchlistTeams": [],
        "evaluation": {"status": "pass", "watchlist_implausible_reduction": 0.0, "warnings": []},
    }
    neutral_report = {
        **old_report,
        "generatedAt": "2026-01-03T00:00:00+00:00",
        "modelVersionAfter": "poisson-v2-rank75-order-neutral",
        "benchmarkMethod": "dual_order_average",
    }
    (tmp_path / "prediction_benchmark_comparison_rank75_2026-01-02.json").write_text(
        json.dumps(old_report), encoding="utf-8"
    )
    (tmp_path / "prediction_benchmark_comparison_rank75_order_neutral_2026-01-03.json").write_text(
        json.dumps(neutral_report), encoding="utf-8"
    )

    summary = get_model_calibration_summary(reports_dir=tmp_path)

    assert summary["modelVersionAfter"] == "poisson-v2-rank75-order-neutral"
    assert summary["benchmarkMethod"] == "dual_order_average"
    assert summary["sourceReports"][0]["name"] == "prediction_benchmark_comparison_rank75_order_neutral"


def test_simulation_stability_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/simulation-stability")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "generatedAt", "sourceReports", "modelVersion", "note", "scope",
        "samples", "comparisons", "summary",
    ):
        assert field in body


def test_simulation_stability_endpoint_has_summary_when_report_exists(client):
    response = client.get("/api/model-diagnostics/simulation-stability")
    body = response.json()
    assert body["summary"]["stabilityBand"] in {"stable", "usable", "volatile"}
    assert body["summary"]["maxAbsChampionPctDelta"] >= 0
    assert len(body["samples"]) >= 1
    assert "topChampionCandidates" in body["samples"][-1]


def test_simulation_stability_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_simulation_stability_summary(reports_dir=tmp_path)
    assert summary["generatedAt"] is None
    assert summary["scope"] is None
    assert summary["samples"] == []
    assert summary["comparisons"] == []
    assert summary["summary"] is None
    assert summary["note"]


def test_get_simulation_stability_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "modelVersion": "poisson-test",
        "note": "test",
        "scope": {"iterationCounts": [100], "baseSeed": 1, "sampleCount": 1},
        "samples": [],
        "comparisons": [],
        "summary": {
            "stabilityBand": "stable",
            "maxAbsChampionPctDelta": 0.0,
            "averageAbsChampionPctDelta": 0.0,
            "recommendation": "current_default_stable",
            "recommendation_ja": "安定しています。",
        },
    }
    report_path = tmp_path / "simulation_stability_audit_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_simulation_stability_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before


def test_substitution_model_gap_endpoint_returns_200_with_expected_top_level_fields(client):
    response = client.get("/api/model-diagnostics/substitution-model-gap")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "generatedAt", "sourceReports", "note", "engineCapabilities",
        "gapCount", "gaps", "recommendationsJa", "summary",
    ):
        assert field in body
    assert body["gapCount"] == len(body["gaps"])


def test_substitution_model_gap_endpoint_exposes_current_engine_limits(client):
    response = client.get("/api/model-diagnostics/substitution-model-gap")
    body = response.json()
    assert body["engineCapabilities"]["hasSubstitutionEvents"] is True
    assert body["engineCapabilities"]["hasManagerSpecificSubstitutionParameters"] is False
    assert body["summary"]["safeCurrentAction"] == "read_only_candidate_collection"
    assert len(body["gaps"]) >= 4


def test_substitution_model_gap_missing_report_falls_back_to_calm_empty_state(tmp_path):
    summary = get_substitution_model_gap_summary(reports_dir=tmp_path)
    assert summary["generatedAt"] is None
    assert summary["engineCapabilities"] is None
    assert summary["gapCount"] == 0
    assert summary["gaps"] == []
    assert summary["note"]


def test_get_substitution_model_gap_summary_is_read_only(tmp_path):
    seed_report = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceReports": [],
        "note": "test",
        "engineCapabilities": {
            "hasSubstitutionEvents": True,
            "hasManagerSpecificSubstitutionParameters": False,
            "hasScoreStateSubstitutionBias": False,
            "hasPositionSpecificSubstitutionPreferences": False,
            "maxSubs": 3,
            "subWindow": {"startMinute": 55, "endMinute": 88},
            "subChancePerMinute": 0.1,
            "subFatigueGap": 0.02,
            "selectionRule": "generic",
        },
        "gapCount": 0,
        "gaps": [],
        "recommendationsJa": ["test"],
        "summary": {
            "currentModelHasManagerSpecificSubstitutions": False,
            "dataResearchCanBeStored": True,
            "safeCurrentAction": "read_only_candidate_collection",
            "recommendedNextSpec": "manager_substitution_tendency_model",
        },
    }
    report_path = tmp_path / "substitution_model_gap_audit_2026-01-01.json"
    report_path.write_text(json.dumps(seed_report), encoding="utf-8")
    before = report_path.read_text(encoding="utf-8")

    get_substitution_model_gap_summary(reports_dir=tmp_path)

    assert report_path.read_text(encoding="utf-8") == before
