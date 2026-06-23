import type {
  DataQualitySummary,
  LikelyLineupOut,
  MatchPredictionOut,
  MatchResult,
  RoundRobinResult,
  StandingsRow,
  TeamOut,
  TeamReviewSummary,
  TeamSummary,
  TournamentResult,
  TournamentSimulationOut,
} from "../types/domain";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
      iterations: opts?.iterations ?? 500,
      seed: opts?.seed ?? 0,
    }),
  getDataQualitySummary: () => getJson<DataQualitySummary>("/api/data-quality/summary"),
  getTeamDataReview: () => getJson<TeamReviewSummary>("/api/model-diagnostics/team-review"),
};
