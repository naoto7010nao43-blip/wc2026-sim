from pydantic import BaseModel


class SourceReportRef(BaseModel):
    name: str
    generatedAt: str | None = None


class ReleaseCurrentTaskState(BaseModel):
    hasActiveReadyTask: bool
    awaitingNextSpec: bool
    latestCompletedSpecText: str | None


class ReleaseModelVersions(BaseModel):
    baselineModelVersion: str | None
    currentModelVersion: str | None


class ReleaseBenchmarkSummary(BaseModel):
    present: bool
    path: str | None = None
    status: str | None
    benchmarkMethod: str | None = None
    watchlistImplausibleReduction: float | None
    overallImplausibleFavoriteCountDelta: float | None
    averageFavoriteWinPctDelta: float | None


class ReleaseRequiredReport(BaseModel):
    pattern: str
    present: bool
    path: str | None


class ReleaseReadinessSummary(BaseModel):
    generatedAt: str | None
    note: str
    readyForManualPush: bool
    blockers: list[str]
    currentTask: ReleaseCurrentTaskState | None
    gitStatusShort: list[str]
    modelVersions: ReleaseModelVersions | None
    rank75Benchmark: ReleaseBenchmarkSummary | None
    requiredReports: list[ReleaseRequiredReport]
    requiredCommands: list[str]


class ExternalDataScope(BaseModel):
    coveredTeams: list[str]
    remainingUnresearchedTeams: list[str]


class ExternalTeamPriority(BaseModel):
    teamId: str
    priorityScore: float
    highImpactCandidateCount: int
    mediumImpactCandidateCount: int
    futureEngineCandidateCount: int


class ExternalTeamSignalProfile(BaseModel):
    teamId: str
    signalBand: str
    candidateCount: int
    categoryCounts: dict[str, int]
    useTierCounts: dict[str, int]
    existingFieldCandidateCount: int
    futureEngineCandidateCount: int
    preservedReviewQuestionCount: int


class ExternalDataDecisionQueueTeam(BaseModel):
    teamId: str
    teamName: str | None
    candidateCount: int
    bucketCounts: dict[str, int]
    currentFieldReviewCount: int
    warningHoldCount: int
    futureEngineCount: int
    reviewScore: float


class ExternalDataDecisionQueueSummary(BaseModel):
    generatedAt: str | None
    currentFieldReviewCount: int
    warningHoldCount: int
    futureEngineCount: int
    provisionalContextCount: int
    bucketCounts: dict[str, int]
    topTeams: list[ExternalDataDecisionQueueTeam]


class ExternalDataVerificationSummary(BaseModel):
    generatedAt: str | None
    note: str
    valid: bool
    errorCount: int
    warningCount: int
    candidateCount: int
    coveredTeamCount: int
    totalTeamCount: int
    remainingTeamCount: int
    scope: ExternalDataScope | None
    categoryCounts: dict[str, int]
    impactCounts: dict[str, int]
    useTierCounts: dict[str, int]
    teamSignalBandCounts: dict[str, int]
    sparseTeamIds: list[str]
    topTeamPriorities: list[ExternalTeamPriority]
    teamSignalProfiles: list[ExternalTeamSignalProfile]
    decisionQueue: ExternalDataDecisionQueueSummary | None
    warnings: list[str]
    errors: list[str]


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


class RatingDecisionCandidate(BaseModel):
    player_id: str
    name: str
    primary_position: str | None
    current_overall: int | None
    review_score: float | None
    review_band: str | None
    suggested_codex_action: str | None
    review_flags: list[str]
    source_risk_flags: list[str]
    driver_alignment: bool
    counterproductive_for_team_underperformance: bool
    decision_bucket: str


class RatingDecisionTeamRow(BaseModel):
    team_id: str
    team_name: str
    dominant_negative_driver: str
    rank_underperformance_flags: int | None
    bucketCounts: dict[str, int]
    candidate_for_later_proposal: list[RatingDecisionCandidate]
    source_review_first: list[RatingDecisionCandidate]
    do_not_use_for_upgrade_proposal: list[RatingDecisionCandidate]
    monitor_only: list[RatingDecisionCandidate]


class RatingDecisionAuditSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    teamCount: int
    bucketCounts: dict[str, int]
    teams: list[RatingDecisionTeamRow]


class ModelCalibrationOverall(BaseModel):
    before_matchup_count: int
    after_matchup_count: int
    average_favorite_win_pct_delta: float
    implausible_favorite_count_delta: float
    minimum_favorite_win_pct_delta: float
    maximum_favorite_win_pct_delta: float


class ModelCalibrationWatchlistTeam(BaseModel):
    team_id: str
    average_favorite_win_pct_delta: float | None
    implausible_favorite_count_delta: float | None
    minimum_favorite_win_pct_delta: float | None


