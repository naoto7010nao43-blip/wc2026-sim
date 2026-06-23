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


class PositionGroupSummary(BaseModel):
    count: int
    avg_overall: float | None
    avg_starting_probability: float | None
    top_player: dict | None


class RatingDistribution(BaseModel):
    min_overall: int | None
    median_overall: float | None
    max_overall: int | None
    top_5_players: list[dict]
    count_overall_gte_75: int
    count_overall_gte_70: int
    count_overall_lt_60: int


class TrustProfile(BaseModel):
    data_confidence_counts: dict[str, int]
    average_uncertainty: float | None
    low_confidence_attribute_count: int
    official_profile_coverage: dict[str, int]


class RosterReconciliationSummary(BaseModel):
    high_confidence_add_candidate_count: int
    other_add_candidate_count: int
    ambiguous_pair_count: int
    likely_stale_seed_player_count: int
    top_ambiguous_pairs: list[dict]


class SquadGapTeamRow(BaseModel):
    team_id: str
    team_name: str
    fifa_rank: int | None
    priority_score: float | None
    rank_underperformance_flags: int
    seed_roster_size: int | None
    position_groups: dict[str, PositionGroupSummary]
    rating_distribution: RatingDistribution
    trust_profile: TrustProfile
    roster_reconciliation: RosterReconciliationSummary
    diagnostic_flags: list[str]
    review_summary_ja: list[str]
    recommended_next_action: str


class SquadGapSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    teams: list[SquadGapTeamRow]
