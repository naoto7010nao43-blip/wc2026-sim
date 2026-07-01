import type { FormationFitTeamRow, FormationPositionFitAuditSummary } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: FormationPositionFitAuditSummary;
}

const BAND_LABELS: Record<string, string> = {
  high: "高リスク",
  medium: "要確認",
  low: "低リスク",
};

function bandTone(band: string): string {
  if (band === "high") return "border-rose-500/40 bg-rose-500/10 text-rose-300";
  if (band === "medium") return "border-amber-500/40 bg-amber-500/10 text-amber-300";
  return "border-slate-600 bg-slate-700/30 text-slate-300";
}

function Metric({ label, value, tone = "slate" }: { label: string; value: string | number; tone?: "slate" | "warn" | "bad" }) {
  const toneClass = tone === "bad" ? "text-rose-300" : tone === "warn" ? "text-amber-300" : "text-slate-100";
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

function PlayerIssueList({ row }: { row: FormationFitTeamRow }) {
  const issues = row.outOfPositionAssignments.slice(0, 4);
  if (issues.length === 0) {
    return <p className="mt-2 text-[11px] text-slate-500">大きなポジション不一致はありません。</p>;
  }
  return (
    <div className="mt-2 space-y-1">
      {issues.map((issue) => (
        <p key={`${issue.slotPosition}-${issue.playerId ?? "empty"}`} className="text-[11px] text-slate-400">
          <span className="font-semibold text-slate-200">{issue.slotPosition}</span>
          <span className="mx-1 text-slate-600">←</span>
          {issue.name ?? "未割当"}
          <span className="ml-1 text-slate-500">({issue.primaryPosition ?? "-"})</span>
          {issue.startingProbability != null && (
            <span className="ml-1 text-amber-300">{Math.round(issue.startingProbability)}%</span>
          )}
        </p>
      ))}
    </div>
  );
}

function TeamCard({ row }: { row: FormationFitTeamRow }) {
  return (
    <div className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <TeamBadge teamId={row.teamId} />
          <p className="mt-1 text-[11px] text-slate-500">
            {row.defaultFormation} / roster {row.rosterSize} / score {row.severityScore.toFixed(1)}
          </p>
        </div>
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${bandTone(row.severityBand)}`}>
          {BAND_LABELS[row.severityBand] ?? row.severityBand}
        </span>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-1.5 text-center text-[11px]">
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">位置不一致</p>
          <p className="font-semibold text-amber-300">{row.outOfPositionCount}</p>
        </div>
        <div className="rounded bg-slate-800/70 px-1 py-1">
          <p className="text-slate-500">低先発確率</p>
          <p className="font-semibold text-slate-300">{row.lowProbabilityStarterCount}</p>
        </div>
      </div>

      <PlayerIssueList row={row} />
      <p className="mt-2 text-[11px] text-slate-400">{row.recommendedActionJa}</p>
    </div>
  );
}

export function FormationPositionFitPanel({ summary }: Props) {
  if (summary.teamCount === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        {summary.note}
      </div>
    );
  }

  const topTeams = summary.teams.filter((team) => team.severityScore > 0).slice(0, 12);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">フォーメーション適合監査</h3>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">{summary.note}</p>
        </div>
        <span className="rounded bg-sky-500/15 px-2 py-1 text-[10px] font-semibold text-sky-300">読み取り専用</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="対象チーム" value={summary.teamCount} />
        <Metric label="注意チーム" value={summary.flaggedTeamCount} tone="warn" />
        <Metric label="高リスク" value={summary.highSeverityTeamCount} tone={summary.highSeverityTeamCount > 0 ? "bad" : "slate"} />
        <Metric label="位置不一致" value={summary.outOfPositionAssignmentCount} tone="warn" />
        <Metric label="低先発確率" value={summary.lowProbabilityStarterCount} tone="warn" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        {topTeams.map((row) => (
          <TeamCard key={row.teamId} row={row} />
        ))}
      </div>

      <div className="mt-3 space-y-1 text-[11px] text-slate-400">
        {summary.recommendationsJa.map((line) => (
          <p key={line}>・{line}</p>
        ))}
      </div>
    </section>
  );
}
