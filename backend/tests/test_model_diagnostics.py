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
from app.services.model_diagnostics import REPORTS_DIR, get_team_review_summary


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
