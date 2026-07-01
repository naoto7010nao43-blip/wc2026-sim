import { useEffect, useState } from "react";
import { api } from "../api/client";
import { TeamBadge } from "./TeamBadge";
import type { TournamentUpsetWatchMatch, TournamentUpsetWatchOut } from "../types/domain";

const DISPLAY_LIMIT = 8;

export function TournamentUpsetWatchPanel() {
  const [summary, setSummary] = useState<TournamentUpsetWatchOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTournamentUpsetWatch(DISPLAY_LIMIT)
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
  }, []);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">波乱候補ウォッチ</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            グループステージ全カードを同じ予測モデルで横断し、格下側の勝率と引き分け確率から「取りこぼしが起きやすい試合」を並べます。
          </p>
        </div>
        {summary && (
          <div className="rounded-lg border border-slate-700 bg-slate-900/55 px-3 py-2 text-right">
            <p className="text-[11px] text-slate-500">対象カード</p>
            <p className="text-base font-bold text-slate-100">{summary.match_count}</p>
          </div>
        )}
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">波乱候補を計算中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">波乱候補の取得に失敗しました: {error}</p>}

      {summary && (
        <div className="mt-5 space-y-3">
          {summary.candidates.map((match, index) => (
            <UpsetRow key={`${match.group_id}-${match.home_team_id}-${match.away_team_id}`} match={match} rank={index + 1} />
          ))}
          <p className="text-[11px] leading-relaxed text-slate-500">
            波乱スコアは格下勝率に引き分け確率の一部を足した目安です。モデル: {summary.model_version}。{summary.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function UpsetRow({ match, rank }: { match: TournamentUpsetWatchMatch; rank: number }) {
  const favoriteLabel = match.favorite_team_id === match.home_team_id ? match.home_team_name : match.away_team_name;
  const underdogLabel = match.underdog_team_id === match.home_team_id ? match.home_team_name : match.away_team_name;
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
            #{rank} / Group {match.group_id}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <TeamBadge teamId={match.home_team_id} />
            <span className="text-slate-500">vs</span>
            <TeamBadge teamId={match.away_team_id} />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right text-xs sm:min-w-[300px]">
          <Metric label="波乱" value={`${match.upset_score.toFixed(1)}`} accent="text-amber-300" />
          <Metric label="格下勝率" value={`${match.underdog_win_pct.toFixed(1)}%`} accent="text-sky-300" />
          <Metric label="引分" value={`${match.draw_pct.toFixed(1)}%`} accent="text-slate-200" />
        </div>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-400 md:grid-cols-[1fr_1fr_2fr]">
        <p>
          本命: <span className="font-semibold text-slate-200">{favoriteLabel}</span> {match.favorite_win_pct.toFixed(1)}%
        </p>
        <p>
          対抗: <span className="font-semibold text-slate-200">{underdogLabel}</span> / xG差 {match.expected_goal_gap.toFixed(2)}
        </p>
        <p className="leading-relaxed">{match.reason_ja}</p>
      </div>
    </article>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div>
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`mt-0.5 text-sm font-bold ${accent}`}>{value}</p>
    </div>
  );
}
