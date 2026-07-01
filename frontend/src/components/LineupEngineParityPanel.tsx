import type { LineupEngineParityAuditSummary, LineupParityTeamRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: LineupEngineParityAuditSummary;
}

function Metric({ label, value, tone = "slate" }: { label: string; value: string | number; tone?: "slate" | "good" | "warn" | "bad" }) {
  const toneClass =
    tone === "good" ? "text-emerald-300" : tone === "bad" ? "text-rose-300" : tone === "warn" ? "text-amber-300" : "text-slate-100";
  return (
    <div className="rounded bg-slate-900/50 px-2 py-2 text-center">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

function TeamParityRow({ row }: { row: LineupParityTeamRow }) {
  return (
    <div className="rounded border border-slate-700/70 bg-slate-900/40 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <TeamBadge teamId={row.teamId} />
          <p className="mt-1 text-[11px] text-slate-500">
            {row.defaultFormation} / 表示 {row.displayedStarterCount} / 実行 {row.simulatedStarterCount}
          </p>
        </div>
        <span
          className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
            row.parityOk
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/40 bg-rose-500/10 text-rose-300"
          }`}
        >
          {row.parityOk ? "一致" : "差分あり"}
        </span>
      </div>
      <p className="mt-2 text-[11px] text-slate-400">{row.reasonJa}</p>
      {row.mismatches.length > 0 && (
        <div className="mt-2 space-y-1 text-[11px] text-slate-400">
          {row.mismatches.slice(0, 4).map((mismatch) => (
            <p key={`${row.teamId}-${mismatch.slotIndex}`}>
              {mismatch.displayedSlotPosition ?? "-"}: {mismatch.displayedName ?? "未設定"} / {mismatch.simulatedName ?? "未設定"}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function LineupEngineParityPanel({ summary }: Props) {
  if (summary.teamCount === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        {summary.note}
      </div>
    );
  }

  const flagged = summary.teams.filter((team) => !team.parityOk);
  const shownRows = flagged.length > 0 ? flagged.slice(0, 8) : summary.teams.slice(0, 6);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-200">スタメン一致監査</h3>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">{summary.note}</p>
        </div>
        <span className="rounded bg-emerald-500/15 px-2 py-1 text-[10px] font-semibold text-emerald-300">表示と実行の接続</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="確認チーム" value={`${summary.checkedTeamCount}/${summary.teamCount}`} />
        <Metric label="完全一致" value={summary.fullParityTeamCount} tone={summary.fullParityTeamCount === summary.teamCount ? "good" : "warn"} />
        <Metric label="差分チーム" value={summary.mismatchTeamCount} tone={summary.mismatchTeamCount > 0 ? "bad" : "good"} />
        <Metric label="差分スロット" value={summary.mismatchSlotCount} tone={summary.mismatchSlotCount > 0 ? "bad" : "good"} />
        <Metric
          label="不完全XI"
          value={summary.incompleteDisplayedLineupTeamCount + summary.incompleteSimulatedLineupTeamCount}
          tone={summary.incompleteDisplayedLineupTeamCount + summary.incompleteSimulatedLineupTeamCount > 0 ? "bad" : "good"}
        />
      </div>

      {flagged.length === 0 ? (
        <div className="mt-3 rounded border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200">
          全チームで、表示される予想スタメンとシミュレーターが実際に起用する先発XIが一致しています。
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {shownRows.map((row) => (
            <TeamParityRow key={row.teamId} row={row} />
          ))}
        </div>
      )}

      <div className="mt-3 space-y-1 text-[11px] text-slate-400">
        {summary.recommendationsJa.map((line) => (
          <p key={line}>・{line}</p>
        ))}
      </div>
    </section>
  );
}
