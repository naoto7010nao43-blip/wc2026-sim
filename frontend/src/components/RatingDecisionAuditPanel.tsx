import type { RatingDecisionAuditSummary, RatingDecisionCandidate, RatingDecisionTeamRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: RatingDecisionAuditSummary;
}

const DRIVER_LABELS: Record<string, string> = {
  attack: "攻撃面",
  defense: "守備面",
  strength: "総合的な強さ",
  tactical: "戦術面",
  none: "特になし",
  unknown: "不明",
};

const BUCKET_LABELS: Record<string, string> = {
  candidate_for_later_proposal: "将来の提案候補",
  source_review_first: "出典確認が先",
  do_not_use_for_upgrade_proposal: "変更候補から除外",
  monitor_only: "モニタリングのみ",
};

function CandidateLine({ candidate }: { candidate: RatingDecisionCandidate }) {
  return (
    <li className="break-words rounded bg-slate-800/50 px-2 py-1 text-[11px] text-slate-300">
      {candidate.name}
      <span className="ml-1 text-slate-500">{candidate.primary_position ?? "-"}</span>
      <span className="ml-1 text-emerald-400">能力値 {candidate.current_overall ?? "-"}</span>
    </li>
  );
}

function RatingDecisionTeamCard({ row }: { row: RatingDecisionTeamRow }) {
  const blockedCount = row.bucketCounts.do_not_use_for_upgrade_proposal ?? 0;
  const sourceReviewCount = row.bucketCounts.source_review_first ?? 0;
  const laterCandidates = row.candidate_for_later_proposal.slice(0, 4);

  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TeamBadge teamId={row.team_id} />
        <span className="rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
          主な要因: {DRIVER_LABELS[row.dominant_negative_driver] ?? row.dominant_negative_driver}
        </span>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[11px]">
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">提案候補</p>
          <p className="font-semibold text-emerald-400">{laterCandidates.length}</p>
        </div>
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">出典確認が先</p>
          <p className="font-semibold text-amber-400">{sourceReviewCount}</p>
        </div>
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">除外候補</p>
          <p className="font-semibold text-slate-400">{blockedCount}</p>
        </div>
      </div>

      {laterCandidates.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {laterCandidates.map((candidate) => (
            <CandidateLine key={candidate.player_id} candidate={candidate} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[11px] text-slate-500">現時点で将来の提案候補に挙がる選手はいません。</p>
      )}
    </div>
  );
}

export function RatingDecisionAuditPanel({ summary }: Props) {
  if (summary.teams.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        {Object.entries(summary.bucketCounts).map(([bucket, count]) => (
          <span key={bucket} className="rounded bg-slate-700/40 px-2 py-1 text-slate-300">
            {BUCKET_LABELS[bucket] ?? bucket}: {count}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {summary.teams.map((row) => (
          <RatingDecisionTeamCard key={row.team_id} row={row} />
        ))}
      </div>
      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
