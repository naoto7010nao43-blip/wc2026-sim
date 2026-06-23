import type { ModelCalibrationSummary, ModelCalibrationWatchlistTeam } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  summary: ModelCalibrationSummary;
}

const STATUS_LABELS: Record<string, string> = {
  pass: "ベンチマーク上は合格",
  review: "要レビュー",
};

function formatSigned(value: number, unit: string): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}${unit}`;
}

function WatchlistRow({ team }: { team: ModelCalibrationWatchlistTeam }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded bg-slate-800/50 px-2 py-1 text-[11px]">
      <TeamBadge teamId={team.team_id} />
      <span className="text-slate-400">
        不自然判定 {formatSigned(team.implausible_favorite_count_delta, "件")} / 平均勝率{" "}
        {formatSigned(team.average_favorite_win_pct_delta, "pt")}
      </span>
    </div>
  );
}

export function ModelCalibrationPanel({ summary }: Props) {
  if (!summary.overall || !summary.watchlist) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">{summary.note}</div>
    );
  }

  const improvedTeams = summary.watchlist.teams.filter((team) => team.implausible_favorite_count_delta < 0);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-slate-200">モデルキャリブレーション</h3>
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
            {summary.modelVersionAfter ?? "-"}
          </span>
          <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-300">
            {(summary.status && STATUS_LABELS[summary.status]) ?? summary.status ?? "-"}
          </span>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[11px]">
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">全体の不自然判定</p>
          <p className="font-semibold text-emerald-400">
            {formatSigned(summary.overall.implausible_favorite_count_delta, "件")}
          </p>
        </div>
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">本命勝率の平均変化</p>
          <p className="font-semibold text-slate-200">
            {formatSigned(summary.overall.average_favorite_win_pct_delta, "pt")}
          </p>
        </div>
        <div className="rounded bg-slate-900/50 px-1 py-1.5">
          <p className="text-slate-500">注目チームの改善</p>
          <p className="font-semibold text-emerald-400">{summary.watchlist.watchlist_implausible_reduction ?? 0}件改善</p>
        </div>
      </div>

      {improvedTeams.length > 0 && (
        <div className="mt-2 space-y-1">
          {improvedTeams.map((team) => (
            <WatchlistRow key={team.team_id} team={team} />
          ))}
        </div>
      )}

      <p className="mt-2 text-[11px] text-slate-400">{summary.note}</p>
    </section>
  );
}
