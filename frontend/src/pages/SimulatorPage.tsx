import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { MatchPredictionPanel } from "../components/MatchPredictionPanel";
import { TacticalMatchupPanel } from "../components/TacticalMatchupPanel";
import { countryNameJa } from "../data/countryNamesJa";
import type { TeamSummary } from "../types/domain";

export function SimulatorPage() {
  const navigate = useNavigate();
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [homeTeamId, setHomeTeamId] = useState("");
  const [awayTeamId, setAwayTeamId] = useState("");
  const [seed, setSeed] = useState("");
  const [decisive, setDecisive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTeams().then((data) => {
      const sorted = [...data].sort((a, b) => (a.group_id ?? "").localeCompare(b.group_id ?? "") || a.name.localeCompare(b.name));
      setTeams(sorted);
      if (sorted.length >= 2) {
        setHomeTeamId(sorted[0].id);
        setAwayTeamId(sorted[1].id);
      }
    });
  }, []);

  const homeTeam = useMemo(() => teams.find((t) => t.id === homeTeamId), [teams, homeTeamId]);
  const awayTeam = useMemo(() => teams.find((t) => t.id === awayTeamId), [teams, awayTeamId]);
  const trimmedSeed = seed.trim();
  const parsedSeed = trimmedSeed === "" ? undefined : Number(trimmedSeed);
  const seedIsValid = trimmedSeed === "" || (typeof parsedSeed === "number" && Number.isInteger(parsedSeed));
  const sameTeamsSelected = Boolean(homeTeamId && awayTeamId && homeTeamId === awayTeamId);
  const canRunSimulation = teams.length > 0 && !loading && !sameTeamsSelected && seedIsValid;

  async function runSimulation() {
    if (!homeTeamId || !awayTeamId || homeTeamId === awayTeamId) {
      setError("異なる2チームを選択してください。");
      return;
    }
    if (!seedIsValid) {
      setError("シードは整数で入力してください。");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const match = await api.simulateMatch(homeTeamId, awayTeamId, {
        seed: parsedSeed,
        allowDraw: !decisive,
      });
      navigate(`/matches/${match.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
        <h2 className="text-xl font-bold">試合シミュレーター</h2>
        <p className="mt-1 text-sm text-slate-400">
          気になる対戦カードを選んで、その1試合だけを詳細にシミュレーションします。
        </p>

        <div className="mt-5 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-slate-300">ホームチーム</label>
            <select
              value={homeTeamId}
              onChange={(e) => setHomeTeamId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-2 py-1.5 text-slate-100"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.group_id}] {countryNameJa(t.id, t.name)} ({t.id})
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              監督: {homeTeam?.tactical_profile?.manager_name ?? "-"} / フォーメーション: {homeTeam?.default_formation ?? "-"}
            </p>
            {homeTeamId && (
              <Link to={`/teams/${homeTeamId}`} className="mt-1 inline-block text-xs text-emerald-400 hover:text-emerald-300">
                予測スタメンを見る →
              </Link>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300">アウェイチーム</label>
            <select
              value={awayTeamId}
              onChange={(e) => setAwayTeamId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-2 py-1.5 text-slate-100"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.group_id}] {countryNameJa(t.id, t.name)} ({t.id})
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              監督: {awayTeam?.tactical_profile?.manager_name ?? "-"} / フォーメーション: {awayTeam?.default_formation ?? "-"}
            </p>
            {awayTeamId && (
              <Link to={`/teams/${awayTeamId}`} className="mt-1 inline-block text-xs text-emerald-400 hover:text-emerald-300">
                予測スタメンを見る →
              </Link>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            シード任意:
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="ランダム"
              inputMode="numeric"
              className="w-28 rounded-md border border-slate-600 bg-slate-900 px-2 py-1 text-slate-100"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input type="checkbox" checked={decisive} onChange={(e) => setDecisive(e.target.checked)} />
            引き分けなし（延長・PK）
          </label>
        </div>

        {(sameTeamsSelected || !seedIsValid) && (
          <p className="mt-3 text-xs text-amber-300">
            {sameTeamsSelected ? "同じチーム同士では実行できません。左右で異なる国を選んでください。" : "シードは空欄、または整数だけを指定できます。"}
          </p>
        )}

        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

        <button
          onClick={runSimulation}
          disabled={!canRunSimulation}
          className="mt-5 rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "シミュレーション中..." : "シミュレーション開始"}
        </button>
      </section>

      <TacticalMatchupPanel homeTeam={homeTeam} awayTeam={awayTeam} />

      {homeTeamId && awayTeamId && homeTeamId !== awayTeamId && (
        <MatchPredictionPanel homeTeamId={homeTeamId} awayTeamId={awayTeamId} />
      )}
    </div>
  );
}
