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

function confidenceLabel(pct: number): string {
  if (pct >= 70) return "有力";
  if (pct >= 50) return "候補";
  if (pct >= 30) return "競争中";
  return "不確実";
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

  const averageProbability =
    data.lineup.length > 0
      ? data.lineup.reduce((sum, slot) => sum + slot.starting_probability, 0) / data.lineup.length
      : 0;
  const strongCount = data.lineup.filter((slot) => slot.starting_probability >= 70).length;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">予測スタメン</p>
          <h2 className="mt-1 text-lg font-bold text-slate-100">{data.formation}</h2>
        </div>
        <div className="grid grid-cols-2 gap-2 text-right text-xs">
          <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 px-3 py-2">
            <p className="text-slate-500">平均確度</p>
            <p className="mt-0.5 font-bold text-slate-100">{Math.round(averageProbability)}%</p>
          </div>
          <div className="rounded-lg border border-slate-700/80 bg-slate-900/45 px-3 py-2">
            <p className="text-slate-500">有力枠</p>
            <p className="mt-0.5 font-bold text-slate-100">{strongCount}/{data.lineup.length}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-1.5">
        {data.lineup.map((slot) => (
          <div key={slot.player_id} className="grid grid-cols-[1fr_5rem] items-center gap-3 py-1">
            <span className="min-w-0 text-sm text-slate-200">
              <span className="flex min-w-0 items-center gap-2">
              <span className="w-10 rounded bg-slate-700 px-1.5 py-0.5 text-center text-[10px] font-bold text-slate-300">
                {slot.slot_position}
              </span>
                <span className="truncate">{slot.name_ja ?? slot.name}</span>
              </span>
              <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-slate-700">
                <span className={`block h-full ${probabilityColor(slot.starting_probability)}`} style={{ width: `${slot.starting_probability}%` }} />
              </span>
            </span>
            <span className="text-right">
              <span className={`inline-block min-w-[3rem] rounded px-1.5 py-0.5 text-center text-xs font-bold text-white ${probabilityColor(slot.starting_probability)}`}>
                {Math.round(slot.starting_probability)}%
              </span>
              <span className="mt-0.5 block text-[10px] text-slate-500">{confidenceLabel(slot.starting_probability)}</span>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">{data.disclaimer}</p>
    </div>
  );
}
