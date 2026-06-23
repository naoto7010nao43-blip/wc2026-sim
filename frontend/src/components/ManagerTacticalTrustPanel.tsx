import type { ManagerTacticalTrustRow, ManagerTacticalTrustSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: ManagerTacticalTrustSummary;
}

const BAND_STYLES: Record<string, string> = {
  high: "border-rose-700/60 bg-rose-500/10 text-rose-300",
  medium: "border-amber-700/60 bg-amber-500/10 text-amber-300",
  low: "border-slate-700/60 bg-slate-800/40 text-slate-400",
};

const BAND_LABELS: Record<string, string> = {
  high: "レビュー優先度: 高",
  medium: "レビュー優先度: 中",
  low: "レビュー優先度: 低",
};

function ManagerTacticalTrustCard({ row }: { row: ManagerTacticalTrustRow }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TeamBadge teamId={row.team_id} />
          <span className="text-xs text-slate-500">FIFA {row.fifa_rank ?? "-"}</span>
        </div>
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${BAND_STYLES[row.review_band] ?? BAND_STYLES.low}`}>
          {BAND_LABELS[row.review_band] ?? row.review_band}
        </span>
      </div>

      <p className="mt-2 text-xs text-slate-300">
        監督: {row.manager_name_seed ?? "不明"}
        {row.manager_name_mismatch && <span className="ml-1 text-rose-400">(名称の不一致あり)</span>}
      </p>

      <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[11px]">
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">プレス</p>
          <p className="font-semibold text-slate-200">{row.tactical_profile.press_intensity ?? "-"}</p>
        </div>
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">ポゼッション</p>
          <p className="font-semibold text-slate-200">{row.tactical_profile.possession_style ?? "-"}</p>
        </div>
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">最終ライン</p>
          <p className="font-semibold text-slate-200">{row.tactical_profile.defensive_line_height ?? "-"}</p>
        </div>
      </div>

      {!row.has_tactical_basis && (
        <p className="mt-2 text-[11px] text-amber-400">戦術プロフィールの根拠情報が未登録です(推定値の可能性があります)</p>
      )}

      <ul className="mt-2 space-y-0.5 text-xs text-slate-400">
        {row.review_reasons.map((reason, idx) => (
          <li key={idx} className="break-words">
            ・{reason}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ManagerTacticalTrustPanel({ summary }: Props) {
  if (summary.teams.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded bg-rose-500/15 px-2 py-1 text-rose-300">高 {summary.bandCounts.high ?? 0}</span>
        <span className="rounded bg-amber-500/15 px-2 py-1 text-amber-300">中 {summary.bandCounts.medium ?? 0}</span>
        <span className="rounded bg-slate-700/40 px-2 py-1 text-slate-400">低 {summary.bandCounts.low ?? 0}</span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {summary.teams.map((row) => (
          <ManagerTacticalTrustCard key={row.team_id} row={row} />
        ))}
      </div>
      <p className="text-[11px] text-slate-500">{summary.note}</p>
    </div>
  );
}
