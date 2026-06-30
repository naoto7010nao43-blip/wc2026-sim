from pydantic import BaseModel


class DataQualitySummary(BaseModel):
    seed_player_count: int
    seed_team_count: int
    official_profile_players: int
    official_profile_coverage_pct: float
    remaining_unmatched_official_players: int | None
    remaining_unmatched_seed_players: int | None
    coach_mismatch_count: int | None
    matched_player_field_update_candidates: int | None
    last_seed_update: str | None
    last_report_update: str | None
    control_character_issues: int
    freshness_status: str
    freshness_critical_count: int
    freshness_warning_count: int
    freshness_notice_count: int
    real_group_match_count: int
    real_group_match_expected: int
    real_group_match_coverage_pct: float
    real_knockout_match_count: int
    notes: list[str]
