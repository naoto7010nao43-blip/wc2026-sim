import { useEffect, useState } from "react";
import { api } from "../api/client";
import { countryNameJa } from "../data/countryNamesJa";
import { flagUrl } from "../data/teamFlags";
import { useTeam } from "../context/useTeams";
import { TeamBadge } from "./TeamBadge";
import type { SimulationStabilitySummary, TournamentSimulationOut } from "../types/domain";

const DEFAULT_ITERATIONS = 1000;
const ITERATION_OPTIONS = [500, 1000, 2000, 3000] as const;
const TOP_N = 5;
const BAR_TOP_N = 10;

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

  const champTop = result ? topEntries(result.champion_pct, BAR_TOP_N) : [];
  const podium = champTop.slice(0, 3);
  const rest = champTop.slice(3);
  const maxPct = champTop.length > 0 ? champTop[0][1] : 100;

  return (
    <section className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-display text-[11px] font-bold uppercase tracking-[0.3em] text-emerald-400">Title Odds</p>
          <h3 className="mt-1 font-display text-xl font-extrabold tracking-wide">優勝確率・モンテカルロ推定</h3>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            大会全体を{iterations.toLocaleString("ja-JP")}回シミュレーションし、各国の勝ち上がりやすさを推定します。
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="text-xs text-slate-500">試行回数</span>
            <select
              value={iterations}
              onChange={(event) => setIterations(Number(event.target.value))}
              disabled={loading}
              className="mt-1 rounded-lg border border-slate-600 bg-slate-900 px-2 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {ITERATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.toLocaleString("ja-JP")}回
                </option>
              ))}
            </select>
          </label>
          <button onClick={run} disabled={loading} className="btn-primary px-6 py-2.5">
            {loading ? "計算中..." : result ? "再計算する" : "優勝確率を計算する"}
          </button>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-rose-400">優勝確率の計算に失敗しました: {error}</p>}

      {!result && !loading && (
        <p className="mt-4 rounded-lg border border-dashed border-slate-700 p-4 text-center text-xs text-slate-500">
          計算負荷が高いため、ボタンを押したときだけ実行します。
        </p>
      )}

      {result && (
        <div className="mt-6 space-y-6">
          {/* 表彰台: 上位3カ国 */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {podium.map(([teamId, pct], i) => (
              <PodiumCard key={teamId} teamId={teamId} pct={pct} rank={i + 1} />
            ))}
          </div>

          {/* 4位以下: アニメーション付きバー */}
          {rest.length > 0 && (
            <div>
              <p className="font-display text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Contenders 4–{BAR_TOP_N}</p>
              <div className="mt-2 space-y-2">
                {rest.map(([teamId, pct], i) => (
                  <OddsBar key={teamId} teamId={teamId} pct={pct} rank={i + 4} maxPct={maxPct} />
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <SummaryMetric label="優勝候補集中度" value={`${sumTopEntries(result.champion_pct, 3).toFixed(1)}%`} hint="上位3チームの合計" />
            <SummaryMetric label="優勝可能性あり" value={`${nonZeroCount(result.champion_pct)}チーム`} hint="1回以上優勝したチーム数" />
            <SummaryMetric label="決勝進出候補" value={`${nonZeroCount(result.final_pct)}チーム`} hint="1回以上決勝に到達" />
          </div>

          {stability?.summary && (
            <div className="border-l-2 border-sky-500/60 pl-3 text-xs text-slate-400">
              <p className="font-semibold text-slate-300">確率の読み方: {stability.summary.recommendation_ja}</p>
              <p className="mt-1">
                監査上の最大ぶれは{stability.summary.maxAbsChampionPctDelta.toFixed(1)}ptです。近い確率差のチームは順位より候補帯として見てください。
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ProbabilityList title="決勝進出 上位" entries={topEntries(result.final_pct, TOP_N)} />
            <ProbabilityList title="準決勝進出 上位" entries={topEntries(result.semifinal_pct, TOP_N)} />
            <ProbabilityList title="準々決勝進出 上位" entries={topEntries(result.quarterfinal_pct, TOP_N)} />
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

const PODIUM_STYLES = [
  {
    ring: "border-amber-400/60",
    bg: "from-amber-500/15",
    label: "text-amber-300",
    bar: "linear-gradient(90deg, #d9a514, #f5d574)",
  },
  {
    ring: "border-slate-400/50",
    bg: "from-slate-400/10",
    label: "text-slate-300",
    bar: "linear-gradient(90deg, #93aa9c, #d3e2d7)",
  },
  {
    ring: "border-orange-700/60",
    bg: "from-orange-800/20",
    label: "text-orange-300",
    bar: "linear-gradient(90deg, #b45309, #f59e0b)",
  },
] as const;

function PodiumCard({ teamId, pct, rank }: { teamId: string; pct: number; rank: number }) {
  const team = useTeam(teamId);
  const style = PODIUM_STYLES[rank - 1];
  const flag = flagUrl(teamId, 80);
  return (
    <div
      className={`fade-up relative overflow-hidden rounded-xl border ${style.ring} bg-gradient-to-b ${style.bg} to-slate-900/60 p-4 ${
        rank === 1 ? "sm:order-none" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={`score-num text-2xl ${style.label}`}>{rank}</span>
        {flag && (
          <img src={flag} alt="" width={48} height={34} loading="lazy" className="h-[34px] w-12 rounded object-cover ring-1 ring-white/20" />
        )}
      </div>
      <p className="mt-3 truncate text-base font-bold text-slate-100">{countryNameJa(teamId, team?.name ?? teamId)}</p>
      <p className={`score-num mt-1 text-4xl ${style.label}`}>
        {pct.toFixed(1)}
        <span className="ml-0.5 text-lg">%</span>
      </p>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct)}%`, background: style.bar }} />
      </div>
    </div>
  );
}

function OddsBar({ teamId, pct, rank, maxPct }: { teamId: string; pct: number; rank: number; maxPct: number }) {
  const width = maxPct > 0 ? (pct / maxPct) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="score-num w-6 shrink-0 text-right text-xs text-slate-500">{rank}</span>
      <div className="w-28 shrink-0 sm:w-44">
        <TeamBadge teamId={teamId} />
      </div>
      <div className="h-4 min-w-0 flex-1 overflow-hidden rounded bg-slate-800/80">
        <div
          className="h-full rounded bg-gradient-to-r from-emerald-600 to-emerald-400 transition-[width] duration-700"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="score-num w-12 shrink-0 text-right text-sm text-emerald-300 sm:w-14 sm:text-base">{pct.toFixed(1)}%</span>
    </div>
  );
}

function SummaryMetric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="score-num mt-1 text-xl text-slate-100">{value}</p>
      <p className="mt-0.5 text-[11px] text-slate-600">{hint}</p>
    </div>
  );
}

function ProbabilityList({ title, entries }: { title: string; entries: [string, number][] }) {
  return (
    <div>
      <p className="font-display text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{title}</p>
      <div className="mt-2 space-y-1.5">
        {entries.map(([teamId, pct]) => (
          <div key={teamId} className="text-sm">
            <div className="flex items-center justify-between gap-2">
              <TeamBadge teamId={teamId} />
              <span className="score-num text-slate-300">{pct.toFixed(1)}%</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-sky-500/80" style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
