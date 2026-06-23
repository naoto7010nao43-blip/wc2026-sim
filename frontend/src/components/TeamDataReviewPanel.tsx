import type { TeamReviewRow, TeamReviewSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: TeamReviewSummary;
}

const BAND_STYLES: Record<TeamReviewRow["priority_band"], string> = {
  high: "bg-rose-500/20 text-rose-300",
  medium: "bg-amber-500/20 text-amber-300",
  low: "bg-slate-700 text-slate-400",
};

const BAND_LABELS: Record<TeamReviewRow["priority_band"], string> = {
  high: "優先レビュー",
  medium: "中優先",
  low: "低優先度",
};

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-100">{value}</p>
    </div>
  );
}

function TeamRow({ row }: { row: TeamReviewRow }) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TeamBadge teamId={row.team_id} />
          <span className="text-xs text-slate-500">FIFA {row.fifa_rank ?? "-"}</span>
        </div>
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${BAND_STYLES[row.priority_band]}`}>
          {BAND_LABELS[row.priority_band]}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-400">
        <span className="rounded bg-slate-800/70 px-2 py-1">シード人数 {row.seed_roster_size ?? "-"}</span>
        <span className="rounded bg-slate-800/70 px-2 py-1">モデル/順位差 {row.rank_underperformance_flags}</span>
        <span className="rounded bg-slate-800/70 px-2 py-1">名寄せ候補 {row.ambiguous_pair_count}</span>
        <span className="rounded bg-slate-800/70 px-2 py-1">古いシード {row.likely_stale_seed_player_count}</span>
        <span className="rounded bg-slate-800/70 px-2 py-1">追加候補 {row.high_confidence_add_candidate_count + row.other_add_candidate_count}</span>
      </div>

      <ul className="mt-2 space-y-0.5 text-xs text-slate-400">
        {row.review_reasons.map((reason, idx) => (
          <li key={idx}>・{reason}</li>
        ))}
      </ul>

      <p className="mt-2 text-xs font-semibold text-emerald-400">次の確認: {row.recommended_next_action}</p>
    </div>
  );
}

export function TeamDataReviewPanel({ summary }: Props) {
  const highTeams = summary.teams.filter((t) => t.priority_band === "high");
  const mediumTeams = summary.teams.filter((t) => t.priority_band === "medium");
  const lowCount = summary.teams.length - highTeams.length - mediumTeams.length;
  const ambiguousCount = summary.teams.filter((t) => t.ambiguous_pair_count > 0).length;
  const rankMismatchCount = summary.teams.filter((t) => t.rank_underperformance_flags > 0).length;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="優先レビュー" value={highTeams.length} />
        <SummaryCard label="中優先" value={mediumTeams.length} />
        <SummaryCard label="名寄せ候補あり" value={ambiguousCount} />
        <SummaryCard label="モデル/順位差あり" value={rankMismatchCount} />
      </div>

      {highTeams.length > 0 && (
        <section>
          <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">優先レビュー</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {highTeams.map((row) => (
              <TeamRow key={row.team_id} row={row} />
            ))}
          </div>
        </section>
      )}

      {mediumTeams.length > 0 && (
        <section>
          <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">中優先</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {mediumTeams.map((row) => (
              <TeamRow key={row.team_id} row={row} />
            ))}
          </div>
        </section>
      )}

      {lowCount > 0 && (
        <p className="text-xs text-slate-500">他{lowCount}チームは低優先度です(特筆すべき指摘なし、または構造的な候補数のみ)。</p>
      )}
    </div>
  );
}
