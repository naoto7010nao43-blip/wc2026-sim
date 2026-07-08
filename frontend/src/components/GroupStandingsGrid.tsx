import type { MatchSummary, StandingsRow } from "../types/domain";
import { MatchCard } from "./MatchCard";
import { StandingsTable } from "./StandingsTable";

interface Props {
  groupStandings: Record<string, StandingsRow[]>;
  groupMatches?: MatchSummary[];
}

const GROUP_LETTERS = "ABCDEFGHIJKL".split("");

function pointSpread(rows: StandingsRow[]): number | null {
  if (rows.length < 2) return null;
  const points = rows.map((row) => row.points);
  return Math.max(...points) - Math.min(...points);
}

export function GroupStandingsGrid({ groupStandings, groupMatches = [] }: Props) {
  const matchesByGroup = groupMatches.reduce<Record<string, MatchSummary[]>>((acc, m) => {
    if (!m.group_id) return acc;
    (acc[m.group_id] ??= []).push(m);
    return acc;
  }, {});
  for (const matches of Object.values(matchesByGroup)) {
    matches.sort((a, b) => a.played_at.localeCompare(b.played_at));
  }
  const realCount = groupMatches.filter((m) => m.is_real).length;

  return (
    <div>
      {groupMatches.length > 0 && (
        <p className="mb-3 flex items-center gap-1.5 text-xs text-slate-400">
          <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
          実際に行われた試合の結果を反映しています({realCount}/{groupMatches.length}試合)。
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {GROUP_LETTERS.map((letter) => {
          const rows = groupStandings[letter] ?? [];
          const spread = pointSpread(rows);
          return (
            <div key={letter} className="panel overflow-hidden">
              <div className="flex items-center justify-between gap-3 border-b border-slate-700/70 bg-slate-900/40 px-3 py-2">
                <div className="flex items-center gap-2.5">
                  <span className="score-num flex h-7 w-7 items-center justify-center rounded bg-emerald-500/15 text-lg text-emerald-300">
                    {letter}
                  </span>
                  <h3 className="font-display text-sm font-bold tracking-wide text-slate-200">GROUP {letter}</h3>
                </div>
                {spread != null && (
                  <span className="text-[11px] text-slate-500">
                    勝点差 <span className="score-num text-slate-400">{spread}</span>
                  </span>
                )}
              </div>
              <div className="p-3">
                <StandingsTable rows={rows} />
                {(matchesByGroup[letter]?.length ?? 0) > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {matchesByGroup[letter].map((m) => (
                      <MatchCard key={m.id} match={m} className="text-xs" />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
