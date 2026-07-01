import type {
  DataQualitySummary,
  ExternalDataVerificationSummary,
  FormationPositionFitAuditSummary,
  LikelyLineupOut,
  LineupEngineParityAuditSummary,
  MatchupBreakdownOut,
  ManagerTacticalTrustSummary,
  MatchPredictionOut,
  MatchResult,
  ModelCalibrationSummary,
  PlayerRatingDiffSummary,
  RatingDecisionAuditSummary,
  RatingReviewWorkbenchSummary,
  ReleaseReadinessSummary,
  SimulationStabilitySummary,
  RoundRobinResult,
  SourceProvenanceAuditSummary,
  SquadGapSummary,
  SubstitutionModelGapSummary,
  SubstitutionProfileCandidateQueueSummary,
  StandingsRow,
  TeamOut,
  TeamReviewSummary,
  TeamSummary,
  TournamentResult,
  TournamentGroupDifficultyOut,
  TournamentPathProjectionOut,
  TournamentSimulationOut,
  TournamentUpsetWatchOut,
} from "../types/domain";

function defaultApiBaseUrl(): string {
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl();

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  listTeams: () => getJson<TeamSummary[]>("/api/teams"),
  getTeam: (teamId: string) => getJson<TeamOut>(`/api/teams/${teamId}`),
  getLikelyLineup: (teamId: string) => getJson<LikelyLineupOut>(`/api/teams/${teamId}/likely-lineup`),
  getMatchPrediction: (homeTeamId: string, awayTeamId: string) =>
    getJson<MatchPredictionOut>(`/api/predictions/${homeTeamId}/${awayTeamId}`),
  getMatchupBreakdown: (homeTeamId: string, awayTeamId: string) =>
    getJson<MatchupBreakdownOut>(`/api/predictions/${homeTeamId}/${awayTeamId}/breakdown`),
  getMatch: (matchId: string) => getJson<MatchResult>(`/api/matches/${matchId}`),
  simulateMatch: (homeTeamId: string, awayTeamId: string, opts?: { seed?: number; allowDraw?: boolean }) =>
    postJson<MatchResult>("/api/matches/simulate", {
      home_team_id: homeTeamId,
      away_team_id: awayTeamId,
      seed: opts?.seed,
      allow_draw: opts?.allowDraw ?? true,
    }),
  getGroupMatches: (groupId: string) => getJson<MatchResult[]>(`/api/groups/${groupId}/matches`),
  getStandings: (groupId: string) => getJson<StandingsRow[]>(`/api/groups/${groupId}/standings`),
  simulateRoundRobin: (groupId: string, teamIds: string[], seed?: number) =>
    postJson<RoundRobinResult>(`/api/groups/${groupId}/simulate-round-robin`, { team_ids: teamIds, seed }),
  runTournament: () => postJson<TournamentResult>("/api/tournament/run", {}),
  getTournamentState: () => getJson<TournamentResult | null>("/api/tournament/state"),
  simulateTournamentMonteCarlo: (opts?: { iterations?: number; seed?: number }) =>
    postJson<TournamentSimulationOut>("/api/tournament/simulate-monte-carlo", {
      iterations: opts?.iterations ?? 1000,
      seed: opts?.seed ?? 0,
    }),
  getTournamentUpsetWatch: (limit?: number) =>
    getJson<TournamentUpsetWatchOut>(`/api/tournament/upset-watch${limit ? `?limit=${limit}` : ""}`),
  getTournamentGroupDifficulty: () => getJson<TournamentGroupDifficultyOut>("/api/tournament/group-difficulty"),
  getTournamentPathProjection: (teamId: string, opts?: { iterations?: number; seed?: number }) =>
    getJson<TournamentPathProjectionOut>(
      `/api/tournament/path-projection?team_id=${encodeURIComponent(teamId)}&iterations=${opts?.iterations ?? 1000}&seed=${opts?.seed ?? 0}`,
    ),
  getDataQualitySummary: () => getJson<DataQualitySummary>("/api/data-quality/summary"),
  getReleaseReadinessSummary: () => getJson<ReleaseReadinessSummary>("/api/model-diagnostics/release-readiness"),
  getExternalDataVerificationSummary: () =>
    getJson<ExternalDataVerificationSummary>("/api/model-diagnostics/external-data-verification"),
  getTeamDataReview: () => getJson<TeamReviewSummary>("/api/model-diagnostics/team-review"),
  getSquadGapReview: () => getJson<SquadGapSummary>("/api/model-diagnostics/squad-gaps"),
  getManagerTacticalTrust: () => getJson<ManagerTacticalTrustSummary>("/api/model-diagnostics/manager-tactical-trust"),
  getRatingReviewWorkbench: () => getJson<RatingReviewWorkbenchSummary>("/api/model-diagnostics/rating-review-workbench"),
  getRatingDecisionAudit: () => getJson<RatingDecisionAuditSummary>("/api/model-diagnostics/rating-decision-audit"),
  getPlayerRatingDiffSummary: () => getJson<PlayerRatingDiffSummary>("/api/model-diagnostics/player-rating-diff"),
  getSourceProvenanceAudit: () => getJson<SourceProvenanceAuditSummary>("/api/model-diagnostics/source-provenance-audit"),
  getModelCalibrationSummary: () => getJson<ModelCalibrationSummary>("/api/model-diagnostics/model-calibration"),
  getSimulationStabilitySummary: () => getJson<SimulationStabilitySummary>("/api/model-diagnostics/simulation-stability"),
  getSubstitutionModelGapSummary: () => getJson<SubstitutionModelGapSummary>("/api/model-diagnostics/substitution-model-gap"),
  getSubstitutionProfileCandidates: () =>
    getJson<SubstitutionProfileCandidateQueueSummary>("/api/model-diagnostics/substitution-profile-candidates"),
  getFormationPositionFitAudit: () =>
    getJson<FormationPositionFitAuditSummary>("/api/model-diagnostics/formation-position-fit"),
  getLineupEngineParityAudit: () =>
    getJson<LineupEngineParityAuditSummary>("/api/model-diagnostics/lineup-engine-parity"),
};
