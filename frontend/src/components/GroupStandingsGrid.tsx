import type { StandingsRow } from "../types/domain";
import { StandingsTable } from "./StandingsTable";

interface Props {
  groupStandings: Record<string, StandingsRow[]>;
}

const GROUP_LETTERS = "ABCDEFGHIJKL".split("");

export function GroupStandingsGrid({ groupStandings }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {GROUP_LETTERS.map((letter) => (
        <div key={letter} className="rounded-lg border border-slate-700 bg-slate-800/60 p-3">
          <h3 className="mb-2 text-sm font-bold text-emerald-400">グループ {letter}</h3>
          <StandingsTable rows={groupStandings[letter] ?? []} />
        </div>
      ))}
    </div>
  );
}
