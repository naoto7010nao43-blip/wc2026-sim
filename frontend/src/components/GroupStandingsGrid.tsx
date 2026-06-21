import type { MatchSummary, StandingsRow } from "../types/domain";
import { MatchCard } from "./MatchCard";
import { StandingsTable } from "./StandingsTable";

interface Props {
  groupStandings: Record<string, StandingsRow[]>;
  groupMatches?: MatchSummary[];
}

const GROUP_LETTERS = "ABCDEFGHIJKL".split("");

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
        <p className="mb-3 text-xs text-slate-400">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-400" />
          実際に行われた試合の結果を反映しています({realCount}/{groupMatches.length}試合)。
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {GROUP_LETTERS.map((letter) => (
          <div key={letter} className="rounded-lg border border-slate-700 bg-slate-800/60 p-3">
            <h3 className="mb-2 text-sm font-bold text-emerald-400">グループ {letter}</h3>
            <StandingsTable rows={groupStandings[letter] ?? []} />
            {(matchesByGroup[letter]?.length ?? 0) > 0 && (
              <div className="mt-3 space-y-1.5">
                {matchesByGroup[letter].map((m) => (
                  <MatchCard key={m.id} match={m} className="px-2 py-1.5 text-xs" />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
