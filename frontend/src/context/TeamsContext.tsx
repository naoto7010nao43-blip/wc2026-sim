import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { TeamSummary } from "../types/domain";

const TeamsContext = createContext<Record<string, TeamSummary>>({});

export function TeamsProvider({ children }: { children: ReactNode }) {
  const [teamsById, setTeamsById] = useState<Record<string, TeamSummary>>({});

  useEffect(() => {
    api.listTeams().then((teams) => {
      const byId: Record<string, TeamSummary> = {};
      for (const t of teams) byId[t.id] = t;
      setTeamsById(byId);
    });
  }, []);

  return <TeamsContext.Provider value={teamsById}>{children}</TeamsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- small hook colocated with its provider; splitting into a separate file is out of scope for this fix
export function useTeamsMap(): Record<string, TeamSummary> {
  return useContext(TeamsContext);
}

// eslint-disable-next-line react-refresh/only-export-components -- see above
export function useTeam(teamId: string | null | undefined): TeamSummary | undefined {
  const teamsById = useTeamsMap();
  return teamId ? teamsById[teamId] : undefined;
}
