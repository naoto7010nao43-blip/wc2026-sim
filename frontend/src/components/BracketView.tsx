import type { MatchSummary, RoundName, TournamentResult } from "../types/domain";
import { MatchCard } from "./MatchCard";
import { TeamBadge } from "./TeamBadge";

interface Props {
  result: TournamentResult;
}

const ROUND_LABELS: Record<RoundName, string> = {
  group: "グループステージ",
  R32: "ラウンド32",
  R16: "ラウンド16",
  QF: "準々決勝",
  SF: "準決勝",
  THIRD_PLACE: "3位決定戦",
  FINAL: "決勝",
};

const BRACKET_ROUNDS: RoundName[] = ["R32", "R16", "QF", "SF", "FINAL"];

function BracketColumn({ round, matches }: { round: RoundName; matches: MatchSummary[] }) {
  return (
    <div className="flex w-[180px] flex-shrink-0 flex-col justify-around gap-4">
      <h4 className="text-center text-xs font-semibold tracking-wide text-slate-400">{ROUND_LABELS[round]}</h4>
      <div className="flex flex-1 flex-col justify-around gap-3">
        {matches.length === 0
          ? <p className="text-center text-xs text-slate-500">未実施</p>
          : matches.map((m) => <MatchCard key={m.id} match={m} />)}
      </div>
    </div>
  );
}

export function BracketView({ result }: Props) {
  const champion = result.champion_team_id;

  return (
    <div>
      {champion && (
        <div className="mb-6 rounded-lg border border-amber-500 bg-amber-500/10 p-4 text-center">
          <p className="text-xs uppercase tracking-widest text-amber-400">優勝</p>
          <div className="mt-1 flex justify-center text-lg">
            <TeamBadge teamId={champion} className="font-extrabold text-amber-300" />
          </div>
        </div>
      )}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {BRACKET_ROUNDS.map((round) => (
          <BracketColumn key={round} round={round} matches={result.matches[round] ?? []} />
        ))}
      </div>
      {result.matches.THIRD_PLACE?.length > 0 && (
        <div className="mt-6 max-w-xs">
          <h4 className="mb-2 text-center text-xs font-semibold tracking-wide text-slate-400">
            {ROUND_LABELS.THIRD_PLACE}
          </h4>
          {result.matches.THIRD_PLACE.map((m) => <MatchCard key={m.id} match={m} />)}
        </div>
      )}
    </div>
  );
}
