import { useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "./TeamBadge";
import type { TournamentSimulationOut } from "../types/domain";

const ITERATIONS = 500;
const TOP_N = 5;

function topEntries(pct: Record<string, number>, n: number): [string, number][] {
  return Object.entries(pct)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

export function TournamentOddsPanel() {
  const [result, setResult] = useState<TournamentSimulationOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.simulateTournamentMonteCarlo({ iterations: ITERATIONS });
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <h3 className="text-lg font-bold">優勝確率・モンテカルロ推定</h3>
      <p className="mt-1 text-sm text-slate-400">
        1回分のブラケットだけでなく、{ITERATIONS}回シミュレーションした場合の確率分布を確認できます。
        計算負荷が高いため、ボタンを押したときのみ実行します。
      </p>

      <button
        onClick={run}
        disabled={loading}
        className="mt-4 rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "計算中..." : result ? "再計算する" : "優勝確率を計算する"}
      </button>

      {error && <p className="mt-3 text-sm text-rose-400">優勝確率の計算に失敗しました: {error}</p>}

      {result && (
        <div className="mt-5 space-y-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">優勝確率 上位{TOP_N}</p>
            <div className="mt-2 space-y-1.5">
              {topEntries(result.champion_pct, TOP_N).map(([teamId, pct]) => (
                <div key={teamId} className="flex items-center justify-between gap-2 text-sm">
                  <TeamBadge teamId={teamId} />
                  <span className="font-semibold text-emerald-400">{pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">準決勝進出確率 上位{TOP_N}</p>
            <div className="mt-2 space-y-1.5">
              {topEntries(result.semifinal_pct, TOP_N).map(([teamId, pct]) => (
                <div key={teamId} className="flex items-center justify-between gap-2 text-sm">
                  <TeamBadge teamId={teamId} />
                  <span className="text-slate-300">{pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-[11px] text-slate-500">
            {result.iterations}回試行 / モデル: {result.model_version}
          </p>
          <p className="text-[11px] text-slate-500">{result.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
