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

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <p className="mb-3 text-xs uppercase tracking-widest text-slate-500">試合分析</p>

      {analysis.turning_point && (
        <div className="mb-3 flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-sm">
          <span className="text-slate-400">ターニングポイント:</span>
          <span className="font-semibold text-amber-300">{analysis.turning_point.minute}'</span>
          <TeamBadge teamId={analysis.turning_point.team_id} />
        </div>
      )}

      {analysis.momentum_segments.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-[11px] text-slate-500">攻勢の流れ(シュート数)</p>
          <div className="space-y-1">
            {analysis.momentum_segments.map((seg) => (
              <div key={seg.start_minute} className="flex items-center gap-2 text-[11px] text-slate-400">
                <span className="w-12 shrink-0 text-right">{seg.start_minute}-{seg.end_minute}'</span>
                <div className="flex h-2.5 flex-1 overflow-hidden rounded-full bg-slate-700">
                  <div
                    className="bg-emerald-500"
                    style={{ width: `${(seg.home_actions / (2 * maxActions)) * 100}%` }}
                  />
                  <div
                    className="ml-auto bg-sky-500"
                    style={{ width: `${(seg.away_actions / (2 * maxActions)) * 100}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-slate-300">{seg.home_actions}-{seg.away_actions}</span>
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
              <div key={p.player_id} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5 text-slate-200">
                  {p.is_mom && <span title="Man of the Match">⭐</span>}
                  {p.name}
                </span>
                <span className="font-semibold text-emerald-400">{p.rating.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-slate-500">{analysis.tactical_note}</p>
    </div>
  );
}
