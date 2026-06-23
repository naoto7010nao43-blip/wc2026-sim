"""Read-only data quality summary derived from existing seed/report files.

Nothing here mutates any seed or report file -- it only reads what
build_fifa_squad_merge_proposal.py and migrate_to_player_data_v2.py have
already written, so this is safe to call on every request.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

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
        "notes": notes,
    }
