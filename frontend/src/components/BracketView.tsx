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
  const isFinal = round === "FINAL";
  return (
    <div className="flex w-[190px] flex-shrink-0 flex-col gap-3">
      <h4
        className={`rounded border px-2 py-1 text-center font-display text-xs font-bold tracking-widest ${
          isFinal
            ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
            : "border-slate-700 bg-slate-800/60 text-slate-400"
        }`}
      >
        {ROUND_LABELS[round]}
      </h4>
      <div className="flex flex-1 flex-col justify-around gap-3">
        {matches.length === 0 ? (
          <p className="rounded border border-dashed border-slate-700 py-4 text-center text-xs text-slate-600">未実施</p>
        ) : (
          matches.map((m) => <MatchCard key={m.id} match={m} />)
        )}
      </div>
    </div>
  );
}

export function BracketView({ result }: Props) {
  const champion = result.champion_team_id;

  return (
    <div>
      {champion && (
        <div className="fade-up relative mb-6 overflow-hidden rounded-xl border border-amber-500/50 bg-gradient-to-b from-amber-500/15 via-slate-900/60 to-slate-900/60 p-6 text-center">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background: "radial-gradient(ellipse 60% 80% at 50% 0%, rgba(238,190,51,0.18), transparent 70%)",
            }}
          />
          <p className="font-display text-xs font-bold uppercase tracking-[0.35em] text-amber-400">Champion</p>
          <div className="mt-2 flex justify-center text-2xl">
            <TeamBadge teamId={champion} className="font-display font-extrabold text-amber-200" />
          </div>
          <p className="mt-1 text-xs text-slate-400">2026 FIFAワールドカップ 優勝(シミュレーション)</p>
        </div>
      )}
      <div className="scroll-thin flex gap-4 overflow-x-auto pb-2">
        {BRACKET_ROUNDS.map((round) => (
          <BracketColumn key={round} round={round} matches={result.matches[round] ?? []} />
        ))}
      </div>
      {result.matches.THIRD_PLACE?.length > 0 && (
        <div className="mt-6 max-w-xs">
          <h4 className="mb-2 rounded border border-slate-700 bg-slate-800/60 px-2 py-1 text-center font-display text-xs font-bold tracking-widest text-slate-400">
            {ROUND_LABELS.THIRD_PLACE}
          </h4>
          {result.matches.THIRD_PLACE.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      )}
    </div>
  );
}