class ModelCalibrationWatchlist(BaseModel):
    watchlist_implausible_reduction: float | None
    teams: list[ModelCalibrationWatchlistTeam]


class ModelCalibrationSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    modelVersionBefore: str | None
    modelVersionAfter: str | None
    status: str | None
    benchmarkMethod: str | None
    overall: ModelCalibrationOverall | None
    watchlist: ModelCalibrationWatchlist | None
    bestSandboxVariantId: str | None
    note: str
    recommendations_ja: list[str]


class SimulationStabilityChampionCandidate(BaseModel):
    team_id: str
    pct: float


class SimulationStabilitySample(BaseModel):
    iterations: int
    modelVersion: str | None
    dataConfidence: str | None
    championCandidateCount: int
    topChampionCandidates: list[SimulationStabilityChampionCandidate]
    topChampionTeamId: str | None
    topChampionPct: float | None
    topThreeChampionPct: float


class SimulationStabilityMover(BaseModel):
    team_id: str
    previous_pct: float
    current_pct: float
    delta_pct: float
    abs_delta_pct: float


class SimulationStabilityComparison(BaseModel):
    fromIterations: int
    toIterations: int
    stabilityBand: str
    max_abs_delta_pct: float
    average_abs_delta_pct: float
    largest_movers: list[SimulationStabilityMover]


class SimulationStabilityResult(BaseModel):
    stabilityBand: str
    maxAbsChampionPctDelta: float
    averageAbsChampionPctDelta: float
    recommendation: str
    recommendation_ja: str


class SimulationStabilityScope(BaseModel):
    iterationCounts: list[int]
    baseSeed: int
    sampleCount: int


class SimulationStabilitySummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    modelVersion: str | None
    note: str
    scope: SimulationStabilityScope | None
    samples: list[SimulationStabilitySample]
    comparisons: list[SimulationStabilityComparison]
    summary: SimulationStabilityResult | None


class SubstitutionEngineCapabilities(BaseModel):
    hasSubstitutionEvents: bool
    hasManagerSpecificSubstitutionParameters: bool
    hasScoreStateSubstitutionBias: bool
    hasPositionSpecificSubstitutionPreferences: bool
    maxSubs: int
    subWindow: dict
    subChancePerMinute: float
    subFatigueGap: float
    selectionRule: str


class SubstitutionModelGap(BaseModel):
    gapId: str
    label: str
    currentBehavior: str
    precisionRiskJa: str
    futureFieldCandidates: list[str]
    evidenceNeededJa: str
    recommendedNextAction: str


class SubstitutionModelGapSummaryState(BaseModel):
    currentModelHasManagerSpecificSubstitutions: bool
    dataResearchCanBeStored: bool
    safeCurrentAction: str
    recommendedNextSpec: str


class SubstitutionModelGapSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    engineCapabilities: SubstitutionEngineCapabilities | None
    gapCount: int
    gaps: list[SubstitutionModelGap]
    recommendationsJa: list[str]
    summary: SubstitutionModelGapSummaryState | None


class SourceRiskFlag(BaseModel):
    marker: str
    severity: str
    reason_ja: str


class SourceRiskPlayer(BaseModel):
    team_id: str | None
    player_id: str | None
    name: str | None
    risk_score: int
    risk_flags: list[SourceRiskFlag]
    source_citations: list[str]


class SeedSourceSummary(BaseModel):
    seed_player_count: int
    players_with_source_risk: int
    marker_counts: dict[str, int]
    severity_counts: dict[str, int]
    top_risky_seed_players: list[SourceRiskPlayer]


class SourceProvenanceCandidate(BaseModel):
    player_id: str
    name: str
    primary_position: str | None
    current_overall: int | None
    decision_bucket: str
    suggested_codex_action: str | None
    risk_score: int
    risk_flags: list[SourceRiskFlag]
    source_citations: list[str]


class SourceProvenanceTeamRow(BaseModel):
    team_id: str
    team_name: str
    candidate_count: int
    source_risk_candidate_count: int
    decision_bucket_counts: dict[str, int]
    clear_later_proposal_candidates: list[SourceProvenanceCandidate]
    source_review_candidates: list[SourceProvenanceCandidate]


class SourceProvenanceAuditSummary(BaseModel):
    generatedAt: str | None
    sourceReports: list[SourceReportRef]
    note: str
    seedSourceSummary: SeedSourceSummary
    decisionCandidateCount: int
    clearLaterProposalCandidateCount: int
    sourceReviewCandidateCount: int
    teamCount: int
    teams: list[SourceProvenanceTeamRow]
    recommendations_ja: list[str]
