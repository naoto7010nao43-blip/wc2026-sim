import type { SquadGapSummary, SquadGapTeamRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: SquadGapSummary;
}

const FLAG_LABELS: Record<string, string> = {
  shallow_seed_roster: "シードロスターが少ない",
  thin_defensive_depth: "守備層が薄い",
  thin_attacking_depth: "攻撃層が薄い",
  low_official_profile_coverage: "公式データ反映率が低い",
  many_low_confidence_attributes: "低信頼度の能力値が多い",
  stale_seed_review_needed: "古いシード選手の確認が必要",
  name_pair_review_needed: "名寄せ候補の確認が必要",
};

const ACTION_LABELS: Record<string, string> = {
  rating_data_review: "能力値データレビュー",
  roster_reconciliation_review: "ロスター候補レビュー",
  name_matching_review: "名寄せ候補レビュー",
  monitor_only: "モニタリングのみ",
};

const POSITION_GROUP_ORDER = ["GK", "DF", "MF", "FW"];

function SquadGapCard({ row }: { row: SquadGapTeamRow }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TeamBadge teamId={row.team_id} />
          <span className="text-xs text-slate-500">FIFA {row.fifa_rank ?? "-"}</span>
        </div>
        <span className="text-xs text-slate-500">スコア {row.priority_score?.toFixed(1) ?? "-"}</span>
      </div>

      <div className="mt-2 grid grid-cols-4 gap-1.5 text-center text-[11px]">
        {POSITION_GROUP_ORDER.map((group) => (
          <div key={group} className="rounded bg-slate-800/70 px-1 py-1">
            <p className="text-slate-500">{group}</p>
            <p className="font-semibold text-slate-200">{row.position_groups[group]?.count ?? 0}</p>
            <p className="text-slate-500">{row.position_groups[group]?.avg_overall?.toFixed(0) ?? "-"}</p>
          </div>
        ))}
      </div>

      <p className="mt-2 text-[11px] text-slate-400">
        能力値: 最小{row.rating_distribution.min_overall ?? "-"} / 中央{row.rating_distribution.median_overall ?? "-"} / 最大
        {row.rating_distribution.max_overall ?? "-"} (70以上 {row.rating_distribution.count_overall_gte_70}人)
      </p>

      {row.diagnostic_flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {row.diagnostic_flags.map((flag) => (
            <span key={flag} className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-300">
              {FLAG_LABELS[flag] ?? flag}
            </span>
          ))}
        </div>
      )}

      <ul className="mt-2 space-y-0.5 text-xs text-slate-400">
        {row.review_summary_ja.map((line, idx) => (
          <li key={idx} className="break-words">
            ・{line}
          </li>
        ))}
      </ul>

      <p className="mt-2 text-xs font-semibold text-emerald-400">
        次の確認: {ACTION_LABELS[row.recommended_next_action] ?? row.recommended_next_action}
      </p>
    </div>
  );
}

export function SquadGapPanel({ summary }: Props) {
  if (summary.teams.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {summary.teams.map((row) => (
          <SquadGapCard key={row.team_id} row={row} />
        ))}
      </div>
      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
