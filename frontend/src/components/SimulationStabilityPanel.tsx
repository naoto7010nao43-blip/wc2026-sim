import type { SimulationStabilitySummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: SimulationStabilitySummary;
}

const BAND_LABELS: Record<string, string> = {
  stable: "安定",
  usable: "表示用に利用可",
  volatile: "揺れが大きい",
};

const BAND_STYLES: Record<string, string> = {
  stable: "bg-emerald-500/15 text-emerald-300",
  usable: "bg-sky-500/15 text-sky-300",
  volatile: "bg-amber-500/15 text-amber-300",
};

function LatestSample({ summary }: Props) {
  const latest = summary.samples[summary.samples.length - 1];
  if (!latest) return null;
  return (
    <div className="rounded bg-slate-900/50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-300">{latest.iterations}回試行の上位候補</p>
        <span className="text-[11px] text-slate-500">候補 {latest.championCandidateCount}チーム</span>
      </div>
      <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {latest.topChampionCandidates.slice(0, 6).map((candidate) => (
          <div key={candidate.team_id} className="flex items-center justify-between gap-2 rounded bg-slate-800/60 px-2 py-1 text-[11px]">
            <TeamBadge teamId={candidate.team_id} />
            <span className="font-semibold text-slate-200">{candidate.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LargestMovers({ summary }: Props) {
  const latestComparison = summary.comparisons[summary.comparisons.length - 1];
  if (!latestComparison) return null;
  return (
    <div className="rounded bg-slate-900/50 p-3">
      <p className="text-xs font-semibold text-slate-300">
        {latestComparison.fromIterations}回から{latestComparison.toIterations}回で揺れた候補
      </p>
      <div className="mt-2 space-y-1">
        {latestComparison.largest_movers.slice(0, 5).map((mover) => (
          <div key={mover.team_id} className="flex items-center justify-between gap-2 rounded bg-slate-800/60 px-2 py-1 text-[11px]">
            <TeamBadge teamId={mover.team_id} />
            <span className={mover.delta_pct >= 0 ? "text-emerald-300" : "text-rose-300"}>
              {mover.delta_pct >= 0 ? "+" : ""}
              {mover.delta_pct.toFixed(1)}pt
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SimulationStabilityPanel({ summary }: Props) {
  if (!summary.summary) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        {summary.note}
      </div>
    );
  }

  const band = summary.summary.stabilityBand;

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-200">モンテカルロ安定性</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">{summary.modelVersion ?? "-"}</p>
        </div>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${BAND_STYLES[band] ?? "bg-slate-700 text-slate-300"}`}>
          {BAND_LABELS[band] ?? band}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-1.5 text-center text-[11px]">
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">最大ブレ幅</p>
          <p className="font-semibold text-slate-100">{summary.summary.maxAbsChampionPctDelta.toFixed(1)}pt</p>
        </div>
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">平均ブレ幅</p>
          <p className="font-semibold text-slate-100">{summary.summary.averageAbsChampionPctDelta.toFixed(1)}pt</p>
        </div>
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">試行回数</p>
          <p className="font-semibold text-slate-100">{summary.scope?.iterationCounts.join("/") ?? "-"}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <LatestSample summary={summary} />
        <LargestMovers summary={summary} />
      </div>

      <p className="mt-3 text-[11px] text-slate-400">{summary.summary.recommendation_ja}</p>
      <p className="mt-1 text-[11px] text-slate-500">{summary.note}</p>
    </section>
  );
}
