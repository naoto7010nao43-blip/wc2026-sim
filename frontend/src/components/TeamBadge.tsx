import { useTeam } from "../context/useTeams";
import { countryNameJa } from "../data/countryNamesJa";

interface Props {
  teamId: string;
  showName?: boolean;
  className?: string;
}

export function TeamBadge({ teamId, showName = true, className = "" }: Props) {
  const team = useTeam(teamId);
  const name = countryNameJa(teamId, team?.name ?? teamId);

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs font-bold text-slate-100">{teamId}</span>
      {showName && <span className="text-slate-200">{name}</span>}
    </span>
  );
}
