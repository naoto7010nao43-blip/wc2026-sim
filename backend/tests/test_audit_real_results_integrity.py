import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_real_results_integrity as audit


def test_real_results_integrity_passes_current_seed_data():
    assert audit.audit_real_results_integrity() == []


def test_group_audit_flags_missing_round_robin_fixture(monkeypatch, tmp_path):
    real_results = tmp_path / "real_results"
    real_results.mkdir()
    for group in audit.GROUPS:
        source = audit.REAL_RESULTS_DIR / f"{group}.json"
        entries = json.loads(source.read_text(encoding="utf-8"))
        if group == "A":
            entries = entries[:-1]
        (real_results / f"{group}.json").write_text(json.dumps(entries), encoding="utf-8")

    monkeypatch.setattr(audit, "REAL_RESULTS_DIR", real_results)

    findings = audit.audit_group_results()

    assert any(f.scope == "group A" and "expected 6 matches" in f.message for f in findings)
    assert any(f.scope == "group A" and "missing fixture pairs" in f.message for f in findings)


def test_score_goal_mismatch_is_reported():
    entry = {
        "home_team_id": "AAA",
        "away_team_id": "BBB",
        "home_score": 2,
        "away_score": 0,
        "date": "2026-06-11",
        "goals": [{"minute": 10, "team_id": "AAA", "scorer_name": "One Goal"}],
    }

    findings = audit._check_score_and_goals("fixture", entry)

    assert any("home goals list has 1 goals but score is 2" in f.message for f in findings)


def test_knockout_draw_requires_penalty_winner(monkeypatch, tmp_path):
    real_results = tmp_path / "real_results"
    real_results.mkdir()
    (real_results / "knockout.json").write_text(json.dumps([
        {
            "round": "R32",
            "home_team_id": "BRA",
            "away_team_id": "JPN",
            "home_score": 1,
            "away_score": 1,
            "date": "2026-06-29",
            "goals": [
                {"minute": 10, "team_id": "BRA", "scorer_name": "Home"},
                {"minute": 20, "team_id": "JPN", "scorer_name": "Away"},
            ],
        }
    ]), encoding="utf-8")

    monkeypatch.setattr(audit, "REAL_RESULTS_DIR", real_results)
    monkeypatch.setattr(audit, "_audit_knockout_entries_are_used", lambda entries: [])

    findings = audit.audit_knockout_results()

    assert any("drawn knockout match" in f.message for f in findings)
