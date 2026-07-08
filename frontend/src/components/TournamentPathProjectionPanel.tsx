import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useTeamsMap } from "../context/useTeams";
import type { TeamSummary, TournamentPathProjectionOut } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

const DEFAULT_ITERATIONS = 200;
const ITERATION_OPTIONS = [200, 500, 1000] as const;

function sortTeams(teamsById: Record<string, TeamSummary>): TeamSummary[] {
  return Object.values(teamsById).sort((a, b) => {
    const groupCompare = (a.group_id ?? "Z").localeCompare(b.group_id ?? "Z");
    if (groupCompare !== 0) return groupCompare;
    return (a.fifa_rank ?? 999) - (b.fifa_rank ?? 999);
  });
}

export function TournamentPathProjectionPanel() {
  const teamsById = useTeamsMap();
  const teams = useMemo(() => sortTeams(teamsById), [teamsById]);
  const [teamId, setTeamId] = useState("JPN");
  const [iterations, setIterations] = useState<number>(DEFAULT_ITERATIONS);
  const [projection, setProjection] = useState<TournamentPathProjectionOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const effectiveTeamId = teamsById[teamId] ? teamId : (teams[0]?.id ?? "");

  useEffect(() => {
    if (!effectiveTeamId) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch status reset when selected team/iteration changes
    setLoading(true);
    setError(null);
    api
      .getTournamentPathProjection(effectiveTeamId, { iterations })
      .then((data) => {
        if (!cancelled) setProjection(data);
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
  }, [effectiveTeamId, iterations]);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold">優勝ルート予測</h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            選んだチームが各ラウンドへ進む確率と、そこで当たりやすい相手を大会全体のモンテカルロ試行から集計します。
          </p>
        </div>
        {projection && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 px-3 py-2 text-right">
            <p className="text-[11px] text-emerald-300">優勝確率</p>
            <p className="text-xl font-bold text-emerald-100">{projection.champion_pct.toFixed(1)}%</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="text-xs text-slate-500">対象チーム</span>
          <select
            value={effectiveTeamId}
            onChange={(event) => setTeamId(event.target.value)}
            className="mt-1 min-w-48 rounded-md border border-slate-600 bg-slate-900 px-2 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500"
          >
            {teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.group_id ? `Group ${team.group_id} / ` : ""}
                {team.name} ({team.id})
              </option>
            ))}
          </select>
        </label>
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
        {projection && (
          <div className="pb-2 text-sm text-slate-300">
            <TeamBadge teamId={projection.team_id} />
          </div>
        )}
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">想定ルートを計算中...</p>}
      {error && <p className="mt-4 text-sm text-rose-400">優勝ルート予測の取得に失敗しました: {error}</p>}

      {projection && !loading && (
        <div className="mt-5 space-y-4">
          <p className="text-sm leading-relaxed text-slate-400">{projection.note_ja}</p>
          <div className="space-y-3">
            {projection.stages.map((stage) => (
              <StageRow key={stage.stage_key} stage={stage} />
            ))}
          </div>
          <p className="text-[11px] leading-relaxed text-slate-500">
            {projection.iterations.toLocaleString("ja-JP")}回試行 / モデル: {projection.model_version} / データ信頼度:{" "}
            {projection.data_confidence}。{projection.disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}

function StageRow({ stage }: { stage: TournamentPathProjectionOut["stages"][number] }) {
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-slate-100">{stage.stage_label_ja}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {stage.most_likely_slot ? `最多スロット: ${stage.most_likely_slot}` : "進出後のブラケット位置から算出"}
          </p>
        </div>
        <div className="min-w-32 text-right">
          <p className="text-[11px] text-slate-500">到達率</p>
          <p className="text-base font-bold text-slate-100">{stage.reach_pct.toFixed(1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-700">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, stage.reach_pct)}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-5">
        {stage.opponent_options.length === 0 ? (
          <p className="text-xs text-slate-500 md:col-span-5">このラウンドの相手候補はほぼ発生していません。</p>
        ) : (
          stage.opponent_options.map((opponent) => (
            <div key={opponent.team_id} className="min-w-0 rounded border border-slate-700/70 bg-slate-950/35 px-2 py-2">
              <TeamBadge teamId={opponent.team_id} />
              <p className="mt-1 text-xs font-semibold text-slate-300">{opponent.probability_pct.toFixed(1)}%</p>
            </div>
          ))
        )}
      </div>
    </article>
  );
}
