import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { LikelyLineupOut } from "../types/domain";

interface Props {
  teamId: string;
}

function probabilityColor(pct: number): string {
  if (pct >= 70) return "bg-emerald-600";
  if (pct >= 50) return "bg-emerald-500/80";
  if (pct >= 30) return "bg-amber-500/80";
  return "bg-rose-600/80";
}

export function LikelyLineupPanel({ teamId }: Props) {
  const [data, setData] = useState<LikelyLineupOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of stale lineup before refetching on teamId change
    setData(null);
    setError(null);
    api.getLikelyLineup(teamId).then(setData).catch((e) => setError(String(e)));
  }, [teamId]);

  if (error) return <p className="text-sm text-rose-400">{error}</p>;
  if (!data) return <p className="text-sm text-slate-400">読み込み中...</p>;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-xs uppercase tracking-widest text-slate-500">予測スタメン ({data.formation})</p>
      </div>
      <div className="mt-3 space-y-1">
        {data.lineup.map((slot) => (
          <div key={slot.player_id} className="flex items-center justify-between gap-2 py-1">
            <span className="flex items-center gap-2 text-sm text-slate-200">
              <span className="w-10 rounded bg-slate-700 px-1.5 py-0.5 text-center text-[10px] font-bold text-slate-300">
                {slot.slot_position}
              </span>
              {slot.name_ja ?? slot.name}
            </span>
            <span className={`min-w-[3rem] rounded px-1.5 py-0.5 text-center text-xs font-bold text-white ${probabilityColor(slot.starting_probability)}`}>
              {Math.round(slot.starting_probability)}%
            </span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">{data.disclaimer}</p>
    </div>
  );
}
