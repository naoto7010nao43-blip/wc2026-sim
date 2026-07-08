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
      className={`group block overflow-hidden rounded-lg border transition ${
        isReal
          ? "border-amber-500/45 bg-gradient-to-b from-amber-950/45 to-slate-800/60 hover:border-amber-400"
          : "border-slate-700 bg-slate-800/70 hover:border-emerald-500 hover:bg-slate-800"
      } ${className}`}
    >
      <div className="px-2.5 py-2">
        <TeamRow teamId={match.home_team_id} score={match.home_score} played={played} won={homeWon} />
        <div className="mt-1.5">
          <TeamRow teamId={match.away_team_id} score={match.away_score} played={played} won={awayWon} />
        </div>
      </div>
      {(match.went_to_penalties || played) && (
        <div className="flex items-center justify-between gap-2 border-t border-white/5 bg-slate-900/50 px-2.5 py-1">
          {played ? (
            isReal ? (
              <span className="text-[10px] font-bold tracking-wider text-amber-300">実結果</span>
            ) : (
              <span className="text-[10px] tracking-wider text-slate-500">SIM</span>
            )
          ) : (
            <span />
          )}
          {match.went_to_penalties && (
            <span className="score-num text-[11px] text-amber-300">
              PK {match.penalty_home_score}–{match.penalty_away_score}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}

function TeamRow({ teamId, score, played, won }: { teamId: string; score: number; played: boolean; won: boolean }) {
  return (
    <div className={`flex items-center justify-between gap-2 text-sm ${won ? "text-slate-100" : "text-slate-300"}`}>
      <span className={`flex min-w-0 items-center gap-1.5 ${won ? "font-bold" : ""}`}>
        <TeamBadge teamId={teamId} />
      </span>
      <span
        className={`score-num shrink-0 rounded px-1.5 py-0.5 text-base ${
          played
            ? won
              ? "bg-emerald-500/20 text-emerald-300"
              : "text-slate-300"
            : "text-slate-600"
        }`}
      >
        {played ? score : "–"}
      </span>
    </div>
  );
}
