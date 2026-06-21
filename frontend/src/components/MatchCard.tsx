import { Link } from "react-router-dom";
import type { MatchSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  match: MatchSummary;
  className?: string;
}

export function MatchCard({ match, className = "" }: Props) {
  const homeWon = match.home_score > match.away_score;
  const awayWon = match.away_score > match.home_score;
  const played = match.status === "completed";

  const isReal = played && match.is_real;

  return (
    <Link
      to={`/matches/${match.id}`}
      className={`block rounded-lg border-l-4 px-3 py-2 text-sm transition hover:bg-slate-700 ${
        isReal
          ? "border-l-amber-400 border border-amber-500/40 bg-amber-950/20 hover:border-amber-400"
          : "border-l-slate-600 border border-slate-700 bg-slate-800 hover:border-emerald-500"
      } ${className}`}
    >
      <div className={`flex items-center justify-between gap-2 ${homeWon ? "font-bold text-slate-100" : "text-slate-300"}`}>
        <TeamBadge teamId={match.home_team_id} />
        <span>{played ? match.home_score : "-"}</span>
      </div>
      <div className={`mt-1 flex items-center justify-between gap-2 ${awayWon ? "font-bold text-slate-100" : "text-slate-300"}`}>
        <TeamBadge teamId={match.away_team_id} />
        <span>{played ? match.away_score : "-"}</span>
      </div>
      {match.went_to_penalties && (
        <div className="mt-1 text-xs text-amber-400">
          PK {match.penalty_home_score}-{match.penalty_away_score}
        </div>
      )}
      {played && (
        <div className="mt-1 flex items-center gap-1">
          {isReal ? (
            <span className="flex items-center gap-1 rounded bg-amber-500/25 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
              ⚽ 実結果
            </span>
          ) : (
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">シミュレーション</span>
          )}
        </div>
      )}
    </Link>
  );
}
