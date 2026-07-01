import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TournamentDarkHorseCandidate, TournamentDarkHorsesOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

const DEFAULT_ITERATIONS = 500;
const ITERATION_OPTIONS = [500, 1000, 2000] as const;

export function TournamentDarkHorsesPanel() {
  const [summary, setSummary] = useState<TournamentDarkHorsesOut | null>(null);
  const [iterations, setIterations] = useState<number>(DEFAULT_ITERATIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch status reset when iteration count changes
    setLoading(true);
    setError(null);
    api
      .getTournamentDarkHorses({ iterations, limit: 8 })
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
          <h3 className="text-lg font-bold">ダークホース候補</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            FIFAランク上位の本命を除き、準々決勝以降へ進む確率がモデル上で残っているチームを抽出します。優勝候補表だけでは見落としやすい観戦ポイントです。
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

      {loading && <p className="mt-4 text-sm text-slate-400">注目候補を集計中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">ダークホース候補の取得に失敗しました: {error}</p>}

      {summary && !loading && (
        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {summary.candidates.map((candidate, index) => (
              <DarkHorseCard key={candidate.team_id} candidate={candidate} rank={index + 1} />
            ))}
          </div>
          <p className="text-[11px] leading-relaxed text-slate-500">
            {summary.iterations.toLocaleString("ja-JP")}回試行 / 候補{summary.candidate_count}チーム / モデル:{" "}
            {summary.model_version} / データ信頼度: {summary.data_confidence}。{summary.note_ja} {summary.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function DarkHorseCard({ candidate, rank }: { candidate: TournamentDarkHorseCandidate; rank: number }) {
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">#{rank}</p>
          <div className="mt-1">
            <TeamBadge teamId={candidate.team_id} />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            FIFAランク {candidate.fifa_rank == null ? "未設定" : `${candidate.fifa_rank}位`}
          </p>
        </div>
        <div className="rounded-lg border border-sky-500/30 bg-sky-950/20 px-3 py-2 text-right">
          <p className="text-[11px] text-sky-300">注目度</p>
          <p className="text-lg font-bold text-sky-100">{candidate.surprise_score.toFixed(1)}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2">
        <Metric label="R16" value={candidate.round_of_16_pct} />
        <Metric label="QF" value={candidate.quarterfinal_pct} />
        <Metric label="決勝" value={candidate.final_pct} />
        <Metric label="優勝" value={candidate.champion_pct} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-slate-400">{candidate.reason_ja}</p>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-slate-700/70 bg-slate-950/35 px-2 py-2 text-center">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-bold text-slate-100">{value.toFixed(1)}%</p>
    </div>
  );
}
