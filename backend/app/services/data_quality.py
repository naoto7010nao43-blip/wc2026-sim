"""Read-only data quality summary derived from existing seed/report files.

Nothing here mutates any seed or report file -- it only reads what
build_fifa_squad_merge_proposal.py and migrate_to_player_data_v2.py have
already written, so this is safe to call on every request.
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

from scripts.check_data_freshness import check_freshness

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

# Control characters that should never appear in JSON string values once
# decoded -- excludes \t/\n/\r, which can legitimately show up in free-text
# fields such as source citations.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _load_json(path: Path) -> object | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_report(reports_dir: Path, pattern: str) -> tuple[Path | None, dict | None]:
    if not reports_dir.exists():
        return None, None
    matches = sorted(reports_dir.glob(pattern))
    if not matches:
        return None, None
    latest = matches[-1]
    return latest, _load_json(latest)


def _count_control_character_issues(paths: list[Path]) -> int:
    issues = 0
    for path in paths:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        issues += len(_CONTROL_CHAR_RE.findall(raw))
    return issues


def _real_results_coverage(seed_dir: Path) -> dict:
    teams = _load_json(seed_dir / "teams.json") or []
    real_results_dir = seed_dir / "real_results"
    group_to_teams: dict[str, list[str]] = {}
    for team in teams:
        group_id = team.get("group_id")
        if group_id:
            group_to_teams.setdefault(group_id, []).append(team["id"])

    expected_group_matches = sum(len(list(combinations(team_ids, 2))) for team_ids in group_to_teams.values())
    real_group_matches = 0
    for group_id in group_to_teams:
        entries = _load_json(real_results_dir / f"{group_id}.json") or []
        real_group_matches += len(entries) if isinstance(entries, list) else 0

    knockout_entries = _load_json(real_results_dir / "knockout.json") or []
    real_knockout_matches = len(knockout_entries) if isinstance(knockout_entries, list) else 0

    return {
        "real_group_match_count": real_group_matches,
        "real_group_match_expected": expected_group_matches,
        "real_group_match_coverage_pct": (
            round(real_group_matches / expected_group_matches * 100, 1) if expected_group_matches else 0.0
        ),
        "real_knockout_match_count": real_knockout_matches,
    }


def _freshness_note(message: str) -> str:
    if message.startswith("FIFA Official Squad feed: stale"):
        return "公式スカッドfeedの最終確認が鮮度ポリシーを超過しています。反映済みデータは保持しつつ、公開後も再確認対象です。"
    if message.startswith("Existing project seed data"):
        return "既存seedデータ（経歴・市場価値・出典）の最終確認が鮮度ポリシーを超過しています。能力値変更前に再確認が必要です。"
    if message.startswith("metadata.lastUpdated"):
        return "seedメタデータの最終更新日が鮮度ポリシーを超過しています。"
    if "not yet integrated" in message:
        return "未連携の外部データソースがあります。現時点では参考情報として扱います。"
    return f"データ鮮度確認: {message}"


def compute_data_quality_summary(seed_dir: Path = SEED_DIR, reports_dir: Path = REPORTS_DIR) -> dict:
    notes: list[str] = []

    seed_players = _load_json(seed_dir / "players.json") or []
    seed_teams = _load_json(seed_dir / "teams.json") or []
    official_players = _load_json(seed_dir / "players2026_official.json") or []
    metadata = _load_json(seed_dir / "metadata.json") or {}

    seed_player_count = len(seed_players)
    seed_team_count = len(seed_teams)

    official_profile_players = sum(
        1 for p in official_players if p.get("caps") is not None or p.get("clubName") is not None
    )
    official_profile_coverage_pct = (
        round(official_profile_players / seed_player_count * 100, 1) if seed_player_count else 0.0
    )

    merge_path, merge_proposal = _latest_report(reports_dir, "fifa_squad_merge_proposal_*.json")
    if merge_proposal is None:
        notes.append("スカッド照合レポートが見つからないため、ロスター照合の数値は表示できません。")
        remaining_unmatched_official_players = None
        remaining_unmatched_seed_players = None
        coach_mismatch_count = None
        matched_player_field_update_candidates = None
        last_report_update = None
    else:
        remaining_unmatched_official_players = merge_proposal.get("unmatchedOfficialPlayerCount")
        remaining_unmatched_seed_players = merge_proposal.get("unmatchedSeedPlayerCount")
        coach_mismatch_count = merge_proposal.get("coachMismatchCount")
        matched_player_field_update_candidates = merge_proposal.get("matchedPlayerFieldUpdateCount")
        last_report_update = merge_proposal.get("generatedAt")

    last_seed_update = metadata.get("lastUpdated")
    real_results = _real_results_coverage(seed_dir)
    freshness_findings = check_freshness(metadata) if isinstance(metadata, dict) else []
    freshness_critical_count = sum(1 for finding in freshness_findings if finding.get("level") == "critical")
    freshness_warning_count = sum(1 for finding in freshness_findings if finding.get("level") == "warning")
    freshness_notice_count = sum(1 for finding in freshness_findings if finding.get("level") == "notice")
    freshness_status = "critical" if freshness_critical_count else "warning" if freshness_warning_count else "ok"

    control_character_issues = _count_control_character_issues(
        [
            seed_dir / "players.json",
            seed_dir / "teams.json",
            seed_dir / "players2026_official.json",
            seed_dir / "teams2026_official.json",
            seed_dir / "metadata.json",
        ]
    )
    if control_character_issues:
        notes.append(f"シードJSONファイル内に制御文字が{control_character_issues}件見つかりました。")

    if matched_player_field_update_candidates == 0:
        notes.append("公式データの反映待ち更新候補はありません。")
    if remaining_unmatched_seed_players:
        notes.append(
            f"{remaining_unmatched_seed_players}人のシード選手が公式スカッドと未対応のままです。"
        )
    if real_results["real_group_match_count"] < real_results["real_group_match_expected"]:
        notes.append(
            f"グループステージ実結果は{real_results['real_group_match_count']}/"
            f"{real_results['real_group_match_expected']}試合まで反映済みです。"
        )
    for finding in freshness_findings:
        if finding.get("level") in {"critical", "warning"}:
            notes.append(_freshness_note(finding.get("message", "")))

    return {
        "seed_player_count": seed_player_count,
        "seed_team_count": seed_team_count,
        "official_profile_players": official_profile_players,
        "official_profile_coverage_pct": official_profile_coverage_pct,
        "remaining_unmatched_official_players": remaining_unmatched_official_players,
        "remaining_unmatched_seed_players": remaining_unmatched_seed_players,
        "coach_mismatch_count": coach_mismatch_count,
        "matched_player_field_update_candidates": matched_player_field_update_candidates,
        "last_seed_update": last_seed_update,
        "last_report_update": last_report_update,
        "control_character_issues": control_character_issues,
        "freshness_status": freshness_status,
        "freshness_critical_count": freshness_critical_count,
        "freshness_warning_count": freshness_warning_count,
        "freshness_notice_count": freshness_notice_count,
        **real_results,
        "notes": notes,
    }
