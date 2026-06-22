import { useContext } from "react";
import { TeamsContext } from "./teamsStore";
import type { TeamSummary } from "../types/domain";

export function useTeamsMap(): Record<string, TeamSummary> {
  return useContext(TeamsContext);
}

export function useTeam(teamId: string | null | undefined): TeamSummary | undefined {
  const teamsById = useTeamsMap();
  return teamId ? teamsById[teamId] : undefined;
}
