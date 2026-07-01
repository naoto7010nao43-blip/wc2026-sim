import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TournamentFinalMatchupCandidate, TournamentFinalMatchupsOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

const DEFAULT_ITERATIONS = 500;
const ITERATION_OPTIONS = [500, 1000, 2000] as const;

export function TournamentFinalMatchupsPanel() {
  const [summary, setSummary] = useState<TournamentFinalMatchupsOut | null>(null);
  const [iterations, setIterations] = useState<number>(DEFAULT_ITERATIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch status reset when iteration count changes
    setLoading(true);
    setError(null);
    api
      .getTournamentFinalMatchups({ iterations, limit: 8 })
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [iterations]);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold">決勝カード候補</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            大会全体を繰り返し試行し、決勝で起こりやすい対戦カードと、そのカード内で優勝寄りのチームを集計します。
          </p>
        </div>
        <label className="block">
          <span className="text-xs text-slate-500">試行回数</span>
          <select
            value={iterations}
            onChange={(event) => setIterations(Number(event.target.value))}
            disabled={loading}
            className="mt-1 rounded-md border border-slate-600 bg-slate-900 px-2 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {ITERATION_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.toLocaleString("ja-JP")}回
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">決勝カードを集計中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">決勝カード候補の取得に失敗しました: {error}</p>}

      {summary && !loading && (
        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {summary.candidates.map((candidate, index) => (
              <FinalMatchupCard key={`${candidate.team_a_id}-${candidate.team_b_id}`} candidate={candidate} rank={index + 1} />
            ))}
          </div>
          <p className="text-[11px] leading-relaxed text-slate-500">
            {summary.iterations.toLocaleString("ja-JP")}回試行 / 候補カード {summary.matchup_count}通り / モデル:{" "}
            {summary.model_version} / データ信頼度: {summary.data_confidence}。{summary.note_ja} {summary.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function FinalMatchupCard({ candidate, rank }: { candidate: TournamentFinalMatchupCandidate; rank: number }) {
  const favoriteIsA = candidate.champion_favorite_team_id === candidate.team_a_id;
  const favoriteWinPct = favoriteIsA ? candidate.team_a_win_given_matchup_pct : candidate.team_b_win_given_matchup_pct;
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">#{rank}</p>
        <div className="text-right">
          <p className="text-[11px] text-slate-500">決勝発生率</p>
          <p className="text-lg font-bold text-emerald-300">{candidate.matchup_pct.toFixed(1)}%</p>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <div className="min-w-0">
          <TeamBadge teamId={candidate.team_a_id} />
          <p className="mt-1 text-xs text-slate-500">勝率 {candidate.team_a_win_given_matchup_pct.toFixed(1)}%</p>
        </div>
        <span className="text-xs font-semibold text-slate-500">vs</span>
        <div className="min-w-0 text-right">
          <div className="flex justify-end">
            <TeamBadge teamId={candidate.team_b_id} />
          </div>
          <p className="mt-1 text-xs text-slate-500">勝率 {candidate.team_b_win_given_matchup_pct.toFixed(1)}%</p>
        </div>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-700">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, candidate.matchup_pct)}%` }} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-slate-400">
        このカードが実現した場合は{" "}
        <span className="font-semibold text-slate-200">
          {favoriteIsA ? candidate.team_a_name : candidate.team_b_name}
        </span>{" "}
        がやや優勢です（条件付き優勝率 {favoriteWinPct.toFixed(1)}%）。
      </p>
    </article>
  );
}
