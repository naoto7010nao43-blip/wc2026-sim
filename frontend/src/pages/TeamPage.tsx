import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { LikelyLineupPanel } from "../components/LikelyLineupPanel";
import { countryNameJa } from "../data/countryNamesJa";
import type { TeamOut } from "../types/domain";

export function TeamPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const [team, setTeam] = useState<TeamOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!teamId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of stale team data before refetching on teamId change
    setTeam(null);
    setError(null);
    api.getTeam(teamId).then(setTeam).catch((e) => setError(String(e)));
  }, [teamId]);

  if (error) return <p className="text-rose-400">{error}</p>;
  if (!team || !teamId) return <p className="text-slate-400">読み込み中...</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/simulate" className="text-sm text-slate-400 hover:text-slate-200">
          ← 試合シミュレーターに戻る
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <span className="rounded bg-slate-700 px-2 py-1 text-sm font-bold text-slate-100">{team.id}</span>
          <h1 className="text-2xl font-bold">{countryNameJa(team.id, team.name)}</h1>
        </div>
        <p className="mt-1 text-sm text-slate-400">
          監督: {team.tactical_profile?.manager_name ?? "-"} / フォーメーション: {team.default_formation} / FIFAランク: {team.fifa_rank ?? "-"}
        </p>
      </div>

      <LikelyLineupPanel teamId={teamId} />
    </div>
  );
}
