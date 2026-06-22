import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_data_freshness import check_freshness


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def test_not_yet_integrated_source_produces_only_a_notice():
    metadata = {
        "freshnessPolicy": {},
        "sources": [{"name": "clubElo API", "status": "not_yet_integrated"}],
    }
    findings = check_freshness(metadata)
    assert len(findings) == 1
    assert findings[0]["level"] == "notice"


def test_stale_hours_based_source_triggers_critical():
    metadata = {
        "freshnessPolicy": {"officialRosterMaxAgeHours": 24},
        "sources": [{
            "name": "FIFA Official Squad feed",
            "status": "active",
            "lastChecked": _iso(hours_ago=48),
        }],
    }
    findings = check_freshness(metadata)
    assert any(f["level"] == "critical" for f in findings)


def test_fresh_hours_based_source_produces_no_finding():
    metadata = {
        "freshnessPolicy": {"officialRosterMaxAgeHours": 24},
        "sources": [{
            "name": "FIFA Official Squad feed",
            "status": "active",
            "lastChecked": _iso(hours_ago=1),
        }],
    }
    assert check_freshness(metadata) == []


def test_stale_days_based_source_triggers_warning_not_critical():
    metadata = {
        "freshnessPolicy": {"marketValueMaxAgeDays": 7},
        "sources": [{
            "name": "Transfermarkt-derived market values",
            "status": "active",
            "lastChecked": _iso(hours_ago=24 * 30),
        }],
    }
    findings = check_freshness(metadata)
    assert len(findings) == 1
    assert findings[0]["level"] == "warning"


def test_active_source_missing_last_checked_warns():
    metadata = {
        "freshnessPolicy": {},
        "sources": [{"name": "World Football Elo Ratings", "status": "active"}],
    }
    findings = check_freshness(metadata)
    assert len(findings) == 1
    assert findings[0]["level"] == "warning"
    assert "no lastChecked" in findings[0]["message"]


def test_stale_metadata_last_updated_warns_to_rebuild():
    metadata = {
        "freshnessPolicy": {"playerRatingsMaxAgeDays": 30},
        "sources": [],
        "lastUpdated": _iso(hours_ago=24 * 60),
    }
    findings = check_freshness(metadata)
    assert len(findings) == 1
    assert "rebuild_player_ratings_v2.py" in findings[0]["message"]
