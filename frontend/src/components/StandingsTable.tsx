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
        <tr className="border-b border-slate-700 text-[11px] uppercase tracking-wider text-slate-500">
          <th className="w-6 py-1.5 text-left font-semibold">#</th>
          <th className="py-1.5 text-left font-semibold">チーム</th>
          <th className="w-8 py-1.5 font-semibold">試</th>
          <th className="w-7 py-1.5 font-semibold">勝</th>
          <th className="w-7 py-1.5 font-semibold">分</th>
          <th className="w-7 py-1.5 font-semibold">敗</th>
          <th className="w-10 py-1.5 font-semibold">+/-</th>
          <th className="w-8 py-1.5 font-semibold">点</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, idx) => {
          const advance = idx < highlightTop;
          const playoff = idx === highlightTop;
          return (
            <tr
              key={r.team_id}
              className={`border-b border-slate-800/80 last:border-b-0 ${
                advance ? "bg-emerald-500/8" : playoff ? "bg-amber-500/6" : ""
              }`}
            >
              <td
                className={`qual-bar py-1.5 pl-2 text-left ${
                  advance ? "qual-bar--advance" : playoff ? "qual-bar--playoff" : ""
                }`}
              >
                <span className={`score-num text-xs ${advance ? "text-emerald-300" : playoff ? "text-amber-300" : "text-slate-500"}`}>
                  {idx + 1}
                </span>
              </td>
              <td className="max-w-0 py-1.5 pr-1 text-left">
                <TeamBadge teamId={r.team_id} className="w-full" />
              </td>
              <td className="py-1.5 text-center text-slate-400">{r.played}</td>
              <td className="py-1.5 text-center text-slate-300">{r.won}</td>
              <td className="py-1.5 text-center text-slate-400">{r.drawn}</td>
              <td className="py-1.5 text-center text-slate-400">{r.lost}</td>
              <td className={`score-num py-1.5 text-center text-xs ${r.goal_diff > 0 ? "text-emerald-300" : r.goal_diff < 0 ? "text-slate-500" : "text-slate-400"}`}>
                {r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}
              </td>
              <td className="score-num py-1.5 text-center text-base text-slate-100">{r.points}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
