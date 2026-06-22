import { useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { TeamsContext } from "./teamsStore";
import type { TeamSummary } from "../types/domain";

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
