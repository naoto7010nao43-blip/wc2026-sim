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
    assert body["real_group_match_count"] == 72
    assert body["real_group_match_expected"] == 72
    assert body["real_group_match_coverage_pct"] == 100.0
    assert body["real_knockout_match_count"] == 24
    assert body["freshness_status"] == "critical"
    assert body["freshness_critical_count"] == 1
    assert body["freshness_warning_count"] >= 1


def test_summary_matches_current_repository_reports():
    summary = compute_data_quality_summary()

    # 676 = 669 + real 2026 WC starters that were previously missing from the
    # roster: Zion Suzuki (Japan No.1 GK, Phase 2a), Ayumu Seko (Japan back-3 CB,
    # Phase 2b), Keito Nakamura (Japan left shadow-striker, Phase 2b), and the
    # Phase 2c cross-team additions Antonio Nusa (Norway LW), Joel Ordonez
    # (Ecuador back-3 CB), Maximiliano Araujo (Uruguay LW) and Ben Doak
    # (Scotland RW), each confirmed from a played 2026 WC lineup. (Croatia's
    # Perisic fix was a position/override correction on an existing player, so it
    # does not change the count.)
    # 677 = the 676 above + Hakan Calhanoglu (TUR_CALHANOGLU), Turkiye's captain
    # and chief playmaker, who was entirely absent from the roster so the sim
    # fielded Turkiye without their key midfielder. Added 2026-07-01 with a
    # sourced profile + EA FC 26 rating (overall 86) and a startingProbability
    # override (confirmed 2026 WC starter).
    # 678 = the 677 above + Simon Banza (COD_BANZA), DR Congo's second-highest-
    # rated attacker (EA FC 26 overall 81, id 231652), who was entirely absent
    # from the roster. Added 2026-07-02 with a sourced profile + EA rating and
    # no startingProbability override (the rating blend ranks him as a strong
    # squad forward behind Yoane Wissa, which is the accurate depth picture).
    assert summary["seed_player_count"] == 678
    assert summary["seed_team_count"] == 48
    assert summary["remaining_unmatched_official_players"] == 652
    assert summary["remaining_unmatched_seed_players"] == 73
    assert summary["matched_player_field_update_candidates"] == 0
    assert summary["control_character_issues"] == 0
    # Ladislav Krejci's 2026-07-01 correction added a source-backed official
    # profile (club/caps/goals) without changing the historical unmatched-seed
    # merge report count (603 -> 604). The 2026-07-01 Czech goalkeeper roster
    # refresh then completed two more profiles that were previously stale
    # placeholders with null club/caps: CZE_KOVAR (Matyas Vagner -> Matej Kovar,
    # PSV) and CZE_JAROS (Antonin Kinsky -> Lukas Hornicek, SC Braga), each
    # confirmed against the final 26-man squad and EA FC 26 (604 -> 606).
    # The same-day Bosnia XI refresh then completed three more stale null-club
    # placeholders, each replaced by a confirmed 2026 WC starter with a sourced
    # profile + EA FC 26 rating: BIH_HADZIKADUNIC (Toni Sunjic -> Nikola Katic,
    # Schalke), BIH_BARISIC (Ognjen Vranjes -> Tarik Muharemovic, Sassuolo) and
    # BIH_GOJAK (Gojko Cimirot -> Benjamin Tahirovic, Brondby) (606 -> 609).
    # The 2026-07-01 Sweden refresh then completed one more stale null-club
    # placeholder: SWE_EKDAL_A (Albin Ekdal, retired from int'l football and not
    # in Sweden's final 26 -> Mattias Svanberg, VfL Wolfsburg), a confirmed 2026
    # squad midfielder with a sourced profile + EA FC 26 rating. Adding his club
    # (previously null) flips him into the official-profile count (609 -> 610).
    # The same-day addition of Hakan Calhanoglu (TUR_CALHANOGLU), a fully-
    # profiled new player with club + caps, adds one more (610 -> 611).
    # The 2026-07-02 addition of Simon Banza (COD_BANZA), a fully-profiled new
    # player with a club (Al-Jazira), adds one more (611 -> 612).
    assert summary["official_profile_players"] == 612
    assert 0 < summary["official_profile_coverage_pct"] < 100
    assert summary["real_group_match_count"] == 72
    assert summary["real_group_match_expected"] == 72
    assert summary["real_group_match_coverage_pct"] == 100.0
    assert summary["real_knockout_match_count"] == 24
    assert summary["freshness_status"] == "critical"
    assert summary["freshness_critical_count"] == 1
    assert summary["freshness_warning_count"] >= 1
    assert any("公式スカッドfeed" in note for note in summary["notes"])


def test_missing_report_falls_back_gracefully(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "players.json").write_text(json.dumps([{"id": "A"}, {"id": "B"}]), encoding="utf-8")
    (seed_dir / "teams.json").write_text(json.dumps([{"id": "T"}]), encoding="utf-8")
    (seed_dir / "players2026_official.json").write_text(
        json.dumps([{"playerId": "A", "caps": 1}, {"playerId": "B", "caps": None, "clubName": None}]),
        encoding="utf-8",
    )
    (seed_dir / "metadata.json").write_text(
        json.dumps({"lastUpdated": "2026-01-01T00:00:00Z", "freshnessPolicy": {"playerRatingsMaxAgeDays": 30}}),
        encoding="utf-8",
    )

    empty_reports_dir = tmp_path / "reports"

    summary = compute_data_quality_summary(seed_dir=seed_dir, reports_dir=empty_reports_dir)

    assert summary["seed_player_count"] == 2
    assert summary["official_profile_players"] == 1
    assert summary["remaining_unmatched_official_players"] is None
    assert summary["remaining_unmatched_seed_players"] is None
    assert summary["matched_player_field_update_candidates"] is None
    assert summary["last_report_update"] is None
    assert summary["real_group_match_count"] == 0
    assert summary["real_group_match_expected"] == 0
    assert summary["real_group_match_coverage_pct"] == 0.0
    assert summary["real_knockout_match_count"] == 0
    assert summary["freshness_status"] == "warning"
    assert summary["freshness_warning_count"] == 1
    assert any("照合レポート" in note for note in summary["notes"])


def test_real_seed_and_reports_directories_exist():
    assert SEED_DIR.exists()
    assert REPORTS_DIR.exists()
