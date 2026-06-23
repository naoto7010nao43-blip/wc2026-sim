export interface SourceBreakdown {
  officialRoster: boolean;
  marketValueUsed: boolean;
  clubMinutesUsed: boolean;
  nationalTeamMinutesUsed: boolean;
  injuryDataUsed: boolean;
  manualOverrideUsed: boolean;
}

export interface PlayerSummary {
  id: string;
  name: string;
  name_ja: string | null;
  age: number;
  primary_position: string;
  overall: number;
  // Rating trust/provenance metadata -- absent (null/[]) for players
  // seeded before this metadata existed, never fabricated client-side.
  starting_probability: number | null;
  data_confidence: string | null;
  uncertainty: number | null;
  source_breakdown: SourceBreakdown | null;
  low_confidence_attributes: string[];
  rating_last_updated: string | null;
  date_of_birth: string | null;
  height_cm: number | null;
  club_name: string | null;
  caps: number | null;
  national_team_goals: number | null;
}

export interface TacticalProfile {
  manager_name: string;
  press_intensity: number;
  possession_style: number;
  defensive_line_height: number;
}

export interface TeamSummary {
  id: string;
  name: string;
  confederation: string;
  fifa_rank: number | null;
  default_formation: string;
  group_id: string | null;
  tactical_profile: TacticalProfile | null;
}

export interface TeamOut extends TeamSummary {
  players: PlayerSummary[];
}

export interface LikelyLineupSlot {
  slot_position: string;
  player_id: string;
  name: string;
  name_ja: string | null;
  primary_position: string;
  starting_probability: number;
}

export interface LikelyLineupOut {
  team_id: string;
  formation: string;
  lineup: LikelyLineupSlot[];
  disclaimer: string;
}

export interface TournamentSimulationOut {
  iterations: number;
  model_version: string;
  round_of_32_pct: Record<string, number>;
  round_of_16_pct: Record<string, number>;
  quarterfinal_pct: Record<string, number>;
  semifinal_pct: Record<string, number>;
  final_pct: Record<string, number>;
  champion_pct: Record<string, number>;
  data_confidence?: string;
  explanation?: string[];
  disclaimer: string;
}

export interface MatchPredictionOut {
  home_team_id: string;
  away_team_id: string;
  home_win_pct: number;
  draw_pct: number;
  away_win_pct: number;
  home_expected_goals: number;
  away_expected_goals: number;
  most_likely_scores: [number, number, number][];
  data_confidence: string;
  explanation: string[];
  model_version: string;
  disclaimer: string;
}

export interface MatchEvent {
  minute: number;
  event_type: string;
  team_id: string;
  player_id: string | null;
  secondary_player_id: string | null;
  x: number | null;
  y: number | null;
  description: string;
  event_metadata: Record<string, unknown> | null;
}

export type RoundName = "group" | "R32" | "R16" | "QF" | "SF" | "THIRD_PLACE" | "FINAL";

export interface MatchSummary {
  id: string;
  group_id: string | null;
  round: RoundName;
  bracket_slot: string | null;
  home_team_id: string;
  away_team_id: string;
  home_score: number;
  away_score: number;
  went_to_penalties: boolean;
  penalty_home_score: number | null;
  penalty_away_score: number | null;
  status: string;
  played_at: string;
  is_real: boolean;
  data_source: string | null;
}

export interface LineupPlayer {
  player_id: string;
  name: string;
  slot_position: string;
  x: number;
  y: number;
}

export interface PlayerRating {
  player_id: string;
  name: string;
  team_id: string;
  rating: number;
  is_mom: boolean;
  is_estimated: boolean;
}

export interface TurningPoint {
  minute: number;
  team_id: string;
  description: string;
}

export interface MomentumSegment {
  start_minute: number;
  end_minute: number;
  home_actions: number;
  away_actions: number;
  dominant_team_id: string | null;
}

export interface KeyPlayerContribution {
  player_id: string;
  name: string;
  team_id: string;
  rating: number;
  is_mom: boolean;
}

export interface MatchAnalysis {
  turning_point: TurningPoint | null;
  momentum_segments: MomentumSegment[];
  key_players: KeyPlayerContribution[];
  tactical_note: string;
}

export interface MatchResult extends MatchSummary {
  home_formation: string;
  away_formation: string;
  home_lineup: LineupPlayer[];
  away_lineup: LineupPlayer[];
  seed: number | null;
  events: MatchEvent[];
  home_possession_pct: number | null;
  away_possession_pct: number | null;
  home_shots: number | null;
  away_shots: number | null;
  home_shots_on_target: number | null;
  away_shots_on_target: number | null;
  home_yellow_cards: number | null;
  away_yellow_cards: number | null;
  home_red_cards: number | null;
  away_red_cards: number | null;
  player_ratings: PlayerRating[];
  analysis: MatchAnalysis | null;
}

export interface StandingsRow {
  team_id: string;
  team_name: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
}

export interface RoundRobinResult {
  matches: MatchSummary[];
  standings: StandingsRow[];
}

export interface TournamentResult {
  champion_team_id: string | null;
  qualifying_third_groups: string[] | null;
  matches: Record<RoundName, MatchSummary[]>;
  group_standings: Record<string, StandingsRow[]>;
}

export interface SourceReportRef {
  name: string;
  generatedAt: string | null;
}

