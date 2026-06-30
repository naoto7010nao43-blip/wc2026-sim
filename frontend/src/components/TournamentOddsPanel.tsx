import { useEffect, useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "./TeamBadge";
import type { SimulationStabilitySummary, TournamentSimulationOut } from "../types/domain";

const DEFAULT_ITERATIONS = 500;
const ITERATION_OPTIONS = [500, 1000, 2000, 3000] as const;
const TOP_N = 5;

function topEntries(pct: Record<string, number>, n: number): [string, number][] {
  return Object.entries(pct)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

function nonZeroCount(pct: Record<string, number>): number {
  return Object.values(pct).filter((value) => value > 0).length;
}

function sumTopEntries(pct: Record<string, number>, n: number): number {
  return topEntries(pct, n).reduce((sum, [, value]) => sum + value, 0);
}

export function TournamentOddsPanel() {
  const [result, setResult] = useState<TournamentSimulationOut | null>(null);
  const [stability, setStability] = useState<SimulationStabilitySummary | null>(null);
  const [iterations, setIterations] = useState<number>(DEFAULT_ITERATIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getSimulationStabilitySummary()
      .then((data) => {
        if (!cancelled) setStability(data);
      })
      .catch(() => {
        if (!cancelled) setStability(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.simulateTournamentMonteCarlo({ iterations });
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
        1回のトーナメント結果だけではなく、複数回のシミュレーションから勝ち上がりやすさを確認できます。
        計算負荷が高いため、ボタンを押したときだけ実行します。
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
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
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "計算中..." : result ? "再計算する" : "優勝確率を計算する"}
        </button>
        <p className="max-w-md text-xs leading-relaxed text-slate-500">
          試行回数を増やすほど確率のぶれは小さくなりますが、計算には時間がかかります。
        </p>
      </div>

      {error && <p className="mt-3 text-sm text-rose-400">優勝確率の計算に失敗しました: {error}</p>}

      {result && (
        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <SummaryMetric label="優勝候補集中度" value={`${sumTopEntries(result.champion_pct, 3).toFixed(1)}%`} />
            <SummaryMetric label="優勝可能性あり" value={`${nonZeroCount(result.champion_pct)}チーム`} />
            <SummaryMetric label="決勝進出候補" value={`${nonZeroCount(result.final_pct)}チーム`} />
          </div>

          {stability?.summary && (
            <div className="border-l-2 border-sky-500/60 pl-3 text-xs text-slate-400">
              <p className="font-semibold text-slate-300">確率の読み方: {stability.summary.recommendation_ja}</p>
              <p className="mt-1">
                監査上の最大ぶれは{stability.summary.maxAbsChampionPctDelta.toFixed(1)}ptです。近い確率差のチームは順位より候補帯として見てください。
              </p>
            </div>
          )}

          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">優勝確率 上位{TOP_N}</p>
            <div className="mt-2 space-y-1.5">
              {topEntries(result.champion_pct, TOP_N).map(([teamId, pct]) => (
                <ProbabilityRow key={teamId} teamId={teamId} pct={pct} accent="emerald" />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ProbabilityList title="決勝進出 上位" entries={topEntries(result.final_pct, TOP_N)} />
            <ProbabilityList title="準決勝進出 上位" entries={topEntries(result.semifinal_pct, TOP_N)} />
            <ProbabilityList title="準々決勝進出 上位" entries={topEntries(result.quarterfinal_pct, TOP_N)} />
          </div>

          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">ラウンド突破の見方</p>
            <div className="mt-2 grid grid-cols-1 gap-2 text-xs text-slate-400 sm:grid-cols-2">
              <p className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
                優勝候補集中度は、上位3チームの優勝確率合計です。高いほど大会が少数候補に寄っています。
              </p>
              <p className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
                各ラウンドの候補数は、{result.iterations}回の試行で1回以上その地点に到達したチーム数です。
              </p>
            </div>
          </div>

          <p className="text-[11px] text-slate-500">
            {result.iterations}回試行 / モデル: {result.model_version} / データ信頼度: {result.data_confidence ?? "不明"}
          </p>
          {(result.explanation?.length ?? 0) > 0 && (
            <ul className="space-y-1 text-[11px] text-slate-500">
              {result.explanation?.map((line, idx) => (
                <li key={idx}>・{line}</li>
              ))}
            </ul>
          )}
          <p className="text-[11px] text-slate-500">{result.disclaimer}</p>
        </div>
      )}
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="mt-1 text-base font-bold text-slate-100">{value}</p>
    </div>
  );
}

function ProbabilityList({ title, entries }: { title: string; entries: [string, number][] }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-widest text-slate-500">{title}</p>
      <div className="mt-2 space-y-1.5">
        {entries.map(([teamId, pct]) => (
          <ProbabilityRow key={teamId} teamId={teamId} pct={pct} accent="slate" />
        ))}
      </div>
    </div>
  );
}

function ProbabilityRow({ teamId, pct, accent }: { teamId: string; pct: number; accent: "emerald" | "slate" }) {
  const barClass = accent === "emerald" ? "bg-emerald-500" : "bg-sky-500";
  const textClass = accent === "emerald" ? "text-emerald-400" : "text-slate-300";
  return (
    <div className="text-sm">
      <div className="flex items-center justify-between gap-2">
        <TeamBadge teamId={teamId} />
        <span className={`font-semibold ${textClass}`}>{pct.toFixed(1)}%</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-700">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}
