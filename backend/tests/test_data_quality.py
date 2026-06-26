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
from app.services.data_quality import SEED_DIR, REPORTS_DIR, compute_data_quality_summary


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


def test_summary_endpoint_returns_current_counts(client):
    response = client.get("/api/data-quality/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["remaining_unmatched_official_players"] == 652
    assert body["remaining_unmatched_seed_players"] == 73
    assert body["matched_player_field_update_candidates"] == 0
    assert body["control_character_issues"] == 0


def test_summary_matches_current_repository_reports():
    summary = compute_data_quality_summary()

    # 670 = 669 + Zion Suzuki (Japan's real No.1 GK, added in Phase 2a GK fixes).
    assert summary["seed_player_count"] == 670
    assert summary["seed_team_count"] == 48
    assert summary["remaining_unmatched_official_players"] == 652
    assert summary["remaining_unmatched_seed_players"] == 73
    assert summary["matched_player_field_update_candidates"] == 0
    assert summary["control_character_issues"] == 0
    assert summary["official_profile_players"] == summary["seed_player_count"] - 73
    assert 0 < summary["official_profile_coverage_pct"] < 100


def test_missing_report_falls_back_gracefully(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "players.json").write_text(json.dumps([{"id": "A"}, {"id": "B"}]), encoding="utf-8")
    (seed_dir / "teams.json").write_text(json.dumps([{"id": "T"}]), encoding="utf-8")
    (seed_dir / "players2026_official.json").write_text(
        json.dumps([{"playerId": "A", "caps": 1}, {"playerId": "B", "caps": None, "clubName": None}]),
        encoding="utf-8",
    )
    (seed_dir / "metadata.json").write_text(json.dumps({"lastUpdated": "2026-01-01T00:00:00Z"}), encoding="utf-8")

    empty_reports_dir = tmp_path / "reports"

    summary = compute_data_quality_summary(seed_dir=seed_dir, reports_dir=empty_reports_dir)

    assert summary["seed_player_count"] == 2
    assert summary["official_profile_players"] == 1
    assert summary["remaining_unmatched_official_players"] is None
    assert summary["remaining_unmatched_seed_players"] is None
    assert summary["matched_player_field_update_candidates"] is None
    assert summary["last_report_update"] is None
    assert any("照合レポート" in note for note in summary["notes"])


def test_real_seed_and_reports_directories_exist():
    assert SEED_DIR.exists()
    assert REPORTS_DIR.exists()
