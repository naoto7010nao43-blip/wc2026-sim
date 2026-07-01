import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MatchupBreakdownFactor, MatchupBreakdownOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  homeTeamId: string;
  awayTeamId: string;
}

interface ScopedError {
  homeTeamId: string;
  awayTeamId: string;
  message: string;
}

function impactWidth(value: number): string {
  return `${Math.min(100, Math.max(8, Math.abs(value) * 900))}%`;
}

function impactTone(value: number): string {
  if (Math.abs(value) < 0.01) return "bg-slate-500";
  return value > 0 ? "bg-blue-400" : "bg-rose-400";
}

function factorValue(value: number | null): string {
  return value == null ? "-" : value.toFixed(1);
}

function FactorRow({ factor }: { factor: MatchupBreakdownFactor }) {
  return (
    <div className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-100">{factor.label}</p>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {factorValue(factor.home_value)} / {factorValue(factor.away_value)}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {factor.edge_team_id ? <TeamBadge teamId={factor.edge_team_id} /> : <span className="text-slate-400">互角</span>}
          <span className="text-slate-500">{factor.model_impact >= 0 ? "+" : ""}{factor.model_impact.toFixed(3)}</span>
        </div>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-700">
        <div className={`h-full rounded-full ${impactTone(factor.model_impact)}`} style={{ width: impactWidth(factor.model_impact) }} />
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{factor.description_ja}</p>
    </div>
  );
}

export function MatchupBreakdownPanel({ homeTeamId, awayTeamId }: Props) {
  const [breakdown, setBreakdown] = useState<MatchupBreakdownOut | null>(null);
  const [error, setError] = useState<ScopedError | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getMatchupBreakdown(homeTeamId, awayTeamId)
      .then((data) => {
        if (cancelled) return;
        setBreakdown(data);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError({ homeTeamId, awayTeamId, message: String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [homeTeamId, awayTeamId]);

  const isStale = !breakdown || breakdown.home_team_id !== homeTeamId || breakdown.away_team_id !== awayTeamId;
  const currentError = error && error.homeTeamId === homeTeamId && error.awayTeamId === awayTeamId ? error.message : null;

  if (currentError) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
        勝敗要因を取得できませんでした。
      </section>
    );
  }

  if (isStale) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        勝敗要因を計算中...
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">勝敗要因</p>
          <h3 className="mt-1 text-base font-bold text-slate-100">{breakdown.summary_ja}</h3>
        </div>
        {breakdown.favorite_team_id && (
          <span className="rounded bg-emerald-500/15 px-2 py-1 text-[10px] font-semibold text-emerald-300">
            優勢: {breakdown.favorite_team_id}
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        {breakdown.factors.map((factor) => (
          <FactorRow key={factor.key} factor={factor} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {breakdown.lineups.map((lineup) => (
          <div key={lineup.team_id} className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
            <div className="flex items-center justify-between gap-2">
              <TeamBadge teamId={lineup.team_id} />
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${lineup.full_xi ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}>
                {lineup.full_xi ? "XI確認済み" : "XI不足"}
              </span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[11px]">
              <div className="rounded bg-slate-800/70 px-1 py-1">
                <p className="text-slate-500">布陣</p>
                <p className="font-semibold text-slate-200">{lineup.formation}</p>
              </div>
              <div className="rounded bg-slate-800/70 px-1 py-1">
                <p className="text-slate-500">先発信頼</p>
                <p className="font-semibold text-slate-200">
                  {lineup.avg_starting_probability == null ? "-" : `${Math.round(lineup.avg_starting_probability)}%`}
                </p>
              </div>
              <div className="rounded bg-slate-800/70 px-1 py-1">
                <p className="text-slate-500">低確率</p>
                <p className={lineup.low_probability_starter_count > 0 ? "font-semibold text-amber-300" : "font-semibold text-slate-200"}>
                  {lineup.low_probability_starter_count}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
        モデル: {breakdown.model_version}。この表示は既存の予測入力を分解した説明で、予測式やseedデータは変更していません。
      </p>
    </section>
  );
}
