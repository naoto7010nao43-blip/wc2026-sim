export interface PlayerSummary {
  id: string;
  name: string;
  name_ja: string | null;
  age: number;
  primary_position: string;
  overall: number;
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
