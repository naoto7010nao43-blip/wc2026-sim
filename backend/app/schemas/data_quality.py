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
    notes: list[str]
