import { useEffect, useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "./TeamBadge";
import type { DataQualitySummary, MatchPredictionOut } from "../types/domain";

interface Props {
  homeTeamId: string;
  awayTeamId: string;
  dataQuality?: DataQualitySummary | null;
}

interface ScopedError {
  homeTeamId: string;
  awayTeamId: string;
  message: string;
}

function freshnessLabel(status: string): string {
  if (status === "critical") return "再確認推奨";
  if (status === "warning") return "一部注意";
  return "良好";
}

function edgeLabel(edgePct: number, drawIsTop: boolean): string {
  if (drawIsTop) return "引き分け寄り";
  if (edgePct >= 18) return "明確な優勢";
  if (edgePct >= 8) return "やや優勢";
  return "拮抗";
}

export function MatchPredictionPanel({ homeTeamId, awayTeamId, dataQuality }: Props) {
  const [prediction, setPrediction] = useState<MatchPredictionOut | null>(null);
  const [error, setError] = useState<ScopedError | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getMatchPrediction(homeTeamId, awayTeamId)
      .then((p) => {
        if (cancelled) return;
        setPrediction(p);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError({ homeTeamId, awayTeamId, message: String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [homeTeamId, awayTeamId]);

  // Derive staleness/error-relevance from the props instead of resetting
  // state synchronously in the effect, so a slow response for a previous
  // matchup can't flash in as if it belongs to the newly selected one.
  const isStale = !prediction || prediction.home_team_id !== homeTeamId || prediction.away_team_id !== awayTeamId;
  const currentError = error && error.homeTeamId === homeTeamId && error.awayTeamId === awayTeamId ? error.message : null;

  if (currentError) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-rose-400">
        予測データを取得できませんでした。
      </div>
    );
  }

  if (isStale) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        予測を計算中...
      </div>
    );
  }

  const topScores = prediction.most_likely_scores.slice(0, 3);
  const drawIsTop =
    prediction.draw_pct >= prediction.home_win_pct && prediction.draw_pct >= prediction.away_win_pct;
  const favoriteTeamId =
    drawIsTop ? null : prediction.home_win_pct >= prediction.away_win_pct ? prediction.home_team_id : prediction.away_team_id;
  const edgePct = Math.abs(prediction.home_win_pct - prediction.away_win_pct);
  const xgEdge = prediction.home_expected_goals - prediction.away_expected_goals;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <p className="text-xs uppercase tracking-widest text-slate-500">事前予測</p>

      <div className="mt-2 flex items-center justify-between text-sm text-slate-200">
        <TeamBadge teamId={homeTeamId} />
        <span className="text-xs text-slate-500">vs</span>
        <TeamBadge teamId={awayTeamId} />
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span className="font-semibold text-blue-400">{prediction.home_win_pct.toFixed(1)}%</span>
          <span className="text-slate-500">引分 {prediction.draw_pct.toFixed(1)}%</span>
          <span className="font-semibold text-rose-400">{prediction.away_win_pct.toFixed(1)}%</span>
        </div>
        <div className="mt-1 flex h-1.5 overflow-hidden rounded-full bg-slate-700">
          <div className="bg-blue-400" style={{ width: `${prediction.home_win_pct}%` }} />
          <div className="bg-slate-500" style={{ width: `${prediction.draw_pct}%` }} />
          <div className="bg-rose-400" style={{ width: `${prediction.away_win_pct}%` }} />
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-700/70 bg-slate-900/45 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-slate-500">優勢度</span>
          <span className="rounded bg-slate-700/60 px-2 py-0.5 font-semibold text-slate-200">
            {edgeLabel(edgePct, drawIsTop)}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-200">
          {favoriteTeamId ? <TeamBadge teamId={favoriteTeamId} /> : <span className="font-semibold text-slate-200">引き分け</span>}
          <span className="text-xs text-slate-500">
            勝率差 {edgePct.toFixed(1)}pt / xG差 {xgEdge >= 0 ? "+" : ""}
            {xgEdge.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span>予想得点: {prediction.home_expected_goals.toFixed(2)}</span>
        <span>予想得点: {prediction.away_expected_goals.toFixed(2)}</span>
      </div>

      {topScores.length > 0 && (
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {topScores.map(([h, a, pct], idx) => (
            <span key={idx} className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200">
              {h}-{a} <span className="text-slate-400">({pct.toFixed(1)}%)</span>
            </span>
          ))}
        </div>
      )}

      {prediction.explanation.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-slate-400">
          {prediction.explanation.slice(0, 4).map((line, idx) => (
            <li key={idx}>・{line}</li>
          ))}
        </ul>
      )}

      <p className="mt-3 text-[11px] text-slate-500">
        モデル: {prediction.model_version} / データ信頼度: {prediction.data_confidence}
      </p>
      {dataQuality && dataQuality.freshness_status !== "ok" && (
        <div className="mt-2 rounded border border-amber-500/25 bg-amber-500/10 px-2 py-1.5 text-[11px] leading-relaxed text-amber-100/85">
          基礎データ: {freshnessLabel(dataQuality.freshness_status)}。能力値・戦術値の追加反映前に最新ソースの再確認が必要です。
        </div>
      )}
      <p className="mt-1 text-[11px] text-slate-500">{prediction.disclaimer}</p>
    </div>
  );
}
