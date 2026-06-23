import type { MatchAnalysis } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  analysis: MatchAnalysis | null;
}

export function MatchAnalysisPanel({ analysis }: Props) {
  if (!analysis) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        この試合の詳細分析は利用できません。
      </div>
    );
  }

  const maxActions = Math.max(1, ...analysis.momentum_segments.flatMap((s) => [s.home_actions, s.away_actions]));
  const totalMomentumActions = analysis.momentum_segments.reduce((sum, seg) => sum + seg.home_actions + seg.away_actions, 0);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs uppercase tracking-widest text-slate-500">試合分析</p>
        {totalMomentumActions > 0 && (
          <p className="text-[11px] text-slate-500">分析対象アクション: {totalMomentumActions}</p>
        )}
      </div>

      {analysis.turning_point && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-400">ターニングポイント</span>
            <span className="font-semibold text-amber-300">{analysis.turning_point.minute}'</span>
            <TeamBadge teamId={analysis.turning_point.team_id} />
          </div>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{analysis.turning_point.description}</p>
        </div>
      )}

      {analysis.momentum_segments.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-[11px] text-slate-500">攻勢の流れ(シュート数)</p>
          <div className="space-y-1">
            {analysis.momentum_segments.map((seg) => (
              <div key={seg.start_minute} className="grid grid-cols-[3.2rem_1fr_4.2rem] items-center gap-2 text-[11px] text-slate-400">
                <span className="text-right">{seg.start_minute}-{seg.end_minute}'</span>
                <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-700">
                  <div className="bg-emerald-500" style={{ width: `${(seg.home_actions / (2 * maxActions)) * 100}%` }} />
                  <div className="ml-auto bg-sky-500" style={{ width: `${(seg.away_actions / (2 * maxActions)) * 100}%` }} />
                </div>
                <span className="text-slate-300">
                  {seg.home_actions}-{seg.away_actions}
                  {seg.dominant_team_id && <span className="ml-1 text-slate-500">優勢 {seg.dominant_team_id}</span>}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.key_players.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-[11px] text-slate-500">注目選手</p>
          <div className="space-y-1">
            {analysis.key_players.map((p) => (
              <div key={p.player_id} className="flex items-center justify-between gap-3 text-sm">
                <span className="min-w-0">
                  <span className="flex min-w-0 items-center gap-1.5 text-slate-200">
                    {p.is_mom && <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">MOM</span>}
                    <span className="truncate">{p.name}</span>
                  </span>
                  <span className="mt-0.5 block text-[11px] text-slate-500">
                    <TeamBadge teamId={p.team_id} showName={false} />
                  </span>
                </span>
                <span className="shrink-0 font-semibold text-emerald-400">{p.rating.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-slate-500">{analysis.tactical_note}</p>
    </div>
  );
}
