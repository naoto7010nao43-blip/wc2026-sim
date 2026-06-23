import type { RatingReviewCandidate, RatingReviewTeamRow, RatingReviewWorkbenchSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: RatingReviewWorkbenchSummary;
}

const BAND_STYLES: Record<string, string> = {
  high: "border-rose-700/60 bg-rose-500/10 text-rose-300",
  medium: "border-amber-700/60 bg-amber-500/10 text-amber-300",
  low: "border-slate-700/60 bg-slate-800/40 text-slate-400",
};

const BAND_LABELS: Record<string, string> = {
  high: "レビュー候補: 高",
  medium: "レビュー候補: 中",
  low: "レビュー候補: 低",
};

const FLAG_LABELS: Record<string, string> = {
  team_rank_underperformance: "チームのランク比劣勢",
  weak_position_group: "手薄ポジション",
  value_outpaces_rating: "市場価値が能力値より高め",
  rating_outpaces_value: "能力値が市場価値より高め",
  caps_outpace_rating: "代表キャップ数が能力値より高め",
  rating_outpaces_caps: "能力値が代表キャップ数より高め",
  high_starting_probability_low_rating: "先発確率は高いが能力値は中央値未満",
  many_low_confidence_attributes: "低信頼度の能力値項目が多い",
  shallow_roster_top_contributor: "薄いロスターの主力級選手",
};

const ACTION_LABELS: Record<string, string> = {
  inspect_for_possible_upgrade: "上方修正の確認候補(Codexレビュー待ち)",
  inspect_for_possible_downgrade: "下方修正の確認候補(Codexレビュー待ち)",
  verify_roster_role_first: "まず役割・出場機会の確認が必要",
  monitor_only: "モニタリングのみ",
};

const POSITION_GROUP_ORDER = ["GK", "DF", "MF", "FW"];

function CandidateRow({ candidate }: { candidate: RatingReviewCandidate }) {
  return (
    <div className="rounded border border-slate-700/60 bg-slate-800/50 p-2">
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <p className="break-words text-xs font-semibold text-slate-200">
          {candidate.name}
          <span className="ml-1 text-[10px] font-normal text-slate-500">{candidate.primary_position}</span>
        </p>
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${BAND_STYLES[candidate.review_band] ?? BAND_STYLES.low}`}>
          {BAND_LABELS[candidate.review_band] ?? candidate.review_band}
        </span>
      </div>
      <p className="mt-1 text-[11px] text-slate-400">
        能力値 {candidate.current_overall ?? "-"} / 先発確率 {candidate.starting_probability ?? "-"}%
      </p>
      {candidate.review_flags.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {candidate.review_flags.map((flag) => (
            <span key={flag} className="rounded bg-slate-700/60 px-1.5 py-0.5 text-[10px] text-slate-300 break-words">
              {FLAG_LABELS[flag] ?? flag}
            </span>
          ))}
        </div>
      )}
      <p className="mt-1 break-words text-[11px] font-semibold text-emerald-400">
        {ACTION_LABELS[candidate.suggested_codex_action] ?? candidate.suggested_codex_action}
      </p>
    </div>
  );
}

function RatingReviewTeamCard({ row }: { row: RatingReviewTeamRow }) {
  const weakGroups = POSITION_GROUP_ORDER.filter((group) => row.position_group_summary[group]?.is_weak_group);
  const topCandidates = row.rating_review_candidates.slice(0, 5);

  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TeamBadge teamId={row.team_id} />
          <span className="text-xs text-slate-500">FIFA {row.fifa_rank ?? "-"}</span>
        </div>
        <span className="text-xs text-slate-500">ランク比劣勢シグナル {row.rank_underperformance_flags}件</span>
      </div>

      {weakGroups.length > 0 && (
        <p className="mt-2 text-[11px] text-amber-400">手薄ポジション候補: {weakGroups.join(" / ")}</p>
      )}

      {topCandidates.length === 0 ? (
        <p className="mt-2 text-[11px] text-slate-500">現時点で能力値レビュー候補に挙がる選手はいません。</p>
      ) : (
        <div className="mt-2 space-y-1.5">
          {topCandidates.map((candidate) => (
            <CandidateRow key={candidate.player_id} candidate={candidate} />
          ))}
        </div>
      )}
    </div>
  );
}

export function RatingReviewWorkbenchPanel({ summary }: Props) {
  if (summary.teams.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-400">対象チーム数: {summary.teamCount}</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {summary.teams.map((row) => (
          <RatingReviewTeamCard key={row.team_id} row={row} />
        ))}
      </div>
      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
