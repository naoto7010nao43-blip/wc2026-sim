import { useTeam } from "../context/useTeams";
import { countryNameJa } from "../data/countryNamesJa";
import { flagUrl } from "../data/teamFlags";

interface Props {
  teamId: string;
  showName?: boolean;
  className?: string;
}

export function TeamBadge({ teamId, showName = true, className = "" }: Props) {
  const team = useTeam(teamId);
  const name = countryNameJa(teamId, team?.name ?? teamId);
  const flag = flagUrl(teamId);

  return (
    <span className={`inline-flex min-w-0 items-center gap-1.5 ${className}`}>
      {flag ? (
        <img
          src={flag}
          srcSet={`${flagUrl(teamId, 80)} 2x`}
          alt=""
          width={20}
          height={14}
          loading="lazy"
          className="h-[14px] w-5 shrink-0 rounded-[2px] object-cover ring-1 ring-white/15"
        />
      ) : (
        <span className="shrink-0 rounded bg-slate-700 px-1.5 py-0.5 font-display text-[11px] font-bold text-slate-100">
          {teamId}
        </span>
      )}
      {showName && <span className="truncate text-slate-200">{name}</span>}
    </span>
  );
}
