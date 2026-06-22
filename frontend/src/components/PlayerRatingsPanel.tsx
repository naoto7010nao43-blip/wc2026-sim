import type { PlayerRating } from "../types/domain";

interface Props {
  ratings: PlayerRating[];
  homeTeamId: string;
  awayTeamId: string;
}

function ratingColor(rating: number): string {
  if (rating >= 8.0) return "bg-emerald-600";
  if (rating >= 7.0) return "bg-emerald-500/80";
  if (rating >= 6.0) return "bg-amber-500/80";
  if (rating >= 5.0) return "bg-orange-600/80";
  return "bg-rose-600/80";
}

function RatingRow({ rating }: { rating: PlayerRating }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className={`flex items-center gap-1 text-sm text-slate-200 ${rating.is_mom ? "font-bold" : ""}`}>
        {rating.is_mom && <span title="Man of the Match">⭐</span>}
        {rating.name}
        {rating.is_estimated && (
          <span className="rounded bg-slate-700 px-1 py-0.5 text-[9px] font-normal text-slate-400">推定</span>
        )}
      </span>
      <span className={`min-w-[2.5rem] rounded px-1.5 py-0.5 text-center text-xs font-bold text-white ${ratingColor(rating.rating)}`}>
        {rating.rating.toFixed(1)}
      </span>
    </div>
  );
}

export function PlayerRatingsPanel({ ratings, homeTeamId, awayTeamId }: Props) {
  if (ratings.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center text-sm text-slate-400">
        この試合の選手採点は利用できません。
      </div>
    );
  }

  const mom = ratings.find((r) => r.is_mom);
  const home = ratings.filter((r) => r.team_id === homeTeamId).sort((a, b) => b.rating - a.rating);
  const away = ratings.filter((r) => r.team_id === awayTeamId).sort((a, b) => b.rating - a.rating);
  const anyEstimated = ratings.some((r) => r.is_estimated);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
      {mom && (
        <div className="mb-3 flex items-center justify-center gap-2 rounded-lg bg-amber-500/10 py-2 text-sm">
          <span>⭐</span>
          <span className="text-slate-400">Man of the Match:</span>
          <span className="font-bold text-amber-400">{mom.name}</span>
          <span className={`rounded px-1.5 py-0.5 text-xs font-bold text-white ${ratingColor(mom.rating)}`}>{mom.rating.toFixed(1)}</span>
        </div>
      )}
      <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">選手採点</p>
      {anyEstimated && (
        <p className="mb-2 text-xs text-slate-500">
          実際の試合のため、確認できた得点者のみ推定採点を表示しています(全選手の採点ではありません)。
        </p>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div>
          {home.map((r) => (
            <RatingRow key={r.player_id} rating={r} />
          ))}
        </div>
        <div>
          {away.map((r) => (
            <RatingRow key={r.player_id} rating={r} />
          ))}
        </div>
      </div>
    </div>
  );
}
