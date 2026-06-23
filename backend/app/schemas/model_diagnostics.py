from pydantic import BaseModel


class SourceReportRef(BaseModel):
    name: str
    generatedAt: str | None = None


class TeamReviewRow(BaseModel):
    team_id: str
    team_name: str
    fifa_rank: int | None
    seed_roster_size: int | None
    attack_rating: float | None
    defense_rating: float | None
    strength_rating: float | None
    rank_underperformance_flags: int
    high_confidence_add_candidate_count: int
    other_add_candidate_count: int
    ambiguous_pair_count: int
    likely_stale_seed_player_count: int
    priority_score: float
    priority_band: str
    review_reasons: list[str]
    recommended_next_action: str


class TeamReviewSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    teamCount: int
    teams: list[TeamReviewRow]
