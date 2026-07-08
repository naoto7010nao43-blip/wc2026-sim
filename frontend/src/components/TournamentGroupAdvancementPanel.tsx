import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TournamentGroupAdvancementGroup, TournamentGroupAdvancementOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

const DEFAULT_ITERATIONS = 200;
const ITERATION_OPTIONS = [200, 500, 1000] as const;

export function TournamentGroupAdvancementPanel() {
  const [summary, setSummary] = useState<TournamentGroupAdvancementOut | null>(null);
  const [iterations, setIterations] = useState<number>(DEFAULT_ITERATIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch status reset when iteration count changes
    setLoading(true);
    setError(null);
    api
      .getTournamentGroupAdvancement({ iterations })
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
          <h3 className="text-lg font-bold">グループ突破確率</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            各組を同じ大会ルールで繰り返し試行し、1位・2位・3位突破・総突破率を並べます。3位争いの重みまで含めて見られる予選の地図です。
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

      {loading && <p className="mt-4 text-sm text-slate-400">グループ突破確率を集計中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">グループ突破確率の取得に失敗しました: {error}</p>}

      {summary && !loading && (
        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {summary.groups.map((group) => (
              <GroupCard key={group.group_id} group={group} />
            ))}
          </div>
          <p className="text-[11px] leading-relaxed text-slate-500">
            {summary.iterations.toLocaleString("ja-JP")}回試行 / モデル: {summary.model_version} / データ信頼度:{" "}
            {summary.data_confidence}。{summary.note_ja} {summary.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function GroupCard({ group }: { group: TournamentGroupAdvancementGroup }) {
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-bold text-slate-100">Group {group.group_id}</h4>
        <p className="text-[11px] text-slate-500">突破率順</p>
      </div>
      <div className="mt-3 space-y-3">
        {group.teams.map((team) => (
          <div key={team.team_id} className="min-w-0">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <TeamBadge teamId={team.team_id} />
                <p className="mt-0.5 text-[11px] text-slate-500">
                  FIFA {team.fifa_rank == null ? "未設定" : `${team.fifa_rank}位`} / 平均勝点 {team.average_points.toFixed(2)}
                </p>
              </div>
              <div className="min-w-20 text-right">
                <p className="text-[11px] text-slate-500">突破</p>
                <p className="text-base font-bold text-emerald-300">{team.advance_pct.toFixed(1)}%</p>
              </div>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-700">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, team.advance_pct)}%` }} />
            </div>
            <div className="mt-2 grid grid-cols-4 gap-2 text-center">
              <MiniMetric label="1位" value={team.first_place_pct} />
              <MiniMetric label="2位" value={team.second_place_pct} />
              <MiniMetric label="3位" value={team.third_place_pct} />
              <MiniMetric label="3位突破" value={team.third_place_qualified_pct} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-slate-700/70 bg-slate-950/35 px-1.5 py-1.5">
      <p className="text-[10px] text-slate-500">{label}</p>
      <p className="mt-0.5 text-xs font-bold text-slate-100">{value.toFixed(1)}%</p>
    </div>
  );
}
