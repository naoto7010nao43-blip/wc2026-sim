import type { StandingsRow } from "../types/domain";
import { TeamBadge } from "./TeamBadge";

interface Props {
  rows: StandingsRow[];
  highlightTop?: number;
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
        {rows.map((r, idx) => (
          <tr
            key={r.team_id}
            className={`border-b border-slate-800 ${idx < highlightTop ? "bg-emerald-900/30" : ""}`}
          >
            <td className="py-1 text-left text-slate-400">{idx + 1}</td>
            <td className="py-1 text-left">
              <TeamBadge teamId={r.team_id} />
            </td>
            <td className="py-1 text-center text-slate-300">{r.played}</td>
            <td className="py-1 text-center text-slate-300">{r.won}</td>
            <td className="py-1 text-center text-slate-300">{r.drawn}</td>
            <td className="py-1 text-center text-slate-300">{r.lost}</td>
            <td className="py-1 text-center text-slate-300">{r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}</td>
            <td className="py-1 text-center font-bold text-slate-100">{r.points}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
