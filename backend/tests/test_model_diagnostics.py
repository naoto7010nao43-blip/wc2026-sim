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
    get_manager_tactical_trust_summary,
    get_rating_review_workbench_summary,
    get_squad_gap_summary,
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
