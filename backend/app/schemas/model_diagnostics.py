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


class ManagerTacticalTrustRow(BaseModel):
    team_id: str
    team_name: str
    fifa_rank: int | None
    default_formation: str | None
    manager_name_seed: str | None
    manager_name_official: str | None
    manager_name_official_profile: str | None
    manager_name_mismatch: bool
    manager_rating_confidence: str | None
    missing_manager_rating: bool
    has_tactical_basis: bool
    tactical_profile: dict
    duplicate_profile_team_ids: list[str]
    team_review_priority_band: str | None
    review_score: float
    review_band: str
    review_reasons: list[str]


class ManagerTacticalTrustSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    teamCount: int
    bandCounts: dict[str, int]
    teams: list[ManagerTacticalTrustRow]


class PositionGroupReviewSummary(BaseModel):
    count: int
    avg_overall: float | None
    top_player: dict | None
    is_weak_group: bool
    review_candidate_count: int


class RatingReviewCandidate(BaseModel):
    player_id: str
    name: str
    name_ja: str | None
    primary_position: str
    age: int | None
    club_name: str | None
    caps: int | None
    national_team_goals: int | None
    market_value_eur: int | None
    source_citations: list[str]
    current_overall: int | None
    position_overall: int | None
    starting_probability: int | None
    uncertainty: float | None
    data_confidence: str | None
    source_breakdown: dict
    low_confidence_attributes: list[str]
    qualitative_adjustments: dict
    review_score: float
    review_band: str
    review_flags: list[str]
    review_summary_ja: list[str]
    suggested_codex_action: str


class RatingReviewTeamRow(BaseModel):
    team_id: str
    team_name: str
    fifa_rank: int | None
    squad_gap_priority_score: float | None
    rank_underperformance_flags: int
    recommended_next_action: str | None
    position_group_summary: dict[str, PositionGroupReviewSummary]
    rating_review_candidates: list[RatingReviewCandidate]


class RatingReviewWorkbenchSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    teamCount: int
    teams: list[RatingReviewTeamRow]
