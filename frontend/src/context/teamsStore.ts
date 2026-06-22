import { createContext } from "react";
import type { TeamSummary } from "../types/domain";

export const TeamsContext = createContext<Record<string, TeamSummary>>({});
