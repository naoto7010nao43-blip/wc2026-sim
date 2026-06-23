import type { StandingsRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  rows: StandingsRow[];
  highlightTop?: number;
}

function qualificationLabel(index: number, highlightTop: number): { text: string; className: string } | null {
  if (index < highlightTop) {
    return { text: "突破圏", className: "bg-emerald-500/15 text-emerald-300" };
  }
  if (index === highlightTop) {
    return { text: "3位候補", className: "bg-amber-500/15 text-amber-300" };
  }
  return null;
}

export function StandingsTable({ rows, highlightTop = 2 }: Props) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-400">まだ試合が行われていません。</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-slate-700 text-slate-400">
          <th className="py-1 text-left font-medium">#</th>
          <th className="py-1 text-left font-medium">チーム</th>
          <th className="py-1 font-medium">試合</th>
          <th className="py-1 font-medium">勝</th>
          <th className="py-1 font-medium">分</th>
          <th className="py-1 font-medium">敗</th>
          <th className="py-1 font-medium">得失差</th>
          <th className="py-1 font-medium">点</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, idx) => {
          const label = qualificationLabel(idx, highlightTop);
          return (
            <tr
              key={r.team_id}
              className={`border-b border-slate-800 ${idx < highlightTop ? "bg-emerald-900/30" : idx === highlightTop ? "bg-amber-900/10" : ""}`}
            >
              <td className="py-1 text-left text-slate-400">{idx + 1}</td>
              <td className="py-1 text-left">
                <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                  <TeamBadge teamId={r.team_id} />
                  {label && <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${label.className}`}>{label.text}</span>}
                </div>
              </td>
              <td className="py-1 text-center text-slate-300">{r.played}</td>
              <td className="py-1 text-center text-slate-300">{r.won}</td>
              <td className="py-1 text-center text-slate-300">{r.drawn}</td>
              <td className="py-1 text-center text-slate-300">{r.lost}</td>
              <td className="py-1 text-center text-slate-300">{r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}</td>
              <td className="py-1 text-center font-bold text-slate-100">{r.points}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