export interface TeamReviewRow {
  team_id: string;
  team_name: string;
  fifa_rank: number | null;
  seed_roster_size: number | null;
  attack_rating: number | null;
  defense_rating: number | null;
  strength_rating: number | null;
  rank_underperformance_flags: number;
  high_confidence_add_candidate_count: number;
  other_add_candidate_count: number;
  ambiguous_pair_count: number;
  likely_stale_seed_player_count: number;
  priority_score: number;
  priority_band: "high" | "medium" | "low";
  review_reasons: string[];
  recommended_next_action: string;
}

export interface TeamReviewSummary {
  generatedAt: string | null;
  sourceReports: SourceReportRef[];
  note: string;
  teamCount: number;
  teams: TeamReviewRow[];
}

export interface PositionGroupSummary {
  count: number;
  avg_overall: number | null;
  avg_starting_probability: number | null;
  top_player: { name: string; overall: number } | null;
}

export interface RatingDistribution {
  min_overall: number | null;
  median_overall: number | null;
  max_overall: number | null;
  top_5_players: { name: string; overall: number }[];
  count_overall_gte_75: number;
  count_overall_gte_70: number;
  count_overall_lt_60: number;
}

export interface SquadTrustProfile {
  data_confidence_counts: Record<string, number>;
  average_uncertainty: number | null;
  low_confidence_attribute_count: number;
  official_profile_coverage: Record<string, number>;
}

export interface RosterReconciliationSummary {
  high_confidence_add_candidate_count: number;
  other_add_candidate_count: number;
  ambiguous_pair_count: number;
  likely_stale_seed_player_count: number;
  top_ambiguous_pairs: { seed_player_name: string; official_candidate_name_block: string; shared_token_count: number }[];
}

export interface SquadGapTeamRow {
  team_id: string;
  team_name: string;
  fifa_rank: number | null;
  priority_score: number | null;
  rank_underperformance_flags: number;
  seed_roster_size: number | null;
  position_groups: Record<string, PositionGroupSummary>;
  rating_distribution: RatingDistribution;
  trust_profile: SquadTrustProfile;
  roster_reconciliation: RosterReconciliationSummary;
  diagnostic_flags: string[];
  review_summary_ja: string[];
  recommended_next_action: string;
}

export interface SquadGapSummary {
  generatedAt: string | null;
  sourceReports: SourceReportRef[];
  note: string;
  teams: SquadGapTeamRow[];
}

export interface ManagerTacticalTrustRow {
  team_id: string;
  team_name: string;
  fifa_rank: number | null;
  default_formation: string | null;
  manager_name_seed: string | null;
  manager_name_official: string | null;
  manager_name_official_profile: string | null;
  manager_name_mismatch: boolean;
  manager_rating_confidence: string | null;
  missing_manager_rating: boolean;
  has_tactical_basis: boolean;
  tactical_profile: { press_intensity: number | null; possession_style: number | null; defensive_line_height: number | null };
  duplicate_profile_team_ids: string[];
  team_review_priority_band: string | null;
  review_score: number;
  review_band: "high" | "medium" | "low";
  review_reasons: string[];
}

export interface ManagerTacticalTrustSummary {
  generatedAt: string | null;
  sourceReports: SourceReportRef[];
  note: string;
  teamCount: number;
  bandCounts: Record<string, number>;
  teams: ManagerTacticalTrustRow[];
}

export interface PositionGroupReviewSummary {
  count: number;
  avg_overall: number | null;
  top_player: { name: string; overall: number } | null;
  is_weak_group: boolean;
  review_candidate_count: number;
}

export interface RatingReviewCandidate {
  player_id: string;
  name: string;
  name_ja: string | null;
  primary_position: string;
  age: number | null;
  club_name: string | null;
  caps: number | null;
  national_team_goals: number | null;
  market_value_eur: number | null;
  source_citations: string[];
  current_overall: number | null;
  position_overall: number | null;
  starting_probability: number | null;
  uncertainty: number | null;
  data_confidence: string | null;
  source_breakdown: Record<string, boolean>;
  low_confidence_attributes: string[];
  qualitative_adjustments: Record<string, number>;
  review_score: number;
  review_band: "high" | "medium" | "low";
  review_flags: string[];
  review_summary_ja: string[];
  suggested_codex_action: string;
}

export interface RatingReviewTeamRow {
  team_id: string;
  team_name: string;
  fifa_rank: number | null;
  squad_gap_priority_score: number | null;
  rank_underperformance_flags: number;
  recommended_next_action: string | null;
  position_group_summary: Record<string, PositionGroupReviewSummary>;
  rating_review_candidates: RatingReviewCandidate[];
}

export interface RatingReviewWorkbenchSummary {
  generatedAt: string | null;
  sourceReports: SourceReportRef[];
  note: string;
  teamCount: number;
  teams: RatingReviewTeamRow[];
}

export interface DataQualitySummary {
  seed_player_count: number;
  seed_team_count: number;
  official_profile_players: number;
  official_profile_coverage_pct: number;
  remaining_unmatched_official_players: number | null;
  remaining_unmatched_seed_players: number | null;
  coach_mismatch_count: number | null;
  matched_player_field_update_candidates: number | null;
  last_seed_update: string | null;
  last_report_update: string | null;
  control_character_issues: number;
  notes: string[];
}
