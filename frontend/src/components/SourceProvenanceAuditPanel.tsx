import type { SourceProvenanceAuditSummary, SourceProvenanceCandidate, SourceProvenanceTeamRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: SourceProvenanceAuditSummary;
}

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-rose-500/15 text-rose-300",
  medium: "bg-amber-500/15 text-amber-300",
  low: "bg-slate-700/40 text-slate-400",
};

function SourceReviewCandidateLine({ candidate }: { candidate: SourceProvenanceCandidate }) {
  return (
    <li className="rounded bg-slate-800/50 px-2 py-1.5 text-[11px]">
      <p className="break-words text-slate-300">
        {candidate.name}
        <span className="ml-1 text-slate-500">{candidate.primary_position ?? "-"}</span>
      </p>
      <div className="mt-1 flex flex-wrap gap-1">
        {candidate.risk_flags.map((flag, idx) => (
          <span key={idx} className={`rounded px-1.5 py-0.5 text-[10px] ${SEVERITY_STYLES[flag.severity] ?? SEVERITY_STYLES.low}`}>
            {flag.marker}
          </span>
        ))}
      </div>
      {candidate.risk_flags[0] && (
        <p className="mt-1 break-words text-[11px] text-slate-400">{candidate.risk_flags[0].reason_ja}</p>
      )}
    </li>
  );
}

function SourceProvenanceTeamCard({ row }: { row: SourceProvenanceTeamRow }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TeamBadge teamId={row.team_id} />
        <span className="text-xs text-slate-500">出典確認候補 {row.source_risk_candidate_count}件</span>
      </div>
      {row.source_review_candidates.length > 0 ? (
        <ul className="mt-2 space-y-1.5">
          {row.source_review_candidates.map((candidate) => (
            <SourceReviewCandidateLine key={candidate.player_id} candidate={candidate} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[11px] text-slate-500">出典確認が必要な候補はありません。</p>
      )}
    </div>
  );
}

export function SourceProvenanceAuditPanel({ summary }: Props) {
  if (summary.teamCount === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  const { seedSourceSummary } = summary;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded bg-slate-700/40 px-2 py-1 text-slate-300">
          シード選手の出典リスク {seedSourceSummary.players_with_source_risk} / {seedSourceSummary.seed_player_count}
        </span>
        <span className="rounded bg-slate-700/40 px-2 py-1 text-slate-300">候補総数 {summary.decisionCandidateCount}</span>
        <span className="rounded bg-emerald-500/15 px-2 py-1 text-emerald-300">提案候補 {summary.clearLaterProposalCandidateCount}</span>
        <span className="rounded bg-amber-500/15 px-2 py-1 text-amber-300">出典確認 {summary.sourceReviewCandidateCount}</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {Object.entries(seedSourceSummary.marker_counts).map(([marker, count]) => (
          <span key={marker} className="rounded bg-slate-800/70 px-1.5 py-0.5 text-[10px] text-slate-400">
            {marker}: {count}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {summary.teams.map((row) => (
          <SourceProvenanceTeamCard key={row.team_id} row={row} />
        ))}
      </div>

      <ul className="space-y-0.5 text-[11px] text-slate-400">
        {summary.recommendations_ja.map((line, idx) => (
          <li key={idx} className="break-words">
            ・{line}
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
